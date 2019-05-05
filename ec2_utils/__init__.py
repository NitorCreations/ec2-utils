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

EC2_ONLY_SCRIPT = [
    'create-shell-archive.sh',
    'encrypt-and-mount.sh',
    'mount-and-format.sh',
    'ssh-hostkeys-collect.sh',
    'disk-by-drive-letter.ps1'
]
EC2_ONLY = [
    'associate-eip=ec2_utils.cli:associate_eip',
    'logs-to-cloudwatch=ec2_utils.cli:logs_to_cloudwatch',
    'pytail=ec2_utils.cli:read_and_follow',
    'account-id=ec2_utils.cli:get_account_id',
    'cf-logical-id=ec2_utils.cli:logical_id',
    'cf-region=ec2_utils.cli:cf_region',
    'cf-get-parameter=ec2_utils.cli:get_parameter',
    'cf-signal-status=ec2_utils.cli:signal_cf_status',
    'cf-stack-name=ec2_utils.cli:stack_name',
    'cf-stack-id=ec2_utils.cli:stack_id',
    'instance-id=ec2_utils.cli:instance_id',
    'region=ec2_utils.cli:get_region',
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