#!/bin/bash

echo ""; echo "Testing New Call Input"; echo ""; echo ""

cp ../../../../events/inbound.json new-call-event.json

rm -f new-call-out.json
node ../../lambda-runner.js ./cases/new-call/new-call-event.json new-call-out.json >/dev/null

validates=$(ajv validate -s new-call-schema.json -d new-call-out.json >>/dev/null 2>>/dev/null && echo true || echo false)
# validate content
#  PAUSE
has_pause_with_millis=$(cat new-call-out.json | jq '.Actions[] | select(.Type=="Pause") | .Parameters.DurationInMilliseconds != null')

# PLAY
has_play_with_audio_source=$(cat new-call-out.json | jq '.Actions[] | select(.Type=="PlayAudio") | .Parameters.AudioSource != null')

# HANGUP
has_hangup_resp_0=$(cat new-call-out.json | jq '.Actions[] | select(.Type=="Hangup") | .Parameters.SipResponseCode == "0"')

success=$($validates && $has_pause_with_millis && $has_play_with_audio_source && $has_hangup_resp_0)
$success && echo "PASSES" || echo "FAILS"

if [ -z $success ]
then
    exit 0
else
    exit 1
fi