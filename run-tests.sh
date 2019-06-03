#!/bin/bash

export EC2_UTILS_MEASURE_COVERAGE=1
rm -f .coverage
OUT=$(mktemp)
for test in $(ls tests/*.sh | sort); do
  echo -n "$(basename $test .sh)"
  if $test > $OUT 2>&1; then
    echo -e " \e[1;32mPASS\e[0m"
  else
    echo -e " \e[1;31mFAIL\e[0m : OUTPUT =>"
    cat $OUT
  fi
done
coverage report
coverage html
#vault -l ec2-utils-coveralls.yml -o .coveralls.yml
#coveralls
