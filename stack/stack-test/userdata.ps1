<powershell>
$ErrorActionPreference = "Continue"
Set-ExecutionPolicy RemoteSigned -Scope LocalMachine -Force
Start-Transcript -path C:\nameless\cloud-init-output.log
ndt ec2-wait-for-metadata -t 300
$selfOutput = Start-Job {ndt logs-to-cloudwatch 'C:\nameless\cloud-init-output.log'}
$cfnOutput = Start-Job {ndt logs-to-cloudwatch 'C:\cfn\log\cfn-init.log'}
$ec2configOutput = Start-Job {ndt logs-to-cloudwatch 'C:\Program Files\Amazon\Ec2ConfigService\Logs\Ec2ConfigLog.txt'}


$build = #CF{ Ref: paramBuildNumber }
$env:AWS_DEFAULT_PROFILE = #CF{ Ref: 'AWS::Region' }

mkdir -p .ssh
vault -l jenkins.nitor.zone.rsa -o .ssh\id_rsa
git clone git@github.com:NitorCreations/ec2-utils.git
cd ec2-utils
pip install -e .
./run-tests.ps1

ndt signal-cf-status SUCCESS

Stop-Job $selfOutput.Id
Stop-Job $cfnOutput.Id
Stop-Job $ec2configOutput.Id
Remove-Job $selfOutput.Id
Remove-Job $cfnOutput.Id
Remove-Job $ec2configOutput.Id
Stop-Transcript
</powershell>
