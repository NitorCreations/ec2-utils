from builtins import str
import os
import sys
import signal
import locale
from subprocess import PIPE, Popen
from argcomplete import USING_PYTHON2, ensure_str, split_line
from ec2_utils import COMMAND_MAPPINGS, cov

SYS_ENCODING = locale.getpreferredencoding()

include_dir = os.path.join(os.path.dirname(__file__), "includes") + os.path.sep

def find_include(basefile):
    if os.path.isfile(basefile):
        return basefile
    if os.path.isfile(include_dir + basefile):
        return include_dir + basefile
    return None

def do_command_completion():
    """ ec2 command completion function
    """
    output_stream = os.fdopen(8, "wb")
    ifs = os.environ.get("_ARGCOMPLETE_IFS", "\v")
    if len(ifs) != 1:
        sys.exit(1)
    current = os.environ["COMP_CUR"]
    prev = os.environ["COMP_PREV"]
    comp_line = os.environ["COMP_LINE"]
    comp_point = int(os.environ["COMP_POINT"])

    # Adjust comp_point for wide chars
    if USING_PYTHON2:
        comp_point = len(comp_line[:comp_point].decode(SYS_ENCODING))
    else:
        comp_point = len(comp_line.encode(SYS_ENCODING)[:comp_point].decode(SYS_ENCODING))

    comp_line = ensure_str(comp_line)
    comp_words = split_line(comp_line, comp_point)[3]
    if "COMP_CWORD" in os.environ and os.environ["COMP_CWORD"] == "1":
        keys = [x for x in list(COMMAND_MAPPINGS.keys()) if x.startswith(current)]
        output_stream.write(ifs.join(keys).encode(SYS_ENCODING))
        output_stream.flush()
        sys.exit(0)
    else:
        command = prev
        if len(comp_words) > 1:
            command = comp_words[1]
        if command not in COMMAND_MAPPINGS:
            sys.exit(1)
        command_type = COMMAND_MAPPINGS[command]
        if command_type == "shell":
            command = command + ".sh"
        if command_type == "ec2shell":
            command = command + ".sh"
        if command_type == "ec2shell" or command_type == "ec2script":
            command = find_include(command)
        if command_type == "shell" or command_type == "script" or \
           command_type == "ec2shell" or command_type == "ec2script":
            proc = Popen([command], stderr=PIPE, stdout=PIPE)
            output = proc.communicate()[0]
            if proc.returncode == 0:
                output_stream.write(output.replace("\n", ifs).decode(SYS_ENCODING))
                output_stream.flush()
            else:
                sys.exit(1)
        else:
            line = comp_line[3:].lstrip()
            os.environ['COMP_POINT'] = str(comp_point - (len(comp_line) -
                                                         len(line)))
            os.environ['COMP_LINE'] = line
            parts = command_type.split(":")
            getattr(__import__(parts[0], fromlist=[parts[1]]), parts[1])()
        sys.exit(0)


def stop_cov(signum, frame):
    if cov:
        cov.save()
        cov.stop()
    if signum:
        sys.exit(0)

def ec2():
    """ The main ec2 utils command that provides bash command
    completion and subcommand execution
    """
    if "_ARGCOMPLETE" in os.environ:
        do_command_completion()
    else:
        signal.signal(signal.SIGINT, stop_cov)
        signal.signal(signal.SIGTERM, stop_cov)
        try:
            if len(sys.argv) < 2 or sys.argv[1] not in COMMAND_MAPPINGS:
                sys.stderr.writelines([u'usage: ec2 <command> [args...]\n'])
                sys.stderr.writelines([u'\tcommand shoud be one of:\n'])
                for command in sorted(COMMAND_MAPPINGS):
                    sys.stderr.writelines([u'\t\t' + command + '\n'])
                sys.exit(1)
            command = sys.argv[1]
            command_type = COMMAND_MAPPINGS[command]
            if command_type == "shell":
                command = command + ".sh"
            if command_type == "ec2shell":
                command = command + ".sh"
            if command_type == "ec2powershell":
                command = command + ".ps1"
            if command_type == "ec2shell" or command_type == "ec2script":
                command = find_include(command)
            if command_type == "shell" or command_type == "script" or \
               command_type == "ec2shell" or command_type == "ec2script" or \
               command_type == "ec2powershell":
                sys.exit(Popen([command] + sys.argv[2:]).wait())
            else:
                parts = command_type.split(":")
                my_func = getattr(__import__(parts[0], fromlist=[parts[1]]),
                                  parts[1])
                sys.argv = sys.argv[1:]
                sys.argv[0] = "ec2 " + sys.argv[0]
                my_func()
        finally:
            stop_cov(None, None)

if __name__ == "__main__":
    ec2()
