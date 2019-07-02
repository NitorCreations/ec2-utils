# Copyright 2019 Nitor Creations Oy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Main module for ec2-utils
"""
import base64
from os import environ

cov = None
if "EC2_UTILS_MEASURE_COVERAGE" in environ:
    from coverage import Coverage
    cov = Coverage(auto_data=True, source=["ec2_utils"], branch=False,
                   omit=["ec2_utils/__init__.py", 
                         "ec2_utils/elastic_c2_register_complete.py",
                         "ec2_utils/ec2.py"])
    cov.start()


EC2_ONLY_SCRIPT = [
    'create-shell-archive.sh',
    'encrypt-and-mount.sh',
    'mount-and-format.sh',
    'ssh-hostkeys-collect.sh',
    'disk-by-drive-letter.ps1'
]
EC2_ONLY = [
    'account-id=ec2_utils.cli:account_id',
    'associate-eip=ec2_utils.cli:associate_eip',
    'attach-eni=ec2_utils.cli:attach_eni',
    'availability-zone=ec2_utils.cli:availability_zone',
    'cf-logical-id=ec2_utils.cli:cf_logical_id',
    'cf-region=ec2_utils.cli:cf_region',
    'cf-get-parameter=ec2_utils.cli:cf_get_parameter',
    'cf-signal-status=ec2_utils.cli:cf_signal_status',
    'cf-stack-name=ec2_utils.cli:cf_stack_name',
    'cf-stack-id=ec2_utils.cli:cf_stack_id',
    'clean-snapshots=ec2_utils.cli:clean_snapshots',
    'create-eni=ec2_utils.cli:create_eni',
    'detach-volume=ec2_utils.cli:detach_volume',
    'detach-eni=ec2_utils.cli:detach_eni',
    'get-latest-snapshot=ec2_utils.cli:latest_snapshot',
    'get-tag=ec2_utils.cli:get_tag',
    'get-userdata=ec2_utils.cli:get_userdata',
    'instance-id=ec2_utils.cli:instance_id',
    'latest-snapshot=ec2_utils.cli:latest_snapshot',
    'list-attachable-enis=ec2_utils.cli:list_attachable_enis',
    'list-attached-enis=ec2_utils.cli:list_attached_enis',
    'list-attached-volumes=ec2_utils.cli:list_attached_volumes',
    'list-compatible-subnets=ec2_utils.cli:list_compatible_subnets',
    'list-local-interfaces=ec2_utils.cli:list_local_interfaces',
    'list-tags=ec2_utils.cli:list_tags',
    'log-to-cloudwatch=ec2_utils.cli:log_to_cloudwatch',
    'logs=ec2_utils.cli:get_logs',
    'prune-snapshots=ec2_utils.cli:prune_snapshots',
    'prune-s3-object-versions=ec2_utils.cli:prune_object_versions',
    'pytail=ec2_utils.cli:read_and_follow',
    'region=ec2_utils.cli:region',
    'register-private-dns=ec2_utils.cli:register_private_dns',
    'snapshot-from-volume=ec2_utils.cli:snapshot_from_volume',
    'stack-params-and-outputs=ec2_utils.cli:stack_params_and_outputs',
    'subnet-id=ec2_utils.cli:subnet_id',
    'volume-from-snapshot=ec2_utils.cli:volume_from_snapshot',
    'wait-for-metadata=ec2_utils.cli:wait_for_metadata'
]
CONSOLE_ONLY = [
    'ec2=ec2_utils.ec2:ec2',
    'elastic-c2-register-complete=ec2_utils.elastic_c2_register_complete:main'
]
CONSOLESCRIPTS = CONSOLE_ONLY
COMMAND_MAPPINGS = {}
for script in EC2_ONLY_SCRIPT:
    name = script
    value = "ec2script"
    if name.endswith(".sh"):
        name = name[:-3]
        value = "ec2shell"
    if name.endswith(".ps1"):
        name = name[:-4]
        value = "ec2powershell"
    COMMAND_MAPPINGS[name] = value
for script in EC2_ONLY:
    name, value = script.split("=")
    COMMAND_MAPPINGS[name] = value

def _to_str(data):
    ret = data
    decode_method = getattr(data, "decode", None)
    if callable(decode_method):
        try:
            ret = data.decode()
        except:
            ret = _to_str(base64.b64encode(data))
    return str(ret)

def _to_bytes(data):
    ret = data
    encode_method = getattr(data, "encode", None)
    if callable(encode_method):
        ret = data.encode("utf-8")
    return bytes(ret)

    