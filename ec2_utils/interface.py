import ctypes.util
import ctypes
from socket import AF_INET, AF_INET6, inet_ntop
import time
from ctypes import (
    Structure, Union, POINTER,
    pointer, get_errno, cast,
    c_ushort, c_byte, c_void_p, c_char_p, c_uint, c_uint16, c_uint32
)
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

def register_private_dns(dns_name, hosted_zone, ttl=None):
    if not ttl:
        ttl=60
    else:
        ttl=int(ttl)
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
                            "Value": info().private_ip()
                        }
                    ]
                }
            }
        ]})


class struct_sockaddr(Structure):
    _fields_ = [
        ('sa_family', c_ushort),
        ('sa_data', c_byte * 14),]

class struct_sockaddr_in(Structure):
    _fields_ = [
        ('sin_family', c_ushort),
        ('sin_port', c_uint16),
        ('sin_addr', c_byte * 4)]

class struct_sockaddr_in6(Structure):
    _fields_ = [
        ('sin6_family', c_ushort),
        ('sin6_port', c_uint16),
        ('sin6_flowinfo', c_uint32),
        ('sin6_addr', c_byte * 16),
        ('sin6_scope_id', c_uint32)]

class union_ifa_ifu(Union):
    _fields_ = [
        ('ifu_broadaddr', POINTER(struct_sockaddr)),
        ('ifu_dstaddr', POINTER(struct_sockaddr)),]

class struct_ifaddrs(Structure):
    pass
struct_ifaddrs._fields_ = [
    ('ifa_next', POINTER(struct_ifaddrs)),
    ('ifa_name', c_char_p),
    ('ifa_flags', c_uint),
    ('ifa_addr', POINTER(struct_sockaddr)),
    ('ifa_netmask', POINTER(struct_sockaddr)),
    ('ifa_ifu', union_ifa_ifu),
    ('ifa_data', c_void_p),]

libc = ctypes.CDLL(ctypes.util.find_library('c'))

def ifap_iter(ifap):
    ifa = ifap.contents
    while True:
        yield ifa
        if not ifa.ifa_next:
            break
        ifa = ifa.ifa_next.contents

def getfamaddr(sa):
    family = sa.sa_family
    addr = None
    if family == AF_INET:
        sa = cast(pointer(sa), POINTER(struct_sockaddr_in)).contents
        addr = inet_ntop(family, sa.sin_addr)
    elif family == AF_INET6:
        sa = cast(pointer(sa), POINTER(struct_sockaddr_in6)).contents
        addr = inet_ntop(family, sa.sin6_addr)
    return family, addr

class NetworkInterface(object):
    def __init__(self, name):
        self.name = name
        self.index = libc.if_nametoindex(name.encode("utf-8"))
        self.addresses = {}

    def __str__(self):
        return "%s [index=%d, IPv4=%s, IPv6=%s]" % (
            self.name, self.index,
            self.addresses.get(AF_INET),
            self.addresses.get(AF_INET6))

def get_network_interfaces():
    ifap = POINTER(struct_ifaddrs)()
    result = libc.getifaddrs(pointer(ifap))
    if result != 0:
        raise OSError(get_errno())
    del result
    try:
        retval = {}
        for ifa in ifap_iter(ifap):
            name = ifa.ifa_name.decode("UTF-8")
            i = retval.get(name)
            if not i:
                i = retval[name] = NetworkInterface(name)
            family, addr = getfamaddr(ifa.ifa_addr.contents)
            if addr:
                if family not in i.addresses:
                    i.addresses[family] = list()
                i.addresses[family].append(addr)
        key_func = lambda ni: ni.index
        return sorted(retval.values(), key=key_func)
    finally:
        libc.freeifaddrs(ifap)
