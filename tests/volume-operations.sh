#!/bin/bash -ex
[[ $UID = 0 ]] || exec sudo -E $0

mkdir -p /mnt/testing
ec2 volume-from-snapshot ec2-testing ec2-testing /mnt/testing 1 -t foo=bar
VOLUMES=$(ec2 list-attached-volumes | wc -l)
[ "$VOLUMES" = 3 ]
ec2 detach-volume /mnt/testing -d
