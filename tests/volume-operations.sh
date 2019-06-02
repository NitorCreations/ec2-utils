#!/bin/bash -ex
[[ $UID = 0 ]] || exec sudo -E $0

mkdir -p /mnt/testing-ss
ec2 volume-from-snapshot ec2-testing-ss ec2-testing-ss /mnt/testing-ss 1 -t foo=bar
ec2 detach-volume /mnt/testing-ss -d
