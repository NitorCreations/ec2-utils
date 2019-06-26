import inspect
import json
import os
import sys
import boto3
from threading import local
from ec2_utils.utils import get_retry

CLIENTS = local()
INSTANCE_IDENTITY_URL = 'http://169.254.169.254/latest/dynamic/instance-identity/document'

def get_client(client_region=None):
    if not client_region:
        client_region = region()
    caller_name = inspect.stack()[1][3]
    param_name = client_region + "_" + caller_name
    if not hasattr(CLIENTS, param_name):
        # region() has one benefit over default resolving - defaults to
        # ec2 instance region if on ec2 and otherwise unset
        setattr(CLIENTS, param_name, session().client(caller_name,
                                                      region_name=client_region))
    return getattr(CLIENTS, param_name)

def get_resource(resource_region=None):
    if not resource_region:
        resource_region = region()
    caller_name = inspect.stack()[1][3].split("_")[0]
    param_name = resource_region + "_resource_" + caller_name
    if not hasattr(CLIENTS, param_name):
        # region() has one benefit over default resolving - defaults to
        # ec2 instance region if on ec2 and otherwise unset
        setattr(CLIENTS, param_name,
                session().resource(caller_name, region_name=resource_region))
    return getattr(CLIENTS, param_name)

def ec2(region=None):
    return get_client(client_region=region)

def sts(region=None):
    return get_client(client_region=region)

def logs(region=None):
    return get_client(client_region=region)

def cloudformation(region=None):
    return get_client(client_region=region)

def cloudformation_resource(region=None):
    return get_resource(resource_region=region)

def ec2_resource(region=None):
    return get_resource(resource_region=region)

def s3(region=None):
    return get_client(client_region=region)

def s3_resource(region=None):
    return get_resource(resource_region=region)

def route53(region=None):
    return get_client(client_region=region)

def cloudfront(region=None):
    return get_client(client_region=region)

def ecr(region=None):
    return get_client(client_region=region)

def organizations(region=None):
    return get_client(client_region=region)

def session():
    if not hasattr(CLIENTS, 'session'):
        CLIENTS.session = boto3.session.Session()
    return CLIENTS.session


def region():
    """ Get default region - the region of the instance if run in an EC2 instance
    """
    # If it is set in the environment variable, use that
    if 'AWS_DEFAULT_REGION' in os.environ:
        return os.environ['AWS_DEFAULT_REGION']
    elif 'AWS_REGION' in os.environ:
        return os.environ['AWS_REGION']
    elif 'REGION' in os.environ:
        return os.environ['REGION']
    else:
        # Otherwise it might be configured in AWS credentials
        if session().region_name:
            return session().region_name
        # If not configured and being called from an ec2 instance, use the
        # region of the instance
        elif is_ec2():
            info = json.loads(get_retry(INSTANCE_IDENTITY_URL).text)
            return info['region']
        # Otherwise default to Ireland
        else:
            return 'eu-west-1'

def regions():
    return session().get_available_regions("s3")

def stacks():
    return [stack.name for stack in cloudformation_resource().stacks.all()]

def is_ec2():
    if sys.platform.startswith("win"):
        import wmi
        systeminfo = wmi.WMI().Win32_ComputerSystem()[0]
        return "EC2" == systeminfo.PrimaryOwnerName
    elif sys.platform.startswith("linux"):
        if read_if_readable("/sys/hypervisor/uuid").startswith("ec2"):
            return True
        elif read_if_readable("/sys/class/dmi/id/product_uuid").startswith("EC2"):
            return True
        elif read_if_readable("/sys/devices/virtual/dmi/id/board_vendor").startswith("Amazon EC2"):
            return True
        elif read_if_readable("/sys/devices/virtual/dmi/id/sys_vendor").startswith("Amazon EC2"):
            return True
        elif read_if_readable("/sys/devices/virtual/dmi/id/sys_vendor").startswith("Amazon EC2"):
            return True
        elif read_if_readable("/sys/devices/virtual/dmi/id/bios_vendor").startswith("Amazon EC2"):
            return True
        elif read_if_readable("/sys/devices/virtual/dmi/id/chassis_vendor").startswith("Amazon EC2"):
            return True
        elif read_if_readable("/sys/devices/virtual/dmi/id/chassis_asset_tag").startswith("Amazon EC2"):
            return True
        elif "AmazonEC2" in read_if_readable("/sys/devices/virtual/dmi/id/modalias"):
            return True 
        elif "AmazonEC2" in read_if_readable("/sys/devices/virtual/dmi/id/uevent"):
            return True
        else:
            return False


def read_if_readable(filename):
    try:
        if os.path.isfile(filename):
            with open(filename) as read_file:
                return read_file.read()
        else:
            return ""
    except:
        return ""