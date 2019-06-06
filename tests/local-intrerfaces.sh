#!/bin/bash -ex

ec2 list-local-interfaces  | egrep '^lo'