import os
import argcomplete
import argparse
import inspect
import json
import locale
import sys
import time
from datetime import datetime, timedelta
from dateutil.tz import tzutc
from argcomplete.completers import ChoicesCompleter, FilesCompleter
from ec2_utils.instance_info import info
from ec2_utils import logs, ebs, s3, interface, instance_info, utils
from ec2_utils.s3 import prune_s3_object_versions
from threadlocal_aws import is_ec2, region as client_region

SYS_ENCODING = locale.getpreferredencoding()

NoneType = type(None)

dthandler = lambda obj: obj.isoformat() if hasattr(obj, 'isoformat') else json.JSONEncoder().default(obj)

def account_id():
    """Get current account id. Either from instance metadata or current cli
    configuration.
    """
    parser = _get_parser()
    parser.parse_args()
    print(instance_info.resolve_account())

def associate_eip():
    """Associate an Elastic IP for the instance that this script runs on
    """
    parser = _get_parser()
    parser.add_argument("-i", "--ip", help="Elastic IP to allocate - default" +
                                           " is to get paramEip from the stack" +
                                           " that created this instance")
    parser.add_argument("-a", "--allocationid", help="Elastic IP allocation " +
                                                     "id to allocate - " +
                                                     "default is to get " +
                                                     "paramEipAllocationId " +
                                                     "from the stack " +
                                                     "that created this instance")
    parser.add_argument("-e", "--eipparam", help="Parameter to look up for " +
                                                 "Elastic IP in the stack - " +
                                                 "default is paramEip",
                        default="paramEip")
    parser.add_argument("-p", "--allocationidparam", help="Parameter to look" +
                                                          " up for Elastic " +
                                                          "IP Allocation ID " +
                                                          "in the stack - " +
                                                          "default is " +
                                                          "paramEipAllocatio" +
                                                          "nId",
                        default="paramEipAllocationId")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    interface.associate_eip(eip=args.ip, allocation_id=args.allocationid,
                            eip_param=args.eipparam,
                            allocation_id_param=args.allocationidparam)

def attach_eni():
    """ Optionally create and attach an elastic network interface
    """
    parser = _get_parser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-s", "--subnet", help="Subnet for the elastic " +\
                       "network inferface if one is " +\
                       "created. Needs to " +\
                       "be on the same availability " +\
                       "zone as the instance.").completer = ChoicesCompleter(interface.list_compatible_subnet_ids())
    group.add_argument("-i", "--eni-id", help="Id of the eni to attach, if " +\
                       "attaching an existing eni.").completer = ChoicesCompleter(interface.list_attachable_eni_ids())
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if args.subnet:
        iface = interface.create_eni(args.subnet)
    elif args.eni_id:
        iface = interface.get_eni(args.eni_id)
    else:
        iface = interface.create_eni(info().subnet_id())
    interface.attach_eni(iface.id)
    print(iface.id)

def availability_zone():
    """ Get availability zone for the instance
    """
    parser = _get_parser()
    argcomplete.autocomplete(parser)
    parser.parse_args()
    if is_ec2():
        print(info().availability_zone())
    else:
        parser.error("Only makes sense on an EC2 instance cretated from a CF stack")

def cf_logical_id():
    """ Get the logical id that is expecting a signal from this instance
    """
    parser = _get_parser()
    argcomplete.autocomplete(parser)
    parser.parse_args()
    if is_ec2():
        print(info().logical_id())
    else:
        parser.error("Only makes sense on an EC2 instance cretated from a CF stack")

def cf_region():
    """ Get region of the stack that created this instance
    """
    parser = _get_parser()
    argcomplete.autocomplete(parser)
    parser.parse_args()
    if is_ec2():
        print(info().stack_id().split(":")[3])
    else:
        parser.error("Only makes sense on an EC2 instance cretated from a CF stack")

def cf_get_parameter():
    """Get a parameter value from the stack
    """
    parser = _get_parser()
    parser.add_argument("parameter", help="The name of the parameter to print")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    print(info().stack_data(args.parameter))

