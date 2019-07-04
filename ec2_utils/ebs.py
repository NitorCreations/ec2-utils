#!/usr/bin/env python

from builtins import chr
from builtins import str
import time
import json
import sys
import os
import subprocess
from subprocess import PIPE, Popen, CalledProcessError
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dateutil import tz
from termcolor import colored
from botocore.exceptions import ClientError
from ec2_utils.ec2 import find_include
from ec2_utils.instance_info import info
from ec2_utils.utils import delete_selected, prune_array, delete_object
from threadlocal_aws.clients import ec2
from threadlocal_aws.resources import ec2 as ec2_resource

def letter_to_target_id(letter):
    return ord(letter) - ord("f") + 5


def target_id_to_letter(target_id):
    return str(chr(target_id - 5 + ord("f")))


def wmic_diskdrive_get():
    return wmic_get("diskdrive")


def wmic_get(command):
    ret = []
    proc = Popen(["wmic", command, "get",
                  "/format:rawxml"], stdout=PIPE, stderr=PIPE)
    output = proc.communicate()[0]
    tree = ET.fromstring(output)
    for elem in tree.iter("RESULTS"):
        for inst in elem.iter("INSTANCE"):
            disk = {}
            for prop in inst.iter("PROPERTY"):
                try:
                    disk[prop.attrib['NAME']] = int(prop.findtext("*"))
                except ValueError:
                    disk[prop.attrib['NAME']] = prop.findtext("*")
                except TypeError:
                    continue
            ret.append(disk)
    return ret


def wmic_disk_with_target_id(target_id):
    ret = [x for x in wmic_diskdrive_get() if x['SCSITargetId'] == target_id]
    if ret:
        return ret[0]
    else:
        return None


def wmic_disk_with_volume_id(volume_id):
    vol2 = volume_id.replace("-", "")
    ret = [x for x in wmic_diskdrive_get() \
           if x['SerialNumber'].startswith(volume_id) or \
           x['SerialNumber'].startswith(vol2)]
    if ret:
        return ret[0]
    else:
        return None


def wmic_disk_with_disk_number(disk_number):
    ret = [x for x in wmic_diskdrive_get() \
           if x['Index'] == disk_number]
    if ret:
        return ret[0]
    else:
        return None


def disk_by_drive_letter(drive_letter):
    ret = {}
    proc = Popen(["powershell.exe", find_include("disk-by-drive-letter.ps1"),
                  drive_letter.upper() + ":"], stdout=PIPE, stderr=PIPE)
    output = proc.communicate()[0]
    tree = ET.fromstring(output)
    for obj in tree.iter("Object"):
        for prop in obj.iter("Property"):
            try:
                ret[prop.attrib['Name']] = int(prop.findtext("."))
            except ValueError:
                ret[prop.attrib['Name']] = prop.findtext(".")
            except TypeError:
                continue
    return ret


