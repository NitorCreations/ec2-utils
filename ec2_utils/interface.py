import ctypes.util
import ctypes
import time
from retry import retry
from threadlocal_aws.clients import ec2, route53
from threadlocal_aws.resources import ec2 as ec2_resource
from ec2_utils.instance_info import info

def associate_eip(eip=None, allocation_id=None, eip_param=None,
                  allocation_id_param=None):
    if not allocation_id:
        if eip:
            address_data = ec2().describe_addresses(PublicIps=[eip])
            if 'Addresses' in address_data and \
               len(address_data['Addresses']) > 0 and \
               'AllocationId' in address_data['Addresses'][0]:
                allocation_id = address_data['Addresses'][0]['AllocationId']
    if not allocation_id:
        if not allocation_id_param:
            allocation_id_param = "paramEipAllocationId"
        allocation_id = info().stack_data(allocation_id_param)
    if not allocation_id:
        if not eip:
            if not eip_param:
                eip_param = "paramEip"
            eip = info().stack_data(eip_param)
        address_data = ec2().describe_addresses(PublicIps=[eip])
        if 'Addresses' in address_data and len(address_data['Addresses']) > 0 \
           and 'AllocationId' in address_data['Addresses'][0]:
            allocation_id = address_data['Addresses'][0]['AllocationId']
    print("Allocating " + allocation_id + " on " + info().instance_id())
    ec2().associate_address(InstanceId=info().instance_id(),
                            AllocationId=allocation_id,
                            AllowReassociation=True)
    info().clear_cache()

def create_eni(subnet_id):
    iface = ec2_resource().create_network_interface(SubnetId=subnet_id)
    return _retry_eni_status(iface.id, "available")

def get_eni(eni_id):
    return ec2_resource().NetworkInterface(eni_id)

def list_attachable_enis():
    return ec2_resource().network_interfaces.filter(Filters=[{"Name": "availability-zone",
                                                              "Values": [info().availability_zone()]},
                                                             {"Name": "status",
                                                              "Values": ["available"]}])

def list_attachable_eni_ids():
    return [eni.id for eni in list_attachable_enis()]

def list_compatible_subnets():
    return ec2_resource().subnets.filter(Filters=[{"Name": "availability-zone",
                                                   "Values": [info().availability_zone()]}])

def list_compatible_subnet_ids():
    return [subnet.id for subnet in list_compatible_subnets()]

def attach_eni(eni_id):
    iface = ec2_resource().NetworkInterface(eni_id)
    iface.attach(DeviceIndex=info().next_network_interface_index(),
                 InstanceId=info().instance_id())
    iface = _retry_eni_status(iface.id, "in-use")
    info().clear_cache()
    return iface

def detach_eni(eni_id, delete=False):
    iface = ec2_resource().NetworkInterface(eni_id)
    iface.detach()
    if iface.status != "available":
        iface = _retry_eni_status(iface.id, "available")
    time.sleep(3)
    if delete:
        iface.delete()
    info().clear_cache()

@retry(tries=60, delay=2, backoff=1)
def _retry_eni_status(eni_id, status):
    iface = ec2_resource().NetworkInterface(eni_id)
    if iface.status != status:
        raise Exception("eni " + eni_id + " not " + status)
    return iface

def register_private_dns(dns_name, hosted_zone, ttl=None, private_ip=None):
    if not ttl:
        ttl=60
    else:
        ttl=int(ttl)

    if not private_ip:
        private_ip = info().private_ip()

    zone_id = None
    zone_paginator = route53().get_paginator("list_hosted_zones")
    for page in zone_paginator.paginate():
        for zone in page.get("HostedZones", []):
            if zone["Name"] == hosted_zone:
                zone_id = zone['Id']
                break
        if zone_id:
            break
    if not zone_id:
        raise Exception("Failed to get zone id for zone " + hosted_zone)
    route53().change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch={
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": dns_name,
                    "Type": "A",
                    "TTL": ttl,
                    "ResourceRecords": [
                        {
                            "Value": private_ip
                        }
                    ]
                }
            }
        ]})

