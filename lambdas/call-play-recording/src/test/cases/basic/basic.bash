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

echo ""; echo "Testing Blank Input"; echo ""; echo ""

rm -f blank-event.json
echo "{}" >>blank-event.json
rm -f basic-out.json
# node runner
node ../../lambda-runner.js ./cases/basic/blank-event.json basic-out-ts.json >/dev/null 
# python runner
python3 ../../lambda-runner.py blank-event.json basic-out-py.json

blank_valid_ts=$(ajv validate -s basic-schema.json -d basic-out-ts.json >/dev/null && echo true || echo false)
blank_valid_py=$(ajv validate -s basic-schema.json -d basic-out-py.json >/dev/null && echo true || echo false)

blank_valid=$($blank_valid_ts && $blank_valid_py)

# copy and munge inbound event

# success
echo ""; echo "Testing ACTION_SUCCESSFUL Input"; echo ""; echo ""

rm -f basic-event.json
cat ../../../../events/inbound.json | jq '.InvocationEventType = "ACTION_SUCCESSFUL"' >>basic-event.json
rm -f basic-out.json
node ../../lambda-runner.js ./cases/basic/basic-event.json basic-out.json >/dev/null
success_valid_ts=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)
python3 ../../lambda-runner.py basic-event.json basic-out.json
success_valid_py=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)

success_valid=$($success_valid_ts && $success_valid_py)

# hangup
echo ""; echo "Testing HANGUP Input"; echo ""; echo ""

rm -f basic-event.json
cat ../../../../events/inbound.json | jq '.InvocationEventType = "HANGUP"' >>basic-event.json
rm -f basic-out.json
node ../../lambda-runner.js ./cases/basic/basic-event.json basic-out.json >/dev/null
hangup_valid_ts=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)
python3 ../../lambda-runner.py basic-event.json basic-out.json
hangup_valid_py=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)

hangup_valid=$($hangup_valid_ts && $hangup_valid_py)

# bad selector
echo ""; echo "Testing IMBAAD Input"; echo ""; echo ""

rm -f basic-event.json
cat ../../../../events/inbound.json | jq '.InvocationEventType = "IMBAAD"' >>basic-event.json
rm -f basic-out.json
node ../../lambda-runner.js ./cases/basic/basic-event.json basic-out.json >/dev/null
badsel_valid_ts=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)
python3 ../../lambda-runner.py basic-event.json basic-out.json
badsel_valid_py=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)

badsel_valid=$($badsel_valid_ts && $badset_valid_py)

success=$($blank_valid && $success_valid && $hangup_valid && $badsel_valid)
$success && echo "PASSES" || echo "FAILS"

if [ -z $success ]
then
    exit 0
else
    exit 1
fi