def volume_from_snapshot(tag_key, tag_value, mount_path, availability_zone=None,
                         size_gb=None, del_on_termination=True, tags=[], copytags=[],
                         ignore_missing_copytags=False):
    snapshot = get_latest_snapshot(tag_key, tag_value)
    if snapshot:
        print("Found snapshot " + snapshot.id)
        volume = create_volume(snapshot.id, availability_zone=availability_zone,
                               size_gb=size_gb)
    else:
        if not size_gb:
            size_gb = 32
        print("Creating empty volyme of size " + str(size_gb))
        volume = create_empty_volume(size_gb,
                                     availability_zone=availability_zone)
    tag_volume(volume, tag_key, tag_value, tags, copytags,
               ignore_missing_copytags=ignore_missing_copytags)
    device = first_free_device()
    print("Attaching volume " + volume + " to " + device)
    attach_volume(volume, device)
    local_device = map_local_device(volume, device)
    if del_on_termination:
        delete_on_termination(device)
    if not snapshot:
        # empty device
        if sys.platform.startswith('win'):
            # Windows format
            drive_letter = mount_path[0].upper()
            disk = wmic_disk_with_target_id(letter_to_target_id(device[-1:]))
            if not disk:
                disk = wmic_disk_with_volume_id(volume)
            disk_number = str(disk['Index'])
            subprocess.check_call(["powershell.exe", "Get-Disk", disk_number,
                                   "|", "Set-Disk", "-IsOffline", "$False"])
            subprocess.check_call(["powershell.exe", "Initialize-Disk",
                                   disk_number, "-PartitionStyle", "MBR"])
            subprocess.check_call(["powershell.exe", "New-Partition",
                                   "-DiskNumber", disk_number,
                                   "-UseMaximumSize", "-DriveLetter",
                                   drive_letter])
            print("Formatting " + device + "(" + drive_letter + ":)")
            subprocess.check_call(["powershell.exe", "Format-Volume",
                                   "-DriveLetter", drive_letter, "-FileSystem",
                                   "NTFS", "-Force", "-Confirm:$False"])
        else:
            # linux format
            print("Formatting " + local_device)
            subprocess.check_call(["mkfs.ext4", local_device])
    else:
        if sys.platform.startswith('win'):
            target_id = letter_to_target_id(device[-1:])
            drive_letter = mount_path[0].upper()
            disk = wmic_disk_with_target_id(target_id)
            if not disk:
                disk = wmic_disk_with_volume_id(volume)
            disk_number = str(disk['Index'])
            with open(os.devnull, 'w') as devnull:
                subprocess.call(["powershell.exe", "Initialize-Disk",
                                 disk_number, "-PartitionStyle", "MBR"],
                                stderr=devnull, stdout=devnull)
            subprocess.check_call(["powershell.exe", "Get-Disk", disk_number,
                                   "|", "Set-Disk", "-IsOffline", "$False"])
            with open(os.devnull, 'w') as devnull:
                subprocess.check_call(["powershell.exe", "Get-Partition",
                                       "-DiskNumber", disk_number,
                                       "-PartitionNumber", "1"
                                       "|", "Set-Partition", "-NewDriveLetter",
                                       drive_letter], stdout=devnull,
                                      stderr=devnull)
            # resize win partition if necessary
            if size_gb and not size_gb == snapshot.volume_size:
                proc = subprocess.Popen(["powershell.exe",
                                         "$((Get-PartitionSupportedSize -Dri" +
                                         "veLetter " + drive_letter +
                                         ").SizeMax)"],
                                        stdout=subprocess.PIPE)
                max_size = proc.communicate()[0]
                subprocess.check_call(["powershell.exe", "Resize-Partition",
                                       "-DriveLetter", drive_letter, "-Size",
                                       max_size])
        else:
            if size_gb and not size_gb == snapshot.volume_size:
                print("Resizing " + local_device + " from " +
                      str(snapshot.volume_size) + "GB to " + str(size_gb))
                try:
                    subprocess.check_call(["e2fsck", "-f", "-p", local_device])
                except CalledProcessError as e:
                    print("Filesystem check returned " + str(e.returncode))
                    if e.returncode > 1:
                        raise Exception("Uncorrected filesystem errors - please fix manually")
                subprocess.check_call(["resize2fs", local_device])
    if not sys.platform.startswith('win'):
        if not os.path.isdir(mount_path):
            os.makedirs(mount_path)
        subprocess.check_call(["mount", local_device, mount_path])


def first_free_device():
    devices = attached_devices()
    print(devices)
    for letter in "fghijklmnopqrstuvxyz":
        device = "/dev/xvd" + letter
        if device not in devices and not os.path.exists(device):
            return device
    return None


def attached_devices(volume_id=None):
    volumes = ec2().describe_volumes(Filters=[{"Name": "attachment.instance-id",
                                               "Values": [ info().instance_id() ]},
                                              {"Name": "attachment.status",
                                               "Values": [ "attached" ]}])
    ret = []
    for volume in volumes['Volumes']:
        for attachment in volume['Attachments']:
            if (not volume_id) or volume['VolumeId'] == volume_id:
                ret.append(attachment['Device'])
    return ret

