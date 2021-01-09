#!/bin/bash -ex
[[ $UID = 0 ]] || exec sudo -E $0

mkdir -p /mnt/testing
OLD_VOLUMES=$(ec2 list-attached-volumes | wc -l)
ec2 volume-from-snapshot ec2-testing ec2-testing /mnt/testing 1 -t foo=bar
VOLUMES=$(ec2 list-attached-volumes | wc -l)
[ "$VOLUMES" = $(($OLD_VOLUMES + 1)) ]
ec2 detach-volume -m /mnt/testing -x
