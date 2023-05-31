#!/bin/bash

set -e

uid=$(uuidgen)
platform=$(uname)

trap 'ret=$?; if [ $ret -ne 0 ]; then echo "Error encountered. Exiting"; curl --header "Content-Type: application/json" --header "user-agent: promptops-cli; user_id=installer-$uid" --request POST --data "{\"trace_id\":\"$uid\", \"error\": \"$ret\",  \"platform\": \"$platform\", \"method\": \"ubuntu-installer.sh\", \"event\": \"cli-install-error\"}" "https://cli.promptops.com/feedback" &> /dev/null; exit $ret; fi' EXIT

# Install request
curl --header "Content-Type: application/json" \
--header "user-agent: promptops-cli; user_id=installer-$uid" \
--request POST \
--data '{"trace_id":"'$uid'", "platform": "'$platform'", "method": "ubuntu-installer.sh", "event": "cli-install-started"}' \
"https://cli.promptops.com/feedback" &> /dev/null

sudo apt-get update

if ! command -v python3 &> /dev/null
then
  sudo apt-get install python3.10 -y
fi

if ! command -v pip3 &> /dev/null
then
  sudo apt-get install python3-pip -y
fi

pip3 install promptops

# Success request
curl --header "Content-Type: application/json" \
--header "user-agent: promptops-cli; user_id=installer-$uid" \
--request POST \
--data '{"trace_id":"'$uid'", "platform": "'$platform'", "method": "ubuntu-installer.sh", "event": "cli-install-success"}' \
"https://cli.promptops.com/feedback" &> /dev/null