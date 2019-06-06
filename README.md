# EC2 Utilities

[![Coverage Status](https://coveralls.io/repos/github/NitorCreations/ec2-utils/badge.svg?branch=master)](https://coveralls.io/github/NitorCreations/ec2-utils?branch=master)

This is a set of tools meant for running on ec2 instances to simplify bootstrapping
and other setup. The tools are related to getting various information about
the instance and the surrounding account and possibly the CloudFormation
stack that created the instance. Also utilities for CloudWatch logging,
EBS volumes and snapshots and Elastic Network Interfaces are provided.

# Commands

The following lists all the commands available and their usage

## `ec2 account-id`

```bash
usage: ec2 account-id [-h]

Get current account id. Either from instance metadata or current cli
configuration.

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 associate-eip`

```bash
usage: ec2 associate-eip [-h] [-i IP] [-a ALLOCATIONID] [-e EIPPARAM]
                         [-p ALLOCATIONIDPARAM]

Associate an Elastic IP for the instance that this script runs on

optional arguments:
  -h, --help            show this help message and exit
  -i IP, --ip IP        Elastic IP to allocate - default is to get paramEip
                        from the stack that created this instance
  -a ALLOCATIONID, --allocationid ALLOCATIONID
                        Elastic IP allocation id to allocate - default is to
                        get paramEipAllocationId from the stack that created
                        this instance
  -e EIPPARAM, --eipparam EIPPARAM
                        Parameter to look up for Elastic IP in the stack -
                        default is paramEip
  -p ALLOCATIONIDPARAM, --allocationidparam ALLOCATIONIDPARAM
                        Parameter to look up for Elastic IP Allocation ID in
                        the stack - default is paramEipAllocationId
```

## `ec2 attach-eni`

```bash
usage: ec2 attach-eni [-h] [-s SUBNET | -i ENI_ID]

Optionally create and attach an elastic network interface

optional arguments:
  -h, --help            show this help message and exit
  -s SUBNET, --subnet SUBNET
                        Subnet for the elastic network inferface if one is
                        created. Needs to be on the same availability zone as
                        the instance.
  -i ENI_ID, --eni-id ENI_ID
                        Id of the eni to attach, if attaching an existing eni.
```

## `ec2 availability-zone`

```bash
usage: ec2 availability-zone [-h]

Get availability zone for the instance

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 cf-get-parameter`

```bash
usage: ec2 cf-get-parameter [-h] parameter

Get a parameter value from the stack

positional arguments:
  parameter   The name of the parameter to print

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 cf-logical-id`

```bash
usage: ec2 cf-logical-id [-h]

Get the logical id that is expecting a signal from this instance

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 cf-region`

```bash
usage: ec2 cf-region [-h]

Get region of the stack that created this instance

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 cf-signal-status`

```bash
usage: ec2 cf-signal-status [-h] [-r RESOURCE] status

Signal CloudFormation status to a logical resource in CloudFormation that is
either given on the command line or resolved from CloudFormation tags

positional arguments:
  status                Status to indicate: SUCCESS | FAILURE

optional arguments:
  -h, --help            show this help message and exit
  -r RESOURCE, --resource RESOURCE
                        Logical resource name to signal. Looked up from
                        cloudformation tags by default
```

## `ec2 cf-stack-id`

```bash
usage: ec2 cf-stack-id [-h]

Get id of the stack the creted this instance

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 cf-stack-name`

```bash
usage: ec2 cf-stack-name [-h]

Get name of the stack that created this instance

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 clean-snapshots`

```bash
usage: ec2 clean-snapshots [-h] [-t DAYS] [-d] tags [tags ...]

Clean snapshots that are older than a number of days (30 by default) and have
one of specified tag values

positional arguments:
  tags                  The tag values to select deleted snapshots

optional arguments:
  -h, --help            show this help message and exit
  -t DAYS, --days DAYS  The number of days that is theminimum age for
                        snapshots to be deleted
  -d, --dry-run         Do not delete, but print what would be deleted
```

## `ec2 create-eni`

```bash
usage: ec2 create-eni [-h] [-s SUBNET]

create an elastic network interface

optional arguments:
  -h, --help            show this help message and exit
  -s SUBNET, --subnet SUBNET
                        Subnet for the elastic network inferface if one is
                        created. Needs to be on the same availability zone as
                        the instance.
```

## `ec2 create-shell-archive`

```bash
file  one or more files to package into the archive
usage: create-shell-archive.sh [-h] [<file> ...]

Creates a self-extracting bash archive, suitable for storing in e.g. Lastpass SecureNotes
positional arguments:

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 detach-eni`

```bash
usage: ec2 detach-eni [-h] [-i ENI_ID] [-d]

Detach an eni from this instance

optional arguments:
  -h, --help            show this help message and exit
  -i ENI_ID, --eni-id ENI_ID
                        Eni id to detach
  -d, --delete          Delete eni after detach
```

## `ec2 detach-volume`

```bash
usage: ec2 detach-volume [-h] [-d] [-i VOLUME_ID] mount_path

Create a snapshot of a volume identified by it\'s mount path

positional arguments:
  mount_path            Mount point of the volume to be detached

optional arguments:
  -h, --help            show this help message and exit
  -d, --delete          Delete volume after detaching
  -i VOLUME_ID, --volume-id VOLUME_ID
                        Eni id to detach
```

## `ec2 disk-by-drive-letter`

```bash
usage: ec2 disk-by-drive-letter [-h] {drive}

positional arguments:
  drive  the drive to get disk info for
optional arguments:
  -h     show this help message and exit
```

## `ec2 encrypt-and-mount`

```bash
Mounts a local block device as an encrypted volume. Handy for things like local database installs.
usage: encrypt-and-mount.sh [-h] blk-device mount-path


positional arguments
  blk-device  the block device you want to encrypt and mount
  mount-path  the mount point for the encrypted volume

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 get-tag`

```bash
usage: ec2 get-tag [-h] name

Get the value of a tag for an ec2 instance

positional arguments:
  name        The name of the tag to get

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 get-userdata`

```bash
usage: ec2 get-userdata [-h] file

Get userdata defined for an instance into a file

positional arguments:
  file        File to write userdata into. \'-\' for stdout

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 instance-id`

```bash
usage: ec2 instance-id [-h]

Get id for instance

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 latest-snapshot`

```bash
usage: ec2 latest-snapshot [-h] tag

Get the latest snapshot with a given tag

positional arguments:
  tag         The tag to find snapshots with

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 list-attachable-enis`

```bash
usage: ec2 list-attachable-enis [-h]

List all enis in the same availability-zone, i.e. ones that can be attached to
this instance.

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 list-attached-enis`

```bash
usage: ec2 list-attached-enis [-h] [-i | -f]

List all enis in the same availability-zone, i.e. ones that can be attached to
this instance.

optional arguments:
  -h, --help        show this help message and exit
  -i, --ip-address  Include first private ip addresses for the interfaces in
                    the output
  -f, --full        Print all available data about attached enis as json
```

## `ec2 list-attached-volumes`

```bash
usage: ec2 list-attached-volumes [-h]

List attached volumes

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 list-compatible-subnets`

```bash
usage: ec2 list-compatible-subnets [-h]

List all subnets in the same availability-zone, i.e. ones that can have ENIs
that can be attached to this instance.

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 list-local-interfaces`

```bash
usage: ec2 list-local-interfaces [-h] [-j]

List local interfaces

optional arguments:
  -h, --help  show this help message and exit
  -j, --json  Output in json format
```

## `ec2 list-tags`

```bash
usage: ec2 list-tags [-h]

List all tags associated with the instance

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 log-to-cloudwatch`

```bash
usage: ec2 log-to-cloudwatch [-h] [-g GROUP] [-s STREAM] file

Read a file and send rows to cloudwatch and keep following the end for new
data. The log group will be the stack name that created instance if not given
as an argument. The logstream will be the instance id and filename if not
given as an argument. Group and stream aare created if they do not exist.

positional arguments:
  file                  File to follow

optional arguments:
  -h, --help            show this help message and exit
  -g GROUP, --group GROUP
                        Log group to log to. Defaults to the stack name that
                        created the instance if not given and instance is
                        created with a CloudFormation stack
  -s STREAM, --stream STREAM
                        The log stream name to log to. The instance id and
                        filename if not given
```

## `ec2 logs`

```bash
usage: ndt logs log_group_pattern [-h] [-f FILTER] [-s START [START ...]] [-e END [END ...]] [-o]

Get logs from multiple CloudWatch log groups and possibly filter them.

positional arguments:
  log_group_pattern     Regular expression to filter log groups with

optional arguments:
  -h, --help            show this help message and exit
  -f FILTER, --filter FILTER
                        CloudWatch filter pattern
  -s START [START ...], --start START [START ...]
                        Start time (x m|h|d|w ago | now | <seconds since
                        epoc>)
  -e END [END ...], --end END [END ...]
                        End time (x m|h|d|w ago | now | <seconds since epoc>)
  -o, --order           Best effort ordering of log entries
```

## `ec2 mount-and-format`

```bash
Mounts a local block device as an encrypted volume. Handy for things like local database installs.
usage: /home/centos/cloud9/ec2-utils/ec2_utils/includes/mount-and-format.sh [-h] blk-device mount-path


positional arguments
  blk-device  the block device you want to mount and formant
  mount-path  the mount point for the volume

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 network-interface-ids`

```bash
usage: ec2 network-interface-ids [-h]

List network interface ids attached to the instance in the order of attachment
device index

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 prune-s3-object-versions`

```bash
usage: ec2 prune-s3-object-versions [-h] [-p PREFIX] [-M TEN_MINUTELY]
                                    [-H HOURLY] [-d DAILY] [-w WEEKLY]
                                    [-m MONTHLY] [-y YEARLY] [-r]
                                    bucket

Prune s3 object versions to have a specified amout of daily, weekly, monthly
and yearly versions

positional arguments:
  bucket                Bucket to prune

optional arguments:
  -h, --help            show this help message and exit
  -p PREFIX, --prefix PREFIX
                        Limit pruning to a prefix
  -M TEN_MINUTELY, --ten-minutely TEN_MINUTELY
                        Number of ten minutely object versions to keep.
                        Defaults to two days of these.
  -H HOURLY, --hourly HOURLY
                        Number of hourly object versions to keep. Defaults to
                        a week of these.
  -d DAILY, --daily DAILY
                        Number of daily object versions to keep. Defaults to a
                        month of these.
  -w WEEKLY, --weekly WEEKLY
                        Number of weekly object versions to keep. Defaults to
                        3 months of these.
  -m MONTHLY, --monthly MONTHLY
                        Number of monthly object versions to keep. Defaults to
                        a year of these.
  -y YEARLY, --yearly YEARLY
                        Number of yearly object versions to keep. Defaults to
                        three years.
  -r, --dry-run         Dry run - print actions that would be taken
```

## `ec2 prune-snapshots`

```bash
usage: ec2 prune-snapshots [-h] [-v VOLUME_ID] [-n [TAG_NAME [TAG_NAME ...]]]
                           [-t [TAG_VALUE [TAG_VALUE ...]]] [-M TEN_MINUTELY]
                           [-H HOURLY] [-d DAILY] [-w WEEKLY] [-m MONTHLY]
                           [-y YEARLY] [-r]

Prune snapshots to have a specified amout of daily, weekly, monthly and yearly
snapshots

optional arguments:
  -h, --help            show this help message and exit
  -v VOLUME_ID, --volume-id VOLUME_ID
                        EBS Volume ID, if wanted for only one volume
  -n [TAG_NAME [TAG_NAME ...]], --tag-name [TAG_NAME [TAG_NAME ...]]
                        Snapshot tag name
  -t [TAG_VALUE [TAG_VALUE ...]], --tag-value [TAG_VALUE [TAG_VALUE ...]]
                        Snapshot tag value
  -M TEN_MINUTELY, --ten-minutely TEN_MINUTELY
                        Number of ten minutely snapshots to keep. Defaults to
                        two days of these.
  -H HOURLY, --hourly HOURLY
                        Number of hourly snapshots to keep. Defaults to a week
                        of these.
  -d DAILY, --daily DAILY
                        Number of daily snapshots to keep. Defaults to a month
                        of these.
  -w WEEKLY, --weekly WEEKLY
                        Number of weekly snapshots to keep. Defaults to 3
                        months of these.
  -m MONTHLY, --monthly MONTHLY
                        Number of monthly snapshots to keep. Defaults to a
                        year of these.
  -y YEARLY, --yearly YEARLY
                        Number of yearly snapshots to keep. Defaults to three
                        years.
  -r, --dry-run         Dry run - print actions that would be taken
```

## `ec2 pytail`

```bash
usage: ec2 pytail [-h] file

Read and print a file and keep following the end for new data

positional arguments:
  file        File to follow

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 region`

```bash
usage: ec2 region [-h]

Get current default region. Defaults to the region of the instance on ec2 if
not otherwise defined.

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 register-private-dns`

```bash
usage: ec2 register-private-dns [-h] [-t TTL] dns_name hosted_zone

Register local private IP in route53 hosted zone usually for internal use.

positional arguments:
  dns_name           The name to update in route 53
  hosted_zone        The name of the hosted zone to update

optional arguments:
  -h, --help         show this help message and exit
  -t TTL, --ttl TTL  Time to live for the record. 60 by default
```

## `ec2 snapshot-from-volume`

```bash
usage: ec2 snapshot-from-volume [-h] [-w] [-c [COPYTAGS [COPYTAGS ...]]]
                                [-t [TAGS [TAGS ...]]] [-i]
                                tag_key tag_value mount_path

Create a snapshot of a volume identified by it\'s mount path

positional arguments:
  tag_key               Key of the tag to find volume with
  tag_value             Value of the tag to find volume with
  mount_path            Where to mount the volume

optional arguments:
  -h, --help            show this help message and exit
  -w, --wait            Wait for the snapshot to finish before returning
  -c [COPYTAGS [COPYTAGS ...]], --copytags [COPYTAGS [COPYTAGS ...]]
                        Tag to copy to the snapshot from instance. Multiple
                        values allowed.
  -t [TAGS [TAGS ...]], --tags [TAGS [TAGS ...]]
                        Tag to add to the snapshot in the format name=value.
                        Multiple values allowed.
  -i, --ignore-missing-copytags
                        If set, missing copytags are ignored.
```

## `ec2 ssh-hostkeys-collect`

```bash
usage: ssh-hostkeys-collect.sh [-h] hostname

Creates a <hostname>-ssh-hostkeys.sh archive in the current directory containing
ssh host keys to preserve the identity of a server over image upgrades.

positional arguments
  hostname   the name of the host used to store the keys. Typically the hostname is what
             instance userdata scripts will use to look for the keys

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 stack-params-and-outputs`

```bash
usage: ec2 stack-params-and-outputs [-h] [-p PARAMETER] [-s STACK_NAME]

Show stack parameters and outputs as a single json documents

optional arguments:
  -h, --help            show this help message and exit
  -p PARAMETER, --parameter PARAMETER
                        Name of paremeter if only one parameter required
  -s STACK_NAME, --stack-name STACK_NAME
                        The name of the stack to show
```

## `ec2 subnet-id`

```bash
usage: ec2 subnet-id [-h]

Get subnet id for instance

optional arguments:
  -h, --help  show this help message and exit
```

## `ec2 volume-from-snapshot`

```bash
usage: ec2 volume-from-snapshot [-h] [-n] [-c [COPYTAGS [COPYTAGS ...]]]
                                [-t [TAGS [TAGS ...]]] [-i]
                                tag_key tag_value mount_path [size_gb]

Create a volume from an existing snapshot and mount it on the given path. The
snapshot is identified by a tag key and value. If no tag is found, an empty
volume is created, attached, formatted and mounted.

positional arguments:
  tag_key               Key of the tag to find volume with
  tag_value             Value of the tag to find volume with
  mount_path            Where to mount the volume
  size_gb               Size in GB for the volume. If different from snapshot
                        size, volume and filesystem are resized

optional arguments:
  -h, --help            show this help message and exit
  -n, --no_delete_on_termination
                        Whether to skip deleting the volume on termination,
                        defaults to false
  -c [COPYTAGS [COPYTAGS ...]], --copytags [COPYTAGS [COPYTAGS ...]]
                        Tag to copy to the volume from instance. Multiple
                        values allowed.
  -t [TAGS [TAGS ...]], --tags [TAGS [TAGS ...]]
                        Tag to add to the volume in the format name=value.
                        Multiple values allowed.
  -i, --ignore-missing-copytags
                        If set, missing copytags are ignored.
```

## `ec2 wait-for-metadata`

```bash
usage: ec2 wait-for-metadata [-h] [--timeout TIMEOUT]

Waits for metadata service to be available. All errors are ignored until time
expires or a socket can be established to the metadata service

optional arguments:
  -h, --help            show this help message and exit
  --timeout TIMEOUT, -t TIMEOUT
                        Maximum time to wait in seconds for the metadata
                        service to be available
```

