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

from array import array
from ast import expr_context
from cmath import exp
from copy import deepcopy
import json
from jsonschema import validate
import os
import unittest
from unittest.mock import MagicMock, patch
import sys

import boto3


class Test_Call_And_Bridge(unittest.TestCase):
    bucket_env_var = "WAVFILE_BUCKET"
    fake_bucket_name = "fake-bucket"

    def __init__(self, methodName: str = ...) -> None:
        super().__init__(methodName)

        with open("../../../events/inbound.json") as f:
            self.test_event = json.load(f)

        with open("./test/cases/basic/basic-schema.json") as f:
            self.basic_schema = json.load(f)

        with open("./test/cases/new-call/new-call-schema.json") as f:
            self.new_call_schema = json.load(f)

    def setUp(self) -> None:
        super().setUp()

        # set env vars
        os.environ[Test_Call_And_Bridge.bucket_env_var] = Test_Call_And_Bridge.fake_bucket_name

    def tearDown(self) -> None:
        # force an import the target function each and every time
        if 'index' in sys.modules:
            del sys.modules["index"]

        # reset env vars
        os.environ.pop(Test_Call_And_Bridge.bucket_env_var, None)

        super().tearDown()

    def check_validate(self, d, s):
        try:
            validate(instance=d, schema=s)
            self.assertTrue(True)
        except Exception as e:
            self.assertTrue(False, e)

    def check_schema_10(self, d):
        self.check_validate(d, self.basic_schema)

    def check_new_call_schema(self, d):
        self.check_validate(d, self.new_call_schema)

    def check_empty_actions(self, d):
        try:
            self.assertEqual(len(d['Actions']), 0)
        except Exception as e:
            self.assertTrue(False, e)

    def check_pause(self, d, count=1):
        rp = list(filter(lambda a: a['Type'] == 'Pause', d['Actions']))
        self.assertEqual(len(rp), count)
        try:
            [self.assertIsNotNone(
                r['Parameters']['DurationInMilliseconds']) for r in rp]
        except Exception as e:
            self.assertTrue(False, e)

    def check_pause2(self, d):
        self.check_pause(d, count=2)

    def check_speak_collect_digits(self, d) -> None:
        rp = list(filter(lambda a: a['Type'] ==
                  'SpeakAndGetDigits', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertIsNotNone(rp[0]['Parameters']['CallId'])
            self.assertIsNotNone(rp[0]['Parameters']
                                 ['SpeechParameters']['Text'])
            self.assertIsNotNone(rp[0]['Parameters']
                                 ['FailureSpeechParameters']['Text'])
        except Exception as e:
            self.assertTrue(False, e)

    def check_call_and_bridge(self, d) -> None:
        rp = list(filter(
            lambda a: a['Type'] == 'CallAndBridge', d['Actions']))
        self.assertEqual(len(rp), 1)

        try:
            self.assertIsNotNone(rp[0]['Parameters']['CallerIdNumber'])

            for e in rp[0]['Parameters']['Endpoints']:
                self.assertIsNotNone(e['Uri'])
                self.assertIsNotNone(e['BridgeEndpointType'])

        except Exception as e:
            self.assertTrue(False, e)

    def check_voice_focus(self, d) -> None:
        rp = list(filter(
            lambda a: a['Type'] == 'VoiceFocus', d['Actions']))
        self.assertGreaterEqual(len(rp), 1)

        try:
            for v in rp:
                self.assertIsNotNone(v['Parameters']['Enable'])
                self.assertIsNotNone(v['Parameters']['CallId'])
        except Exception as e:
            self.assertTrue(False, e)

    def check_receive_digits(self, d) -> None:
        rp = list(filter(
            lambda a: a['Type'] == 'ReceiveDigits', d['Actions']))
        self.assertEqual(len(rp), 1)

        try:
            self.assertIsNotNone(rp[0]['Parameters']['InputDigitsRegex'])
        except Exception as e:
            self.assertTrue(False, e)

    def check_play(self, d):
        rp = list(filter(lambda a: a['Type'] == 'PlayAudio', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertIsNotNone(rp[0]['Parameters']['AudioSource'])
        except Exception as e:
            self.assertTrue(False, e.message)

    def check_hangup(self, d):
        rp = list(filter(lambda a: a['Type'] == 'Hangup', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertEqual(rp[0]['Parameters']['SipResponseCode'], '0')
        except Exception as e:
            self.assertTrue(False, e.message)

    def call_and_test(self, event, tests: array):
        # since the static setup is tested separately, need to reload
        from index import handler

        r = handler(event, None)
        [t(r) for t in tests]

    def copy_caller_to_recipient(self, event):
        participant = deepcopy(event['CallDetails']['Participants'][0])
        participant['Direction'] = "Outbound"
        event['CallDetails']['Participants'].append(participant)

    #
    # Tests
    #

    def test_empty(self):
        event = {}
        self.call_and_test(event, [self.check_schema_10])

    def test_wav_file_bucket_env_var(self):
        # unset any env var for the bucket
        import index
        # .setUp() sets an env var
        self.assertEqual(index.wav_file_bucket,
                         Test_Call_And_Bridge.fake_bucket_name)

        # reset it all...
        self.tearDown()
        self.assertIsNone(os.getenv(Test_Call_And_Bridge.bucket_env_var, None))

        import index
        self.assertIsNone(index.wav_file_bucket)

    def test_log_level_set_from_env_var(self):
        import index
        self.assertEqual(index.log_level, 'INFO')

        self.tearDown()
        os.environ['LogLevel'] = 'DEBUG'
        import index
        self.assertEqual(index.log_level, 'DEBUG')

    def test_new_inbound_call(self):
        event = deepcopy(self.test_event)
        self.call_and_test(event,
                           [self.check_schema_10,
                            self.check_new_call_schema,
                            self.check_pause,
                            self.check_speak_collect_digits
                            ])

    def test_action_successful_speak_get_digits(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['ActionData'] = {'Type': 'SpeakAndGetDigits',
                               'ReceivedDigits': "12125551212"}

        self.call_and_test(event,
                           [self.check_schema_10,
                            self.check_pause,
                            self.check_call_and_bridge
                            ])

    def test_action_successful_call_and_bridge(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['ActionData'] = {'Type': 'CallAndBridge'}
        # clone and munge participant[0] --> [1]
        self.copy_caller_to_recipient(event)

        self.call_and_test(event,
                           [self.check_schema_10,
                            self.check_voice_focus,
                            self.check_receive_digits
                            ])

    def test_action_successful_digits_received(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['ActionData'] = {'Type': 'ReceiveDigits'}

        self.call_and_test(event,
                           [self.check_schema_10,
                            self.check_empty_actions
                            ])

    def test_action_successful_voice_focus(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['ActionData'] = {
            'Type': 'VoiceFocus',
            'Parameters': {
                'Enable': True
            }
        }

        self.call_and_test(event,
                           [self.check_schema_10,
                            self.check_empty_actions
                            ])

    def test_action_successful_bad_selector(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['ActionData'] = {'Type': 'foobar'}

        self.call_and_test(event,
                           [self.check_schema_10,
                            self.check_empty_actions
                            ])

    def go_digits_received(self, digit, tests: array):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "DIGITS_RECEIVED"
        event['ActionData'] = {
            'Type': 'ReceivedDigits', 'ReceivedDigits': digit}

        self.copy_caller_to_recipient(event)

        self.call_and_test(event, tests)

    def test_digits_received_0(self):
        self.go_digits_received(
            "0", [self.check_schema_10, self.check_voice_focus, self.check_receive_digits])

    def test_digits_received_1(self):
        self.go_digits_received(
            "1", [self.check_schema_10, self.check_voice_focus, self.check_receive_digits])

    def test_digits_received_N(self):
        self.go_digits_received("7", [self.check_schema_10])

    def test_digits_received_no_action(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "DIGITS_RECEIVED"
        event['ActionData'] = {'Type': 'no action'}

        self.call_and_test(event, [self.check_schema_10])

    def test_hangup(self):
        # TODO
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "HANGUP"
        self.call_and_test(event, [self.check_schema_10])

    def test_bad_action(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "IMBAAD"
        self.call_and_test(event, [self.check_schema_10])
