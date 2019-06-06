#!/bin/bash -ex

ec2 log-to-cloudwatch ${BASH_SOURCE[0]} -g ec2-test-group &
PID=$!
sleep 3
kill $PID
ec2 logs ec2-test-group -s "5 minutes ago" -e now | grep 'kill $PID'

