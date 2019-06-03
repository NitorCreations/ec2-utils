#!/usr/bin/env python

from __future__ import print_function
import sys
from ec2_utils import COMMAND_MAPPINGS
from ec2_utils.ec2 import find_include
from subprocess import Popen, PIPE
import locale
SYS_ENCODING = locale.getpreferredencoding()
def do_call(command):
    proc = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = proc.communicate()
    if proc.returncode != 0:
        print("Call to '" + " ".join(command) + "' failed\n" + err.decode(SYS_ENCODING))
        sys.exit(1)
    return (output + err).decode(SYS_ENCODING).strip().replace("'", "\\'")

for command in sorted(COMMAND_MAPPINGS.keys()):
    print("## `ec2 " + command + "`")
    print("")
    print("```bash")
    if COMMAND_MAPPINGS[command] == "ec2powershell":
        print(do_call(["powershell", find_include(command + ".ps1"), "-h"]))
    else:
        print(do_call(["ec2", command, "-h"]))
    print("```\n")