def get_latest_snapshot(tag_name, tag_value):
    """Get the latest snapshot with a given tag
    """
    filters = snapshot_filters(tag_name=tag_name, tag_value=tag_value)
    snapshots = sorted(ec2_resource().snapshots.filter(
        Filters=filters),
        key=lambda k: k.start_time, reverse=True)
    if snapshots:
        return snapshots[0]
    else:
        return None


def create_volume(snapshot_id, availability_zone=None, size_gb=None):
    args = {'SnapshotId': snapshot_id,
            'VolumeType': 'gp2'}
    if not availability_zone:
        availability_zone = info().availability_zone()
    args['AvailabilityZone'] = availability_zone
    if size_gb:
        args['Size'] = size_gb
    resp = ec2().create_volume(**args)
    wait_for_volume_status(resp['VolumeId'], "available")
    return resp['VolumeId']


def create_empty_volume(size_gb, availability_zone=None):
    args = {'Size': size_gb,
            'VolumeType': 'gp2'}
    if not availability_zone:
        availability_zone = info().availability_zone()
    args['AvailabilityZone'] = availability_zone
    resp = ec2().create_volume(**args)
    wait_for_volume_status(resp['VolumeId'], "available")
    return resp['VolumeId']


def wait_for_volume_status(volume_id, status, timeout_sec=300):
    start = time.time()
    volume = None
    while not match_volume_state(volume, status):
        time.sleep(2)
        if time.time() - start > timeout_sec:
            raise Exception("Failed waiting for status '" + status + "' for " +
                            volume_id + " (timeout: " + str(timeout_sec) + ")")
        resp = ec2().describe_volumes(VolumeIds=[volume_id])
        if "Volumes" in resp:
            volume = resp['Volumes'][0]


def match_volume_state(volume, status):
    if not volume:
        return False
    if status == "attached":
        return 'Attachments' in volume and len(volume['Attachments']) > 0 and \
               volume['Attachments'][0]['State'] == "attached"
    else:
        return volume['State'] == status


def wait_for_snapshot_complete(snapshot_id, timeout_sec=900):
    start = time.time()
    snapshot = None
    while not is_snapshot_complete(snapshot):
        time.sleep(2)
        if time.time() - start > timeout_sec:
            raise Exception("Failed waiting for status 'completed' for " +
                            snapshot_id + " (timeout: " + str(timeout_sec) + ")")
        resp = ec2().describe_snapshots(SnapshotIds=[snapshot_id])
        if "Snapshots" in resp:
            snapshot = resp['Snapshots'][0]

def is_snapshot_complete(snapshot):
    return snapshot is not None and 'State' in snapshot and \
        snapshot['State'] == 'completed'


def attach_volume(volume_id, device_path):
    instance_id = info().instance_id()
    ec2().attach_volume(VolumeId=volume_id, InstanceId=instance_id,
                        Device=device_path)
    wait_for_volume_status(volume_id, "attached")
    info().clear_cache()

def delete_on_termination(device_path):
    instance_id = info().instance_id()
    ec2().modify_instance_attribute(InstanceId=instance_id,
                                    BlockDeviceMappings=[{
                                        "DeviceName": device_path,
                                        "Ebs": {"DeleteOnTermination": True}}])


def detach_volume(mount_path, delete_volume=False, volume_id=None):
    instance_id = info().instance_id()
    if not volume_id:
        device = device_from_mount_path(mount_path)
        if "/nvme" in device:
            proc = Popen(["nvme", "id-ctrl", device], stdout=PIPE, stderr=PIPE)
            out = proc.communicate()[0]
            for nvme_line in out.split("\n"):
                if nvme_line.startswith("sn"):
                    volume_id = nvme_line.split()[2]
                    if "vol-" not in volume_id:
                        volume_id = volume_id.replace("vol", "vol-")
                    break
        else:
            volume = ec2().describe_volumes(Filters=[{"Name": "attachment.device",
                                                      "Values": [device]},
                                                     {"Name": "attachment.instance-id",
                                                      "Values": [instance_id]}])
            volume_id = volume['Volumes'][0]['VolumeId']
    proc = Popen(["umount", "-f", mount_path], stdout=PIPE, stderr=PIPE)
    out = proc.communicate()[0]
    ec2().detach_volume(VolumeId=volume_id, InstanceId=instance_id)
    if delete_volume:
        wait_for_volume_status(volume_id, "available")
        ec2().delete_volume(VolumeId=volume_id)
    info().clear_cache()


