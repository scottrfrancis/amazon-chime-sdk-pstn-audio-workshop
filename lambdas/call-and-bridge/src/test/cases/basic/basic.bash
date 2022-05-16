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

echo ""; echo "Testing Client Construction"; echo ""; echo ""

# TS validates as part of every call
pushd ../../..
single_client_py=$(python3 -m unittest -v -k test_static_client  test/lambda_function_test.py >/dev/null && echo true || echo false)
popd

single_client_valid=$($single_client_py)


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
#
#   need to force a no-err return from the sender, which needs a mock, use Jest
echo ""; echo "Testing HANGUP Input"; echo ""; echo ""

rm -f basic-out.out
pushd ../../..
hangup_valid_ts=$(yarn test -t 'first hangup' >/dev/null && echo true || echo false)
hangup_valid_py=$(python3 -m unittest -v -k test_hangup_action  test/lambda_function_test.py >/dev/null && echo true || echo false)
popd

hangup_valid=$($hangup_valid_ts && $hangup_valid_py)

# hangup -- force error
#
#   no way to inject/mock the client behavior from bash... so call jest
echo ""; echo "Testing FORCED ERROR on HANGUP Input"; echo ""; echo ""

rm -f forced-error.out
pushd ../../..
force_valid_ts=$(yarn test -t 'force hangup error' >/dev/null && echo true || echo false)
force_valid_py=$(python3 -m unittest -v -k test_forced_exception  test/lambda_function_test.py >/dev/null && echo true || echo false)
popd

force_valid=$($force_valid_ts && $force_valid_py)

# second hangup
echo ""; echo "Testing _second_ HANGUP Input"; echo ""; echo ""

rm -f basic-event.json
cat ../../../../events/inbound.json | jq '.InvocationEventType = "HANGUP"' >>basic-event.json
mv basic-event.json basic-event-tmp.json
cat basic-event-tmp.json | jq '.CallDetails.Participants[0].Direction = "foobar"' >>basic-event.json

rm -f basic-out.json
node ../../lambda-runner.js ./cases/basic/basic-event.json basic-out.json >/dev/null
hangup2_valid_ts=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)
python3 ../../lambda-runner.py basic-event.json basic-out.json
hangup2_valid_py=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)

hangup2_valid=$($hangup2_valid_ts && $hangup2_valid_py)

# outbound
echo ""; echo "Testing OUTBOUND Input"; echo ""; echo ""

rm -f basic-event.json
cat ../../../../events/inbound.json | jq '.InvocationEventType = "NEW_OUTBOUND_CALL"' >>basic-event.json
rm -f basic-out.json
node ../../lambda-runner.js ./cases/basic/basic-event.json basic-out.json >/dev/null
outbound_valid_ts=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)
python3 ../../lambda-runner.py basic-event.json basic-out.json
outbound_valid_py=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)

outbound_valid=$($outbound_valid_ts && $outbound_valid_py)

# ringing
echo ""; echo "Testing RINGING Input"; echo ""; echo ""

rm -f basic-event.json
cat ../../../../events/inbound.json | jq '.InvocationEventType = "RINGING"' >>basic-event.json
rm -f basic-out.json
node ../../lambda-runner.js ./cases/basic/basic-event.json basic-out.json >/dev/null
ringing_valid_ts=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)
python3 ../../lambda-runner.py basic-event.json basic-out.json
ringing_valid_py=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)

ringing_valid=$($ringing_valid_ts && $ringing_valid_py)

# answered
echo ""; echo "Testing CALL_ANSWERED Input"; echo ""; echo ""

rm -f basic-event.json
cat ../../../../events/inbound.json | jq '.InvocationEventType = "CALL_ANSWERED"' >>basic-event.json
rm -f basic-out.json
node ../../lambda-runner.js ./cases/basic/basic-event.json basic-out.json >/dev/null
answered_valid_ts=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)
python3 ../../lambda-runner.py basic-event.json basic-out.json
answered_valid_py=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)

answered_valid=$($answered_valid_ts && $answered_valid_py)

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

success=$($single_client_valid && $blank_valid && $success_valid && $hangup_valid && $hangup2_valid && $outbound_valid && $ringing_valid && $answered_valid && $badsel_valid)
$success && echo "PASSES" || echo "FAILS"

if [ -z $success ]
then
    exit 0
else
    exit 1
fi