def cf_signal_status():
    """Signal CloudFormation status to a logical resource in CloudFormation
    that is either given on the command line or resolved from CloudFormation
    tags
    """
    parser = _get_parser()
    parser.add_argument("status",
                        help="Status to indicate: SUCCESS | FAILURE").completer\
        = ChoicesCompleter(("SUCCESS", "FAILURE"))
    parser.add_argument("-r", "--resource", help="Logical resource name to " +
                                                 "signal. Looked up from " +
                                                 "cloudformation tags by " +
                                                 "default")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if args.status != "SUCCESS" and args.status != "FAILURE":
        parser.error("Status needs to be SUCCESS or FAILURE")
    instance_info.signal_status(args.status, resource_name=args.resource)

def cf_stack_name():
    """ Get name of the stack that created this instance
    """
    parser = _get_parser()
    argcomplete.autocomplete(parser)
    parser.parse_args()
    if is_ec2():
        print(info().stack_name())
    else:
        parser.error("Only makes sense on an EC2 instance cretated from a CF stack")

def cf_stack_id():
    """ Get id of the stack the creted this instance
    """
    parser = _get_parser()
    argcomplete.autocomplete(parser)
    parser.parse_args()
    if is_ec2():
        print(info().stack_id())
    else:
        parser.error("Only makes sense on an EC2 instance cretated from a CF stack")

def clean_snapshots():
    """Clean snapshots that are older than a number of days (30 by default) and
    have one of specified tag values
    """
    parser = _get_parser()
    parser.add_argument("-t", "--days", help="The number of days that is the" +
                                             "minimum age for snapshots to " +
                                             "be deleted", type=int, default=30)
    parser.add_argument("-d", "--dry-run", action="store_true",
                        help="Do not delete, but print what would be deleted")
    parser.add_argument("tags", help="The tag values to select deleted " +
                                     "snapshots", nargs="+")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ebs.clean_snapshots(args.days, args.tags, dry_run=args.dry_run)

def create_eni():
    """ create an elastic network interface
    """
    parser = _get_parser()
    parser.add_argument("-s", "--subnet", help="Subnet for the elastic " +\
                                               "network inferface if one is " +\
                                               "created. Needs to " +\
                                               "be on the same availability " +\
                                               "zone as the instance.").completer = ChoicesCompleter(interface.list_compatible_subnet_ids())
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if not args.subnet:
        args.subnet = info().subnet_id()
    iface = interface.create_eni(args.subnet)
    print(iface.id)

def detach_eni():
    """ Detach an eni from this instance
    """
    parser = _get_parser()
    parser.add_argument("-i", "--eni-id", help="Eni id to detach").completer = ChoicesCompleter(info().network_interface_ids())
    parser.add_argument("-d", "--delete", help="Delete eni after detach", action="store_true")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    interface.detach_eni(args.eni_id, delete=args.delete)    

def detach_volume():
    """ Create a snapshot of a volume identified by it's mount path
    """
    parser = _get_parser()
    parser.add_argument("mount_path", help="Mount point of the volume to be detached").completer = FilesCompleter()
    parser.add_argument("-d", "--delete", help="Delete volume after detaching",
                        action="store_true")
    parser.add_argument("-i", "--volume-id", help="Volume id to detach").completer = ChoicesCompleter(info().volume_ids())
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if is_ec2():
        ebs.detach_volume(args.mount_path, delete_volume=args.delete)
    else:
        parser.error("Only makes sense on an EC2 instance")

def get_tag():
    """ Get the value of a tag for an ec2 instance
    """
    parser = _get_parser()
    parser.add_argument("name", help="The name of the tag to get")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if is_ec2():
        value = info().tag(args.name)
        if value is not None:
            print(value)
        else:
            sys.exit("Tag " + args.name + " not found")
    else:
        parser.error("Only makes sense on an EC2 instance")

