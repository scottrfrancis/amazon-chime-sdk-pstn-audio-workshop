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

echo ""; echo "Testing New Call Input"; echo ""; echo ""

cp ../../../../events/inbound.json new-call-event.json

rm -f new-call-out.json
node ../../lambda-runner.js ./cases/new-call/new-call-event.json new-call-out.json >/dev/null
validates_ts=$(ajv validate -s new-call-schema.json -d new-call-out.json >>/dev/null 2>>/dev/null && echo true || echo false)

# validate content
#  PAUSE
has_pause_with_millis_ts=$(cat new-call-out.json | jq '.Actions[] | select(.Type=="Pause") | .Parameters.DurationInMilliseconds != null')
# PLAY
has_play_with_audio_source_ts=$(cat new-call-out.json | jq '.Actions[] | select(.Type=="PlayAudio") | .Parameters.AudioSource != null')
# HANGUP
has_hangup_resp_0_ts=$(cat new-call-out.json | jq '.Actions[] | select(.Type=="Hangup") | .Parameters.SipResponseCode == "0"')

# python
python3 ../../lambda-runner.py new-call-event.json new-call-out-py.json
validates_py=$(ajv validate -s new-call-schema.json -d new-call-out.json >>/dev/null 2>>/dev/null && echo true || echo false)

#  PAUSE
has_pause_with_millis_py=$(cat new-call-out.json | jq '.Actions[] | select(.Type=="Pause") | .Parameters.DurationInMilliseconds != null')
# PLAY
has_play_with_audio_source_py=$(cat new-call-out.json | jq '.Actions[] | select(.Type=="PlayAudio") | .Parameters.AudioSource != null')
# HANGUP
has_hangup_resp_0_py=$(cat new-call-out.json | jq '.Actions[] | select(.Type=="Hangup") | .Parameters.SipResponseCode == "0"')


validates=$($validates_ts && $validates_py)
has_pause_with_millis=$($has_pause_with_millis_ts && $has_pause_with_millis_py)
has_play_with_audio_source=$(has_play_with_audio_source_ts && $has_play_with_audio_source_py)
has_hangup_resp_0=$(has_hangup_resp_0_ts && $has_hangup_resp_0_py)

success=$($validates && $has_pause_with_millis && $has_play_with_audio_source && $has_hangup_resp_0)
$success && echo "PASSES" || echo "FAILS"

if [ -z $success ]
then
    exit 0
else
    exit 1
fi