def create_snapshot(tag_key, tag_value, mount_path, wait=False, tags={},
                    copytags=[], ignore_missing_copytags=False):
    create_tags = _create_tag_array(tag_key, tag_value, tags, copytags,
                                    ignore_missing_copytags=ignore_missing_copytags)
    device = device_from_mount_path(mount_path)
    with open(os.devnull, 'w') as devnull:
        subprocess.call(["sync", mount_path[0]], stdout=devnull,
                        stderr=devnull)
    volume_id = None
    if "/nvme" in device:
        proc = Popen(["nvme", "id-ctrl", device], stdout=PIPE, stderr=PIPE)
        out = proc.communicate()[0]
        for nvme_line in out.split("\n"):
            if nvme_line.startswith("sn"):
                volume_id = nvme_line.split()[2]
                if "vol-" not in volume_id:
                    volume_id = volume_id.replace("vol", "vol-")
                break
    else:
        instance_id = info().instance_id()
        volume = ec2().describe_volumes(Filters=[{"Name": "attachment.instance-id", "Values": [instance_id]}])
        for volume in volume['Volumes']:
            if volume['Attachments'][0]['Device'] == device:
                volume_id = volume['VolumeId']
    if volume_id:
        snap = ec2().create_snapshot(VolumeId=volume_id)
        ec2().create_tags(Resources=[snap['SnapshotId']], Tags=create_tags)
    else:
        raise Exception("Could not find volume for " + mount_path + "(" + device + ")")
    if wait:
        wait_for_snapshot_complete(snap['SnapshotId'])
    return snap['SnapshotId']


def tag_volume(volume, tag_key, tag_value, tags, copytags, ignore_missing_copytags=False):
    tag_array = _create_tag_array(tag_key, tag_value, tags, copytags,
                                  ignore_missing_copytags=ignore_missing_copytags)
    ec2().create_tags(Resources=[volume], Tags=tag_array)


def _create_tag_array(tag_key, tag_value, tags={}, copytags=[], ignore_missing_copytags=False):
    if copytags:
        for tag in copytags:
            if info().tag(tag):
                tags[tag] = info().tag(tag)
            elif not ignore_missing_copytags:
                raise Exception("Missing copy tag " + tag)
    create_tags = []
    if not tags:
        tags = {}
    tags[tag_key] = tag_value
    tags['Name'] = tag_value
    for key, value in list(tags.items()):
        if not key.startswith("aws:"):
            create_tags.append({'Key': key, 'Value': value})
    return create_tags


def map_local_device(volume, device):
    if os.path.exists(device) or sys.platform.startswith('win'):
        return device
    vol2 = volume.replace("-", "")
    proc = Popen(["lsblk", "-lnpo", "NAME"], stdout=PIPE, stderr=PIPE)
    output = proc.communicate()[0]
    for line in output.split("\n"):
        proc = Popen(["nvme", "id-ctrl", line], stdout=PIPE, stderr=PIPE)
        out = proc.communicate()[0]
        for nvme_line in out.split("\n"):
            if nvme_line.startswith("sn"):
                if nvme_line.split()[2] == volume or nvme_line.split()[2] == vol2:
                    return line
    return None