def get_userdata():
    """Get userdata defined for an instance into a file
    """
    parser = _get_parser()
    parser.add_argument("file", help="File to write userdata into. '-' " + \
                                     "for stdout").completer =FilesCompleter()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if args.file != "-":
        dirname = os.path.dirname(args.file)
        if dirname:
            if os.path.isfile(dirname):
                parser.error(dirname + " exists and is a file")
            elif not os.path.isdir(dirname):
                os.makedirs(dirname)
    instance_info.get_userdata(args.file)
    return

def instance_id():
    """ Get id for instance
    """
    parser = _get_parser()
    argcomplete.autocomplete(parser)
    parser.parse_args()
    if is_ec2():
        print(info().instance_id())
    else:
        parser.error("Only makes sense on an EC2 instance")

def latest_snapshot():
    """Get the latest snapshot with a given tag
    """
    parser = _get_parser()
    parser.add_argument("tag", help="The tag to find snapshots with")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    snapshot = ebs.get_latest_snapshot(args.tag, args.tag)
    if snapshot:
        print(snapshot.id)
    else:
        sys.exit(1)

def list_attachable_enis():
    """ List all enis in the same availability-zone, i.e. ones that can be attached
    to this instance.
    """
    parser = _get_parser()
    argcomplete.autocomplete(parser)
    parser.parse_args()
    if is_ec2():
        for eni_id in interface.list_attachable_eni_ids():
            print(eni_id) 
    else:
        parser.error("Only makes sense on an EC2 instance")

def list_attached_enis():
    """ List all enis in the same availability-zone, i.e. ones that can be attached
    to this instance.
    """
    parser = _get_parser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--ip-address", help="Include first private ip addresses for the interfaces in the output", action="store_true")
    group.add_argument("-f", "--full", help="Print all available data about attached enis as json", action="store_true")    
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if is_ec2():
        enis = info().network_interfaces()
        if args.full:
            print(json.dumps(enis, indent=2, default=dthandler))
        else:
            for eni in enis:
                ip_addr = ":" + eni["PrivateIpAddresses"][0]["PrivateIpAddress"] \
                    if args.ip_address and "PrivateIpAddresses" in eni and \
                    eni["PrivateIpAddresses"] and "PrivateIpAddress" in \
                    eni["PrivateIpAddresses"][0] else ""
                print(eni["NetworkInterfaceId"] + ip_addr)
    else:
        parser.error("Only makes sense on an EC2 instance")

def list_attached_volumes():
    """ List attached volumes
    """
    parser = _get_parser()
    argcomplete.autocomplete(parser)
    _ = parser.parse_args()
    if is_ec2():
        for volume_id in info().volume_ids():
            print(volume_id)
    else:    
        parser.error("Only makes sense on an EC2 instance")


def list_compatible_subnets():
    """ List all subnets in the same availability-zone, i.e. ones that can have
    ENIs that can be attached to this instance.
    """
    parser = _get_parser()
    argcomplete.autocomplete(parser)
    parser.parse_args()
    if is_ec2():
        for subnet_id in interface.list_compatible_subnet_ids():
            print(subnet_id) 
    else:
        parser.error("Only makes sense on an EC2 instance")

def list_local_interfaces():
    """ List local interfaces
    """
    parser = _get_parser()
    parser.add_argument("-j", "--json", help="Output in json format", action="store_true")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    to_print={}
    for iface in interface.get_network_interfaces():
        if args.json:
            to_print[iface.name] = { "index": iface.index,
                                     "ipv4":  iface.addresses.get(interface.AF_INET),
                                     "ipv6": iface.addresses.get(interface.AF_INET6) }
        else:
            print(iface)
    if to_print:
        print(json.dumps(to_print, indent=2))

def list_tags():
    """ List all tags associated with the instance
    """
    parser = _get_parser()
    argcomplete.autocomplete(parser)
    parser.parse_args()
    if is_ec2():
        for key, value in info().tags().items():
            print(key + "=" + value) 
    else:
        parser.error("Only makes sense on an EC2 instance")

