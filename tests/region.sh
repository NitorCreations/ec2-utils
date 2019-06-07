#!/bin/bash -ex

ec2 cf-region | egrep '^eu-west-1$'
ec2 region | egrep '^eu-west-1$'