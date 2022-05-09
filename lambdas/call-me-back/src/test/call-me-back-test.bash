#!/bin/bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 

# transpile the target lambda for TYPESCRIPT
pushd ..
tsc index.ts
popd

echo "Using node $(node -v)"

# setup pythonpath for PYTHON
pushd ..
export PYTHONPATH=$PYTHONPATH:$(pwd)
popd


# node ./lambda-runner.js <event_file> out.json
# ajv validate
# install with `npm install -g ajv-cli`
# also jq -- `brew install jq` | `sudo apt install jq`

echo ""; echo "BEGIN testing"; echo ""

# set expected env vars
export AWS_REGION=$(aws configure get region) 


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
