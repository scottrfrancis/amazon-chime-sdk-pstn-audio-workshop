#!/bin/bash

echo ""; echo "Testing Blank Input"; echo ""; echo ""

rm -f blank-event.json
echo "{}" >>blank-event.json
rm -f basic-out.json
node ../../lambda-runner.js ./cases/basic/blank-event.json basic-out.json >/dev/null 

blank_valid=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)

# copy and munge inbound event

# success
echo ""; echo "Testing ACTION_SUCCESSFUL Input"; echo ""; echo ""

rm -f basic-event.json
cat ../../../../events/inbound.json | jq '.InvocationEventType = "ACTION_SUCCESSFUL"' >>basic-event.json
rm -f basic-out.json
node ../../lambda-runner.js ./cases/basic/basic-event.json basic-out.json >/dev/null
success_valid=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)

# hangup
echo ""; echo "Testing HANGUP Input"; echo ""; echo ""

rm -f basic-event.json
cat ../../../../events/inbound.json | jq '.InvocationEventType = "HANGUP"' >>basic-event.json
rm -f basic-out.json
node ../../lambda-runner.js ./cases/basic/basic-event.json basic-out.json >/dev/null
hangup_valid=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)

# bad selector
echo ""; echo "Testing IMBAAD Input"; echo ""; echo ""

rm -f basic-event.json
cat ../../../../events/inbound.json | jq '.InvocationEventType = "IMBAAD"' >>basic-event.json
rm -f basic-out.json
node ../../lambda-runner.js ./cases/basic/basic-event.json basic-out.json >/dev/null
badsel_valid=$(ajv validate -s basic-schema.json -d basic-out.json >/dev/null && echo true || echo false)

success=$($blank_valid && $success_valid && $hangup_valid && $badsel_valid)
$success && echo "PASSES" || echo "FAILS"

if [ -z $success ]
then
    exit 0
else
    exit 1
fi