#!/bin/bash -ex
[[ $UID = 0 ]] || exec sudo -E $0

mkdir -p /mnt/testing
ec2 volume-from-snapshot ec2-testing ec2-testing /mnt/testing 1 -t foo=bar -c 'test:instance'
ec2 detach-volume /mnt/testing -d
