import os
import argcomplete
import argparse
import inspect
import locale
import sys
from argcomplete.completers import ChoicesCompleter, FilesCompleter
from ec2_utils.instance_info import InstanceInfo
from ec2_utils import logs
from ec2_utils import clients
from ec2_utils.clients import is_ec2

SYS_ENCODING = locale.getpreferredencoding()

NoneType = type(None)

def get_parser(formatter=None):
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

def get_userdata():
    """Get userdata defined for an instance into a file
    """
    parser = get_parser()
    parser.add_argument("file", help="File to write userdata into").completer =\
        FilesCompleter()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    dirname = os.path.dirname(args.file)
    if dirname:
        if os.path.isfile(dirname):
            parser.error(dirname + " exists and is a file")
        elif not os.path.isdir(dirname):
            os.makedirs(dirname)
    instance_info.get_userdata(args.file)
    return

def get_region():
    """ Get current default region. Defaults to the region of the instance on
    ec2 if not otherwise defined.
    """
    parser = get_parser()
    parser.parse_args()
    print(clients.region())

def get_account_id():
    """Get current account id. Either from instance metadata or current cli
    configuration.
    """
    parser = get_parser()
    parser.parse_args()
    print(instance_info.resolve_account())


def associate_eip():
    """Associate an Elastic IP for the instance that this script runs on
    """
    parser = get_parser()
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
    ec2.associate_eip(eip=args.ip, allocation_id=args.allocationid,
                           eip_param=args.eipparam,
                           allocation_id_param=args.allocationidparam)

"""
    'log-to-cloudwatch=ec2_utils.cli:log_to_cloudwatch',
"""
def logs_to_cloudwatch():
    """Read a file and send rows to cloudwatch and keep following the end for new data.
    The log group will be the stack name that created instance if not given
    as an argument. The logstream will be the instance id and filename if not
    given as an argument. Group and stream aare created if they do not exist.
    """
    parser = get_parser()
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
    ec2.send_logs_to_cloudwatch(args.file, group=args.group,
                                     stream=args.stream)

def instance_id():
    """ Get id for instance
    """
    parser = get_parser()
    argcomplete.autocomplete(parser)
    parser.parse_args()
    if is_ec2():
        info = InstanceInfo()
        print(info.instance_id())
    else:
        sys.exit(1)

foo = """
   'pytail=ec2_utils.cli:read_and_follow',
    'account-id=ec2_utils.cli:get_account_id',
    'cf-logical-id=ec2_utils.cli:logical_id',
    'cf-region=ec2_utils.cli:cf_region',
    'cf-get-parameter=ec2_utils.cli:get_parameter',
    'cf-signal-status=ec2_utils.cli:signal_cf_status',
    'cf-stack-name=ec2_utils.cli:stack_name',
    'cf-stack-id=ec2_utils.cli:stack_id',
    'instance-id=ec2_utils.cli:instance_id',
    'region=ec2_utils.cli:ec2_region',
    'wait-for-metadata=ec2_utils.cli:wait_for_metadata',
    'get-tag=ec2_utils.cli:tag',
    'get-userdata=ec2_utils.cli:get_userdata',
    'detach-volume=ec2_utils.cli:detach_volume',
    'volume-from-snapshot=ec2_utils.cli:volume_from_snapshot',
    'snapshot-from-volume=ec2_utils.cli:snapshot_from_volume',
    'show-stack-params-and-outputs=ec2_utils.cli:show_stack_params_and_outputs',
    'register-private-dns=ec2_utils.cli:cli_register_private_dns',
    'interpolate-file=ec2_utils.cli:cli_interpolate_file',
    'ecr-ensure-repo=ec2_utils.cli:cli_ecr_ensure_repo',
    'ecr-repo-uri=ec2_utils.cli:cli_ecr_repo_uri',
    'latest-snapshot=ec2_utils.volumes:latest_snapshot'
"""