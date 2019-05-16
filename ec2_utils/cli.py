import os
import argcomplete
import argparse
import inspect
import json
import locale
import sys
from argcomplete.completers import ChoicesCompleter, FilesCompleter
from ec2_utils.instance_info import info
from ec2_utils import logs, clients, ebs, s3, interface, instance_info
from ec2_utils.clients import is_ec2, stacks

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

def detach_volume():
    """ Create a snapshot of a volume identified by it's mount path
    """
    parser = _get_parser()
    parser.add_argument("mount_path", help="Where to mount the volume").completer = FilesCompleter()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if is_ec2():
        ebs.detach_volume(args.mount_path)
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

def region():
    """ Get current default region. Defaults to the region of the instance on
    ec2 if not otherwise defined.
    """
    parser = _get_parser()
    parser.parse_args()
    print(clients.region())

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
                                  args.mount_path, wait=args.wait, tags=tags, copytags=args.copytags))
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
                        ChoicesCompleter(stacks())
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
                                 copytags=args.copytags, tags=tags)
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
