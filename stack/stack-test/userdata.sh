#!/bin/bash -x

CF_paramBuildNumber=0001

source $(n-include cloud_init_functions.sh)

export HOME=/root
cd $HOME
mkdir -p .ssh
chmod 700 .ssh
vault -l jenkins.nitor.zone.rsa -o .ssh/id_rsa
chmod 600 .ssh/id_rsa
git clone git@github.com:NitorCreations/ec2-utils.git
cd ec2-utils
pip install -e .
./run-tests.sh $CF_paramBuildNumber
source $(n-include cloud_init_footer.sh)