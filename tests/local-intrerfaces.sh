#!/bin/bash -ex

ec2 register-private-dns ec2-utils-test.dev.nitor.zone dev.nitor.zone.
LOCAL_IP="$(dig +short ec2-utils-test.dev.nitor.zone)"
ec2 list-local-interfaces  | egrep $LOCAL_IP
