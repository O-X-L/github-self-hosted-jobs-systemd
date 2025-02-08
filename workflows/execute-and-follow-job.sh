#!/usr/bin/env bash

FETCH_INTERVAL_SEC=2
SEP='##############################'

set -euo pipefail

echo 'Checking environment'
test $CI_API_URL
test $CI_TOKEN
test $LOG_FILE

echo 'Checking dependencies'
test jq
test curl

echo 'Starting job'
curl -XPOST "${CI_API_URL}?token=${CI_TOKEN}" 2>/dev/null

echo 'Following job output'
echo "$SEP"
echo ''

while true
do
  sleep $FETCH_INTERVAL_SEC
  curl "${CI_API_URL}/tail?token=${CI_TOKEN}" 2>/dev/null | jq -r '.logs' | tee -a "$LOG_FILE"
  STATE="$(curl "${CI_API_URL}/state?token=${CI_TOKEN}" 2>/dev/null | jq -r '.state')"

  if ! echo "$STATE" | grep -Eq 'running|activating|active'
  then
    echo ''
    echo "$SEP"
    echo "Job finished with result: ${STATE}" | tee -a "$LOG_FILE"
    if [[ "$STATE" == "failed" ]]
    then
      exit 1
    else
      exit 0
    fi

  fi
done


