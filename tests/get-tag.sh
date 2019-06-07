#!/bin/bash -ex

ec2 list-tags  |  egrep '^aws:cloudformation:logical-id'
ec2 get-tag aws:cloudformation:logical-id |  egrep '^resourceAsg$'
