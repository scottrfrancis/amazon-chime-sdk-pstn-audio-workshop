#!/bin/bash

# transpile the target lambda
pushd ..
tsc index.ts
popd

echo "Using node $(node -v)"

# node ./lambda-runner.js <event_file> out.json
# ajv validate
# install with `npm install -g ajv-cli`
# also jq -- `brew install jq` | `sudo apt install jq`

echo ""; echo "BEGIN testing"; echo ""


# 
# 1. basic events
#
pushd cases/basic
./basic.bash
basic_result=$?
popd

# 
# 2. new call event
#
pushd cases/new-call
./new-call.bash
new_call_result=$?
popd

echo ""; echo "TESTING COMPLETE"; echo ""


[[ $basic_result -eq 0 ]] && [[ $new_call_result -eq 0 ]] && echo "ALL PASS" || echo "FAILURES"
