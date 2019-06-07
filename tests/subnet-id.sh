#!/bin/bash -ex

ec2 list-compatible-subnets | egrep '^subnet-'
ec2 subnet-id | egrep '^subnet-[0-9a-f]{8,16}$'