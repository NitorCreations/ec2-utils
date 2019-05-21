#!/bin/bash -ex

ec2 stack-params-and-outputs -p resourceAsg |  grep '\-resourceAsg-'