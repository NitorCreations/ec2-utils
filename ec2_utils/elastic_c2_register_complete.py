from __future__ import print_function

def main():
    """Print out shell function and command to register ndt command completion
    """
    print("""_ec2_complete() {
    local IFS=$'\\013'
    local COMP_CUR="${COMP_WORDS[COMP_CWORD]}"
    local COMP_PREV="${COMP_WORDS[COMP_CWORD-1]}"
    local SUPPRESS_SPACE=0
    if compopt +o nospace 2> /dev/null; then
        SUPPRESS_SPACE=1
    fi
    COMPREPLY=( $(IFS="$IFS" \\
                  COMP_LINE="$COMP_LINE" \\
                  COMP_POINT="$COMP_POINT" \\
                  COMP_TYPE="$COMP_TYPE" \\
                  COMP_CUR="$COMP_CUR" \\
                  COMP_PREV="$COMP_PREV" \\
                  COMP_CWORD=$COMP_CWORD \\
                  _ARGCOMPLETE_COMP_WORDBREAKS="$COMP_WORDBREAKS" \\
                  _ARGCOMPLETE=1 \\
                  _ARGCOMPLETE_SUPPRESS_SPACE=$SUPPRESS_SPACE \\
                  "$1" 8>&1 9>&2 1>/dev/null 2>/dev/null) )
    if [[ $? != 0 ]]; then
        unset COMPREPLY
    elif [[ $SUPPRESS_SPACE == 1 ]] && [[ "$COMPREPLY" =~ [=/:]$ ]]; then
        compopt -o nospace
    fi
}
complete -o nospace -F _ec2_complete "ec2"
""", end="")
    return

if __name__ == "__main__":
    main()