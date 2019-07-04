#!/bin/bash

export EC2_UTILS_MEASURE_COVERAGE=1
rm -f .coverage
OUT=$(mktemp)
EXIT=0
for test in $(ls tests/*.sh | sort); do
  echo -n "$(basename $test .sh)"
  if $test > $OUT 2>&1; then
    echo -e " \e[1;32mPASS\e[0m"
  else
    echo -e " \e[1;31mFAIL\e[0m : OUTPUT =>"
    cat $OUT
    EXIT=$(($EXIT + 1))
  fi
done
exit $EXIT

