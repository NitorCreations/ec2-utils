from ec2_utils.clients import ec2
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


