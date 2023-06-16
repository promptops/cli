#!/bin/bash

set -e

uid=$(uuidgen)
platform=$(uname)
errfile=$(mktemp)

trap 'ret=$?; if [ $ret -ne 0 ]; then errmsg=$(cat $errfile); echo "Error encountered. Exiting"; curl --header "Content-Type: application/json" --header "user-agent: promptops-cli; user_id=installer-$uid" --request POST --data "{\"trace_id\":\"$uid\", \"error\": \"$ret\", \"error_msg\": \"$errmsg\", \"platform\": \"$platform\", \"method\": \"ubuntu-installer.sh\", \"event\": \"cli-install-error\"}" "https://cli.promptops.com/feedback" &> /dev/null; exit $ret; fi' EXIT

curl --header "Content-Type: application/json" \
--header "user-agent: promptops-cli; user_id=installer-$uid" \
--request POST \
--data '{"trace_id":"'$uid'", "platform": "'$platform'", "method": "ubuntu-installer.sh", "event": "cli-install-started"}' \
"https://cli.promptops.com/feedback" &> /dev/null

sudo apt-get update 2> $errfile

if ! command -v python3 &> /dev/null
then
  sudo apt-get install python3.10 -y 2> $errfile
fi

if ! command -v pip3 &> /dev/null
then
  sudo apt-get install python3-pip -y 2> $errfile
fi

pip3 install promptops 2> $errfile

curl --header "Content-Type: application/json" \
--header "user-agent: promptops-cli; user_id=installer-$uid" \
--request POST \
--data '{"trace_id":"'$uid'", "platform": "'$platform'", "method": "ubuntu-installer.sh", "event": "cli-install-success"}' \
"https://cli.promptops.com/feedback" &> /dev/null