#!/bin/bash -ex

aws s3 cp ${BASH_SOURCE[0]} s3://ec2-utils-test
aws s3 cp ${BASH_SOURCE[0]} s3://ec2-utils-test
ec2 prune-s3-object-versions ec2-utils-test -M 1 -H 0 -d 0 -w 0 -m 0 -y 0