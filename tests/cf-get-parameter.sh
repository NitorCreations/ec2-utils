#!/bin/bash -ex

ec2 cf-get-parameter resourceAsg |  grep '\-resourceAsg-'