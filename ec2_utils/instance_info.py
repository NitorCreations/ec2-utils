import json
import os
from os.path import expanduser
from requests.exceptions import ConnectionError
import tempfile
import time
from botocore.exceptions import ClientError, EndpointConnectionError
from ec2_utils.utils import get_retry, wait_net_service
from threadlocal_aws import INSTANCE_IDENTITY_URL, is_ec2, region
from threadlocal_aws.clients import ec2, sts, cloudformation
from retry import retry

ACCOUNT_ID = None
INSTANCE_DATA = tempfile.gettempdir() + os.sep + 'instance-data.json'
USER_DATA_URL = 'http://169.254.169.254/latest/user-data'
INFO = None

dthandler = lambda obj: obj.isoformat() if hasattr(obj, 'isoformat') else json.JSONEncoder().default(obj)

def info():
    global INFO
    if not INFO:
        INFO = InstanceInfo()
    return INFO


def resolve_account():
    global ACCOUNT_ID
    if not ACCOUNT_ID:
        try:
            ACCOUNT_ID = sts().get_caller_identity()['Account']
        except BaseException:
            pass
    return ACCOUNT_ID


def set_region():
    """ Sets the environment variable AWS_DEFAULT_REGION if not already set
        to a sensible default
    """
    if 'AWS_DEFAULT_REGION' not in os.environ:
        os.environ['AWS_DEFAULT_REGION'] = region()


def get_userdata(outfile):
    response = get_retry(USER_DATA_URL)
    if outfile == "-":
        print(response.text)
    else:
        with open(outfile, 'w') as outf:
            outf.write(response.text)


class InstanceInfo(object):
    """ A class to get the relevant metadata for an instance running in EC2
        firstly from the metadata service and then from EC2 tags and then
        from the CloudFormation template that created this instance

        The info is then cached in $TMP/instance-data.json
    """
    _info = {}

    def stack_name(self):
        if 'stack_name' in self._info:
            return self._info['stack_name']
        else:
            return None

    def stack_id(self):
        if 'stack_id' in self._info:
            return self._info['stack_id']
        else:
            return None

    def subnet_id(self):
        if 'SubnetId' in self._info:
            return self._info['SubnetId']
        else:
            return None

    def instance_id(self):
        if 'instanceId' in self._info:
            return self._info['instanceId']
        else:
            return None

    def region(self):
        if 'region' in self._info:
            return self._info['region']
        else:
            return None

    def initial_status(self):
        if 'initial_status' in self._info:
            return self._info['initial_status']
        else:
            return None

    def logical_id(self):
        if 'logical_id' in self._info:
            return self._info['logical_id']
        else:
            return None

    def availability_zone(self):
        if 'availabilityZone' in self._info:
            return self._info['availabilityZone']
        else:
            return None
    def network_interfaces(self):
        if 'NetworkInterfaces' in self._info:
            return self._info["NetworkInterfaces"]
        else:
            return []

    def network_interface_ids(self):
        if self.network_interfaces():
            return [eni["NetworkInterfaceId"] for eni in 
                    sorted(self.network_interfaces(), key=lambda ni: ni["Attachment"]["DeviceIndex"])]
        else:
            return []

    def volumes(self):
        if 'BlockDeviceMappings' in self._info:
            return self._info['BlockDeviceMappings']
        else:
            return []

    def volume_ids(self):
        if self.volumes():
            return [ebs['Ebs']['VolumeId'] for ebs in self.volumes() if "Ebs" in ebs]

    def next_network_interface_index(self):
        iface = None
        if 'NetworkInterfaces' in self._info:
            iface = max(self._info["NetworkInterfaces"], key=lambda ni: ni["Attachment"]["DeviceIndex"])
        if iface:
            return iface["Attachment"]["DeviceIndex"] + 1
        return 0

    def private_ip(self):
        if 'privateIp' in self._info:
            return self._info['privateIp']
        else:
            return None

    def tag(self, name):
        if 'Tags' in self._info and name in self._info['Tags']:
            return self._info['Tags'][name]
        else:
            return None

    def tags(self):
        if 'Tags' in self._info:
            return self._info['Tags']
        else:
            return None

    def clear_cache(self):
        if os.path.isfile(INSTANCE_DATA):
            os.remove(INSTANCE_DATA)
        self._info = None
        self.__init__()

    def __init__(self):
        if os.path.isfile(INSTANCE_DATA) and \
           time.time() - os.path.getmtime(INSTANCE_DATA) < 900:
            try:
                self._info = json.load(open(INSTANCE_DATA))
            except BaseException:
                pass
        if not self._info and is_ec2():
            try:
                if not wait_net_service("169.254.169.254", 80, 120):
                    raise Exception("Failed to connect to instance identity service")
                response = get_retry(INSTANCE_IDENTITY_URL)
                self._info = json.loads(response.text)
                os.environ['AWS_DEFAULT_REGION'] = self.region()
                instance_info = {}
                try:
                    instance_info = _get_instance_info(self._info["instanceId"])
                except ClientError:
                    pass
                if instance_info:
                    self._info.update(instance_info)
                tags = {}
                tag_response = { 'Tags': [] }
                try:
                    tag_response = self._get_tag_response()
                except ClientError:
                    pass
                for tag in tag_response['Tags']:
                    tags[tag['Key']] = tag['Value']
                self._info['Tags'] = tags
                if 'aws:cloudformation:stack-name' in self._info['Tags']:
                    self._info['stack_name'] = tags['aws:cloudformation:stack-name']
                if 'aws:cloudformation:stack-id' in self._info['Tags']:
                    self._info['stack_id'] = tags['aws:cloudformation:stack-id']
                if self.stack_name():
                    stack_parameters, stack = stack_params_and_outputs_and_stack(stack_name=self.stack_name())
                    self._info['StackData'] = stack_parameters
                    self._info['FullStackData'] = stack
            except ConnectionError:
                self._info = {}
            info_file = None
            info_file_dir = tempfile.gettempdir()
            info_file_parent = os.path.dirname(info_file_dir)
            if not os.path.isdir(info_file_dir) and os.access(info_file_parent, os.W_OK):
                os.makedirs(info_file_dir)
            if not os.access(info_file_dir, os.W_OK):
                home = expanduser("~")
                info_file_dir = home + os.sep + ".ndt"
            if not os.path.isdir(info_file_dir) and os.access(info_file_parent, os.W_OK):
                os.makedirs(info_file_dir)
            if os.access(info_file_dir, os.W_OK):
                info_file = info_file_dir + os.sep + 'instance-data.json'
                with open(info_file, 'w') as outf:
                    outf.write(json.dumps(self._info, skipkeys=True, indent=2, default=dthandler))
                    try:
                        os.chmod(info_file, 0o666)
                        os.chmod(info_file_dir, 0o777)
                    except BaseException:
                        pass
        if self.region():
            os.environ['AWS_DEFAULT_REGION'] = self.region()
        if 'FullStackData' in self._info and 'StackStatus' in self._info['FullStackData']:
            self._info['initial_status'] = self._info['FullStackData']['StackStatus']
        if 'Tags' in self._info:
            tags = self._info['Tags']
            if 'aws:cloudformation:stack-name' in tags:
                self._info['stack_name'] = tags['aws:cloudformation:stack-name']
            if 'aws:cloudformation:stack-id' in tags:
                self._info['stack_id'] = tags['aws:cloudformation:stack-id']
            if 'aws:cloudformation:logical-id' in tags:
                self._info['logical_id'] = tags['aws:cloudformation:logical-id']

    @retry((ConnectionError, EndpointConnectionError), tries=20, delay=1)
    def _get_tag_response(self):
        return ec2().describe_tags(Filters=[{'Name': 'resource-id',
                                             'Values': [self.instance_id()]}])
    def stack_data_dict(self):
        if 'StackData' in self._info:
            return self._info['StackData']

    def stack_data(self, name):
        if 'StackData' in self._info:
            if name in self._info['StackData']:
                return self._info['StackData'][name]
        return ''

    def __str__(self):
        return json.dumps(self._info, skipkeys=True, default=dthandler)