def log_to_cloudwatch():
    """Read a file and send rows to cloudwatch and keep following the end for new data.
    The log group will be the stack name that created instance if not given
    as an argument. The logstream will be the instance id and filename if not
    given as an argument. Group and stream aare created if they do not exist.
    """
    parser = _get_parser()
    parser.add_argument("file", help="File to follow").completer = FilesCompleter()
    parser.add_argument("-g", "--group", help="Log group to log to. Defaults" +\
                                              " to the stack name that " +\
                                              "created the instance if not " +\
                                              "given and instance is created" +\
                                              " with a CloudFormation stack")
    parser.add_argument("-s", "--stream", help="The log stream name to log" + \
                                               " to. The instance id and " + \
                                               "filename if not given")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    logs.send_log_to_cloudwatch(args.file, group=args.group, stream=args.stream)

def get_logs():
    """Get logs from multiple CloudWatch log groups and possibly filter them.
    """
    parser = _get_parser()
    parser.add_argument("log_group_pattern", help="Regular expression to filter log groups with")
    parser.add_argument("-f", "--filter", help="CloudWatch filter pattern")
    parser.add_argument("-s", "--start", help="Start time (x m|h|d|w ago | now | <seconds since epoc>)", nargs="+")
    parser.add_argument("-e", "--end", help="End time (x m|h|d|w ago | now | <seconds since epoc>)", nargs="+")
    parser.add_argument("-o", "--order", help="Best effort ordering of log entries", action="store_true")
    parser.usage = "ndt logs log_group_pattern [-h] [-f FILTER] [-s START [START ...]] [-e END [END ...]] [-o]"
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    cwlogs_groups = logs.CloudWatchLogsGroups(
        log_group_filter=args.log_group_pattern,
        log_filter=args.filter,
        start_time=' '.join(args.start) if args.start else None,
        end_time=' '.join(args.end) if args.end else None,
        sort=args.order
    )
    cwlogs_groups.get_logs()

def read_and_follow():
    """Read and print a file and keep following the end for new data
    """
    parser = _get_parser()
    parser.add_argument("file", help="File to follow").completer = FilesCompleter()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if not os.path.isfile(args.file):
        parser.error(args.file + " not found")
    logs.read_and_follow(args.file, sys.stdout.write)

def prune_snapshots():
    """ Prune snapshots to have a specified amout of daily, weekly, monthly
    and yearly snapshots
    """
    parser = _get_parser()
    parser.add_argument('-v', '--volume-id', type=str,
                        help='EBS Volume ID, if wanted for only one volume')
    parser.add_argument('-n', '--tag-name', type=str,
                        help='Snapshot tag name', nargs='*')
    parser.add_argument('-t', '--tag-value', type=str,
                        help='Snapshot tag value', nargs='*')

    parser.add_argument('-M', '--ten-minutely', type=int,
                        help='Number of ten minutely snapshots to keep. ' + \
                             'Defaults to two days of these.', default=288)
    parser.add_argument('-H', '--hourly', type=int,
                        help='Number of hourly snapshots to keep. ' +\
                             'Defaults to a week of these.', default=168)
    parser.add_argument('-d', '--daily', type=int,
                        help='Number of daily snapshots to keep. ' +\
                             'Defaults to a month of these.', default=30)
    parser.add_argument('-w', '--weekly', type=int,
                        help='Number of weekly snapshots to keep. ' +\
                             'Defaults to 3 months of these.', default=13)
    parser.add_argument('-m', '--monthly', type=int,
                        help='Number of monthly snapshots to keep. ' +\
                             'Defaults to a year of these.', default=12)
    parser.add_argument('-y', '--yearly', type=int,
                        help='Number of yearly snapshots to keep. ' +\
                             'Defaults to three years.', default=3)

    parser.add_argument('-r', '--dry-run', action='store_true',
                        help='Dry run - print actions that would be taken')

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ebs.prune_snapshots(**vars(args))

