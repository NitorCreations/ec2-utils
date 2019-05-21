#!/bin/bash -ex

ec2 subnet-id | egrep '^subnet-[0-9a-b]{8,16}$'