@retry((ConnectionError, EndpointConnectionError), tries=10, delay=1)
def _get_stack(stack_name, stack_region=None):
    ret = cloudformation(region=stack_region).describe_stacks(StackName=stack_name)
    if "Stacks" in ret and ret["Stacks"]:
        return ret["Stacks"][0]

@retry((ConnectionError, EndpointConnectionError), tries=5, delay=1, backoff=1.5)
def _get_stack_resources(stack_name, stack_region=None):
    return cloudformation(region=stack_region).describe_stack_resources(StackName=stack_name)

@retry((ConnectionError, EndpointConnectionError), tries=10, delay=1, backoff=1.5)
def _get_instance_info(instance_id):
    resp = ec2().describe_instances(InstanceIds=[instance_id])
    if "Reservations" in resp and resp["Reservations"] and  \
       "Instances" in resp["Reservations"][0] and resp["Reservations"][0]["Instances"]:
        return resp["Reservations"][0]["Instances"][0]

def stack_params_and_outputs_and_stack(stack_name=None, stack_region=None):
    """ Get parameters and outputs from a stack as a single dict and the full stack
    """
    stack = {}
    resources = {}
    try:
        stack = _get_stack(stack_name, stack_region=stack_region)
    except ClientError:
        pass
    if not stack:
        return {}, {}

    try:
        resources = _get_stack_resources(stack_name, stack_region=stack_region)
    except ClientError:
        pass
    resp = {}
    if 'CreationTime' in stack:
        stack['CreationTime'] = time.strftime("%a, %d %b %Y %H:%M:%S +0000",
                                              stack['CreationTime'].timetuple())
    if 'LastUpdatedTime' in stack:
        stack['LastUpdatedTime'] = time.strftime("%a, %d %b %Y %H:%M:%S +0000",
                                                 stack['LastUpdatedTime'].timetuple())
    if "StackResources" in resources:
        for resource in resources["StackResources"]:
            resp[resource['LogicalResourceId']] = resource['PhysicalResourceId']
    if 'Parameters' in stack:
        for param in stack['Parameters']:
            resp[param['ParameterKey']] = param['ParameterValue']
    if 'Outputs' in stack:
        for output in stack['Outputs']:
            resp[output['OutputKey']] = output['OutputValue']
    return resp, stack

def signal_status(status, resource_name=None):
    if not resource_name:
        resource_name = info().logical_id()
    print("Signalling " + status + " for " + info().stack_name() + "." \
          + resource_name)
    cloudformation().signal_resource(StackName=info().stack_name(),
                                     LogicalResourceId=resource_name,
                                     UniqueId=info().instance_id(),
                                     Status=status)