def device_from_mount_path(mount_path):
    if sys.platform.startswith('win'):
        disk = disk_by_drive_letter(mount_path[0])
        if disk['TargetId'] != 0:
            return "/dev/xvd" + target_id_to_letter(disk['TargetId'])
        else:
            disk = wmic_disk_with_disk_number(disk['DiskNumber'])
            volume = disk['SerialNumber'].split("_")[0]
            if "-" not in volume:
                volume = volume.replace("vol", "vol-")
            return attached_devices(volume)[0]
    else:
        proc = Popen(["lsblk", "-lnpo", "NAME,MOUNTPOINT"], stdout=PIPE, stderr=PIPE)
        output = proc.communicate()[0]
        for line in output.split("\n"):
            dev_and_mount = line.split()
            if len(dev_and_mount) > 1 and dev_and_mount[1] == mount_path:
                return dev_and_mount[0]
        return None

def snapshot_filters(volume_id=None, tag_name=None, tag_value=None):
    if tag_name and not isinstance(tag_name, list):
        tag_name = [tag_name]
    if tag_value and not isinstance(tag_value, list):
        tag_value = [tag_value]

    filters =  [{ 'Name': 'status', 'Values': [ 'completed' ]}]
    if volume_id:
        filters.append({ 'Name': 'volume-id', 'Values': [volume_id] })
    if tag_name and tag_value:
        filters.append({ 'Name': 'tag:' + tag_name[0], 'Values': tag_value })
    elif tag_name:
        filters.append({ 'Name': 'tag-key', 'Values': tag_name})
    elif tag_value:
        filters.append({ 'Name': 'tag-value', 'Values': tag_value})
    return filters

def clean_snapshots(days, tags, dry_run=False):
    newest_timestamp = datetime.utcnow() - timedelta(days=days)
    newest_timestamp = newest_timestamp .replace(tzinfo=tz.UTC)
    filters = snapshot_filters(tag_value=tags)
    for snapshot in ec2_resource().snapshots.filter(Filters=filters):
        tags = {}
        for tag in snapshot.tags:
            tags[tag['Key']] = tag['Value']
        print_time = snapshot.start_time.replace(tzinfo=tz.tzlocal()).timetuple()
        compare_time = snapshot.start_time.replace(tzinfo=tz.UTC)
        if compare_time < newest_timestamp:
            print(colored("Deleting " + snapshot.id, "yellow") +
                  " || " + time.strftime("%a, %d %b %Y %H:%M:%S", print_time) +
                  " || " + json.dumps(tags))
            try:
                if not dry_run:
                    delete_object(snapshot)
                    time.sleep(0.3)
            except ClientError as err:
                print(colored("Delete failed: " +
                              err.response['Error']['Message'], "red"))
        else:
            print(colored("Skipping " + snapshot.id, "cyan") +
                  " || " + time.strftime("%a, %d %b %Y %H:%M:%S", print_time) +
                  " || " + json.dumps(tags))


# By default: 2 days of ten minutely, 7 days of hourly, 30 days of daily
# ~3 months of weekly, 6 months of monthly and 3 years of yearly
# 6*24*2 + 24*(7-2) + 30- 7+ + 6-1 + 2 = 438 snapshots
def prune_snapshots(volume_id=None, tag_name=None, tag_value=None,
                    ten_minutely=288, hourly=168, daily=30,
                    weekly=13, monthly=6, yearly=3, dry_run=False):
    filters = snapshot_filters(volume_id=volume_id, tag_name=tag_name,
                               tag_value=tag_value)
    time_func = lambda snapshot: snapshot.start_time
    snapshots = sorted([s for s in ec2_resource().snapshots.filter(Filters=filters)],
                       key=time_func, reverse=True)
    keep, snapshots_to_delete = prune_array(snapshots,
                                            time_func,
                                            lambda snapshot: snapshot.volume_id,
                                            ten_minutely=ten_minutely,
                                            hourly=hourly,
                                            daily=daily,
                                            weekly=weekly,
                                            yearly=yearly)
    delete_selected(snapshots, snapshots_to_delete, name_for_snap, time_func,
                    dry_run=dry_run)

def name_for_snap(snap):
    for tag in snap.tags:
        if tag["Key"] == "Name" or tag["Key"] == tag["Value"]:
            return (snap.id + " " + tag["Value"]).ljust(50)
    return snap.id.ljust(50)
