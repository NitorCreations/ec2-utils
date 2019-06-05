#!/bin/bash -ex
[[ $UID = 0 ]] || exec sudo -E $0

mkdir -p /mnt/testing
ec2 volume-from-snapshot ec2-testing ec2-testing /mnt/testing 1 -i -t foo=bar -c 'test:instance'
ec2 snapshot-from-volume ec2-testing ec2-testing /mnt/testing -w -i -t foo=bar -c 'test:instance'
sleep 5
ec2 snapshot-from-volume ec2-testing ec2-testing /mnt/testing -w -i -t foo=bar -c 'test:instance'
ec2 clean-snapshots ec2-testing -t 1
ec2 prune-snapshots -n ec2-testing -M 1 -H 0 -d 0 -w 0 -m 0 -y 0
ec2 detach-volume /mnt/testing -d
