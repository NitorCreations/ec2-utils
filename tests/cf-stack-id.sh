#!/bin/bash -ex

ec2 cf-stack-id | egrep 'arn:aws:cloudformation:.*:stack/'