#!/bin/bash -ex

ENI=$(ec2 attach-eni)
echo $ENI | egrep '^eni-[0-9a-f]{13,26}$'
ec2 list-attached-enis
ec2 list-attached-enis | grep $ENI
LINES=$(ec2 list-attached-enis | wc -l)
[ "$LINES" = "2" ]
ec2 detach-eni -i $ENI -d
LINES=$(ec2 list-attached-enis | wc -l)
[ "$LINES" = "1" ]