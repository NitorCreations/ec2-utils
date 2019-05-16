from retry import retry
from ec2_utils.clients import ec2, route53
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

def create_and_attach_eni():
    iface = ec2_resource().create_network_interface(SubnetId=subnet_id)
    if iface.status != "available":
        _retry_eni_status(iface.id)
    

@retry(tries=60, delay=2, backoff=1)        
def _retry_eni_status(eni_id):
    iface = ec2_resource().NetworkInterface(eni_id)
    if iface.status != 'available':
        raise Exception("eni " + eni_id + " not available")
    return True

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