def prune_object_versions():
    """ Prune s3 object versions to have a specified amout of daily, weekly, monthly
    and yearly versions
    """
    parser = _get_parser()
    parser.add_argument('bucket', type=str, help='Bucket to prune')
    parser.add_argument('-p', '--prefix', type=str,
                        help='Limit pruning to a prefix', default="")

    parser.add_argument('-M', '--ten-minutely', type=int,
                        help='Number of ten minutely object versions to keep. ' +\
                             'Defaults to two days of these.', default=288)
    parser.add_argument('-H', '--hourly', type=int,
                        help='Number of hourly object versions to keep. ' +\
                             'Defaults to a week of these.', default=168)
    parser.add_argument('-d', '--daily', type=int,
                        help='Number of daily object versions to keep. ' +\
                             'Defaults to a month of these.', default=30)
    parser.add_argument('-w', '--weekly', type=int,
                        help='Number of weekly object versions to keep. ' +\
                             'Defaults to 3 months of these.', default=13)
    parser.add_argument('-m', '--monthly', type=int,
                        help='Number of monthly object versions to keep. ' +\
                             'Defaults to a year of these.', default=12)
    parser.add_argument('-y', '--yearly', type=int,
                        help='Number of yearly object versions to keep. ' +\
                             'Defaults to three years.', default=3)

    parser.add_argument('-r', '--dry-run', action='store_true',
                        help='Dry run - print actions that would be taken')

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    prune_s3_object_versions(**vars(args))

def region():
    """ Get current default region. Defaults to the region of the instance on
    ec2 if not otherwise defined.
    """
    parser = _get_parser()
    parser.parse_args()
    print(client_region())

def register_private_dns():
    """ Register local private IP in route53 hosted zone usually for internal
    use.
    """
    parser = _get_parser()
    parser.add_argument("dns_name", help="The name to update in route 53")
    parser.add_argument("hosted_zone", help="The name of the hosted zone to update")
    parser.add_argument("-t", "--ttl", help="Time to live for the record. 60 by default",
                        default="60")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    interface.register_private_dns(args.dns_name, args.hosted_zone, ttl=args.ttl)

def snapshot_from_volume():
    """ Create a snapshot of a volume identified by it's mount path
    """
    parser = _get_parser()
    parser.add_argument("-w", "--wait", help="Wait for the snapshot to finish" +
                        " before returning",
                        action="store_true")
    parser.add_argument("tag_key", help="Key of the tag to find volume with")
    parser.add_argument("tag_value", help="Value of the tag to find volume with")
    parser.add_argument("mount_path", help="Where to mount the volume")
    parser.add_argument("-c", "--copytags", nargs="*", help="Tag to copy to the snapshot from instance. Multiple values allowed.")
    parser.add_argument("-t", "--tags", nargs="*", help="Tag to add to the snapshot in the format name=value. Multiple values allowed.")
    parser.add_argument("-i", "--ignore-missing-copytags", action="store_true", help="If set, missing copytags are ignored.")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    tags = {}
    if args.tags:
        for tag in args.tags:
            try:
                key, value = tag.split('=', 1)
                tags[key] = value
            except ValueError:
                parser.error("Invalid tag/value input: " + tag)
    if is_ec2():
        print(ebs.create_snapshot(args.tag_key, args.tag_value,
                                  args.mount_path, wait=args.wait, tags=tags,
                                  copytags=args.copytags,
                                  ignore_missing_copytags=args.ignore_missing_copytags))
    else:
        parser.error("Only makes sense on an EC2 instance")

