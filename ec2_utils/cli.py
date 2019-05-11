import os
import argcomplete
import argparse
import inspect
import locale
import sys
from argcomplete.completers import ChoicesCompleter, FilesCompleter
from ec2_utils.instance_info import info, InstanceInfo
from ec2_utils import logs, clients, ebs, s3, interface

from ec2_utils.clients import is_ec2

SYS_ENCODING = locale.getpreferredencoding()

NoneType = type(None)


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

def signal_cf_status():
    """Signal CloudFormation status to a logical resource in CloudFormation
    that is either given on the command line or resolved from CloudFormation
    tags
    """
    parser = get_parser()
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

def get_userdata():
    """Get userdata defined for an instance into a file
    """
    parser = _get_parser()
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
    parser = _get_parser()
    parser.parse_args()
    print(clients.region())



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

	parser.add_argument('-t', '--ten-minutely', type=int,
	                    help='Number of ten minutely snapshots to keep')
	parser.add_argument('-h', '--hourly', type=int,
	                    help='Number of hourly snapshots to keep')
	parser.add_argument('-d', '--daily', type=int,
	                    help='Number of daily snapshots to keep')
	parser.add_argument('-w', '--weekly', type=int,
	                    help='Number of weekly snapshots to keep')
	parser.add_argument('-m', '--monthly', type=int,
	                    help='Number of monthly snapshots to keep')
	parser.add_argument('-y', '--yearly', type=int,
	                    help='Number of yearly snapshots to keep')

	parser.add_argument('-r', '--dry-run', action='store_true',
	                    help='Dry run - print actions that would be taken')

    argcomplete.autocomplete(parser)
	args = parser.parse_args()
    ebs.prune_snapshots(**args)

def prune_object_versions():
    """ Prune s3 object versions to have a specified amout of daily, weekly, monthly
    and yearly versions
    """
    parser = _get_parser()
	parser.add_argument('-b', '--bucket', type=str,
	                    help='Bucket to prune')
	parser.add_argument('-p', '--prefix', type=str,
	                    help='Limit pruning to a prefix')

	parser.add_argument('-t', '--ten-minutely', type=int,
	                    help='Number of ten minutely snapshots to keep')
	parser.add_argument('-h', '--hourly', type=int,
	                    help='Number of hourly snapshots to keep')
	parser.add_argument('-d', '--daily', type=int,
	                    help='Number of daily snapshots to keep')
	parser.add_argument('-w', '--weekly', type=int,
	                    help='Number of weekly snapshots to keep')
	parser.add_argument('-m', '--monthly', type=int,
	                    help='Number of monthly snapshots to keep')
	parser.add_argument('-y', '--yearly', type=int,
	                    help='Number of yearly snapshots to keep')

	parser.add_argument('-r', '--dry-run', action='store_true',
	                    help='Dry run - print actions that would be taken')

    argcomplete.autocomplete(parser)
	args = parser.parse_args()
    ebs.prune_snapshots(**args)



foo = """
    'cf-signal-status=ec2_utils.cli:cf_signal_status',
    'cf-stack-name=ec2_utils.cli:stack_name',
    'cf-stack-id=ec2_utils.cli:stack_id',
    'clean-snapshots=ec2_utils.cli:clean_snapshots',
    'detach-volume=ec2_utils.cli:detach_volume',
    'get-tag=ec2_utils.cli:tag',
    'get-userdata=ec2_utils.cli:get_userdata',
    'instance-id=ec2_utils.cli:instance_id',
    'interpolate-file=ec2_utils.cli:cli_interpolate_file',
    'latest-snapshot=ec2_utils.volumes:latest_snapshot',
    'logs-to-cloudwatch=ec2_utils.cli:logs_to_cloudwatch',
    'volume-from-snapshot=ec2_utils.cli:volume_from_snapshot',
    'snapshot-from-volume=ec2_utils.cli:snapshot_from_volume',
    'prune-snapshots=ec2_utils.cli:prune_snapshots',
    'prune-s3-object-versions=ec2_utils.cli:prune_s3_object_versions',
    'pytail=ec2_utils.cli:read_and_follow',
    'show-stack-params-and-outputs=ec2_utils.cli:show_stack_params_and_outputs',
    'region=ec2_utils.cli:get_region',
    'register-private-dns=ec2_utils.cli:cli_register_private_dns',
    'wait-for-metadata=ec2_utils.cli:wait_for_metadata'
"""

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
