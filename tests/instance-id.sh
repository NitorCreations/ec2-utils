#!/bin/bash -ex

ec2 instance-id | egrep '^i-[0-9a-f]{13,26}$'