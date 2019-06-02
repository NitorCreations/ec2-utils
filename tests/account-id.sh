#!/bin/bash -ex

ec2 availability-zone | egrep '^(ap|ca|eu|sa|us)-(central|east|north|northeast|south|southeast|west)-[0-9][abcde]'