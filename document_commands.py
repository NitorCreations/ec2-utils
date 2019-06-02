#!/usr/bin/env python

from __future__ import print_function
from ec2_utils import COMMAND_MAPPINGS
from subprocess import Popen, PIPE
import locale
SYS_ENCODING = locale.getpreferredencoding()
def do_call(command):
    proc = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = proc.communicate()
    return (output + err).decode(SYS_ENCODING).strip().replace("'", "\\'")

for command in sorted(COMMAND_MAPPINGS.keys()):
    print("## `ec2 " + command + "`")
    print("")
    print("```bash")
    print(do_call(["ec2", command, "-h"]))
    print("```\n")