def stack_params_and_outputs():
    """ Show stack parameters and outputs as a single json documents
    """
    parser = _get_parser()
    parser.add_argument("-p", "--parameter", help="Name of paremeter if only" +
                                                  " one parameter required")
    parser.add_argument("-s", "--stack-name", help="The name of the stack to show",
                        default=info().stack_name()).completer = \
        ChoicesCompleter(_best_effort_stacks())
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    resp, _ = instance_info.stack_params_and_outputs_and_stack(stack_name=args.stack_name)
    if args.parameter:
        if args.parameter in resp:
            print(resp[args.parameter])
        else:
            parser.error("Parameter " + args.parameter + " not found")
    else:
        print(json.dumps(resp, indent=2))

def _best_effort_stacks():
    try:
        return stacks()
    except:
        return []

def subnet_id():
    """ Get subnet id for instance
    """
    parser = _get_parser()
    argcomplete.autocomplete(parser)
    parser.parse_args()
    if is_ec2():
        print(info().subnet_id())
    else:
        parser.error("Only makes sense on an EC2 instance")

def volume_from_snapshot():
    """ Create a volume from an existing snapshot and mount it on the given
    path. The snapshot is identified by a tag key and value. If no tag is
    found, an empty volume is created, attached, formatted and mounted.
    """
    parser = _get_parser()
    parser.add_argument("tag_key", help="Key of the tag to find volume with")
    parser.add_argument("tag_value", help="Value of the tag to find volume with")
    parser.add_argument("mount_path", help="Where to mount the volume")
    parser.add_argument("size_gb", nargs="?", help="Size in GB for the volum" +
                                                   "e. If different from sna" +
                                                   "pshot size, volume and " +
                                                   "filesystem are resized",
                        default=None, type=int)
    parser.add_argument("-n", "--no_delete_on_termination",
                        help="Whether to skip deleting the volume on termi" +
                             "nation, defaults to false", action="store_true")
    parser.add_argument("-c", "--copytags", nargs="*", help="Tag to copy to the volume from instance. Multiple values allowed.")
    parser.add_argument("-t", "--tags", nargs="*", help="Tag to add to the volume in the format name=value. Multiple values allowed.")
    parser.add_argument("-i", "--ignore-missing-copytags", action="store_true", help="If set, missing copytags are ignored.")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    tags = {}
    if args.tags:
        for tag in args.tags:
            try:
                key, value = tag.split('=', 1)
                tags[key] = value
            except ValueError:
                parser.error("Invalid tag/value input: " + tag)
    if is_ec2():
        ebs.volume_from_snapshot(args.tag_key, args.tag_value, args.mount_path,
                                 size_gb=args.size_gb,
                                 del_on_termination=not args.no_delete_on_termination,
                                 copytags=args.copytags, tags=tags,
                                 ignore_missing_copytags=args.ignore_missing_copytags)
    else:
        parser.error("Only makes sense on an EC2 instance")

def wait_for_metadata():
    """ Waits for metadata service to be available. All errors are ignored until
    time expires or a socket can be established to the metadata service """
    parser = _get_parser()
    parser.add_argument('--timeout', '-t', type=int, help="Maximum time to wait in seconds for the metadata service to be available", default=300)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    start = datetime.utcnow().replace(tzinfo=tzutc())
    cutoff = start + timedelta(seconds=args.timeout)
    timeout = args.timeout
    connected = False
    while not connected:
        try:
            connected = utils.wait_net_service("169.254.169.254", 80, timeout)
        except:
            pass
        if datetime.utcnow().replace(tzinfo=tzutc()) >= cutoff:
            print("Timed out waiting for metadata service")
            sys.exit(1)
        time.sleep(1)
        timeout = max(1, args.timeout - (datetime.utcnow().replace(tzinfo=tzutc()) - start).total_seconds())


def _get_parser(formatter=None):
    func_name = inspect.stack()[1][3]
    caller = sys._getframe().f_back
    func = caller.f_locals.get(
        func_name, caller.f_globals.get(
            func_name
        )
    )
    if formatter:
        return argparse.ArgumentParser(formatter_class=formatter, description=func.__doc__)
    else:
        return argparse.ArgumentParser(description=func.__doc__)
