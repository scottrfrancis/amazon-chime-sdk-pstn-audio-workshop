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
from itertools import cycle
import json
from jsonschema import validate
import os
import unittest
from unittest.mock import MagicMock, patch
import sys

import boto3


class Test_Transcribe(unittest.TestCase):
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

        # this is what would come back from a get_object / read()
        self.canned_transcribe_result = b'{"jobName":"4623f486-0feb-476f-97e6-f60b56c4accf","accountId":"123","results":{"transcripts":[{"transcript":"This is a message to transcribe."}],"items":[{"start_time":"1.29","end_time":"1.56","alternatives":[{"confidence":"1.0","content":"This"}],"type":"pronunciation"},{"start_time":"1.56","end_time":"1.71","alternatives":[{"confidence":"1.0","content":"is"}],"type":"pronunciation"},{"start_time":"1.71","end_time":"1.83","alternatives":[{"confidence":"1.0","content":"a"}],"type":"pronunciation"},{"start_time":"1.83","end_time":"2.73","alternatives":[{"confidence":"1.0","content":"message"}],"type":"pronunciation"},{"start_time":"2.76","end_time":"2.82","alternatives":[{"confidence":"0.9094","content":"to"}],"type":"pronunciation"},{"start_time":"2.83","end_time":"3.96","alternatives":[{"confidence":"0.9975","content":"transcribe"}],"type":"pronunciation"},{"alternatives":[{"confidence":"0.0","content":"."}],"type":"punctuation"}]},"status":"COMPLETED"}'


    def setUp(self) -> None:
        super().setUp()

        # set env vars
        os.environ[Test_Transcribe.bucket_env_var] = Test_Transcribe.fake_bucket_name

    def tearDown(self) -> None:
        # force an import the target function each and every time
        if 'index' in sys.modules:
            del sys.modules["index"]

        # reset env vars
        os.environ.pop(Test_Transcribe.bucket_env_var, None)

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

    def check_speak(self, d):
        rp = list(filter(lambda a: a['Type'] == 'Speak', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertIsNotNone(rp[0]['Parameters']['Engine'])
            self.assertIsNotNone(rp[0]['Parameters']['Text'])
            self.assertIsNotNone(rp[0]['Parameters']['VoiceId'])
        except Exception as e:
            self.assertTrue(False, e)

    def check_transaction_attrs(self, d, attrs):
        try:
            self.assertIsNotNone(d['TransactionAttributes'])
            for k, v in attrs.items():
                self.assertEquals(d['TransactionAttributes'][k], v)
        except Exception as e:
            self.assertTrue(False, e)

    def check_record_audio(self, d):
        rp = list(filter(lambda a: a['Type'] == 'RecordAudio', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertIsNotNone(rp[0]['Parameters']['CallId'])
            self.assertIsNotNone(rp[0]['Parameters']['DurationInSeconds'])
            self.assertIsNotNone(rp[0]['Parameters']
                                 ['SilenceDurationInSeconds'])
            self.assertIsNotNone(rp[0]['Parameters']['SilenceThreshold'])
            self.assertIsNotNone(rp[0]['Parameters']['RecordingTerminators'])
            self.assertIsNotNone(rp[0]['Parameters']
                                 ['RecordingDestination']['Type'])

            if (os.getenv(Test_Transcribe.bucket_env_var, None) is not None):
                self.assertIsNotNone(
                    rp[0]['Parameters']['RecordingDestination']['BucketName'])

            self.assertIsNotNone(rp[0]['Parameters']
                                 ['RecordingDestination']['Prefix'])

        except Exception as e:
            self.assertTrue(False, e)


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
                         Test_Transcribe.fake_bucket_name)

        # # reset it all...
        self.tearDown()
        self.assertIsNone(os.getenv(Test_Transcribe.bucket_env_var, None))

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
        event['InvocationEventType'] = "NEW_INBOUND_CALL"

        self.call_and_test(event,
                           [self.check_schema_10,
                            self.check_pause,
                            self.check_speak,
                            lambda r: self.check_transaction_attrs(
                                r, {"state": "new"})
                            ])

    def test_action_successful_new(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = {"state": "new"}

        self.call_and_test(event,
                           [self.check_schema_10,
                            self.check_pause,
                            self.check_play,
                            lambda r: self.check_transaction_attrs(
                                r, {"state": "beeping"})
                            ])

    def test_action_successful_beeping(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = {"state": "beeping"}

        self.call_and_test(event,
                           [self.check_schema_10,
                            self.check_record_audio,
                            lambda r: self.check_transaction_attrs(
                                r, {"state": "recording"})
                            ])

    def test_action_successful_beeping_no_bucket(self):
        os.environ.pop(Test_Transcribe.bucket_env_var, None)

        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = {"state": "beeping"}

        self.call_and_test(event,
                           [self.check_schema_10,
                            self.check_record_audio,
                            lambda r: self.check_transaction_attrs(
                                r, {"state": "recording"})
                            ])

    def test_action_successful_recording_okay(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = {"state": "recording"}
        event['ActionData'] = {"RecordingDestination": {
            "BucketName": "recording-bucket",
            "Key": "recording-key"
        }}

        import index as lam
        with patch.object(lam.transcribe_client, 'start_transcription_job') as job_starter: 
            job_starter.return_value={}

            r = lam.handler(event, None)
            
            self.check_speak(r)
            self.check_transaction_attrs(r, {"state": "transcribing"})


    def test_action_successful_recording_err(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = {"state": "recording"}
        event['ActionData'] = {"RecordingDestination": {
            "BucketName": "recording-bucket",
            "Key": "recording-key"
        }}

        import index as lam
        with patch.object(lam.transcribe_client, 'start_transcription_job') as job_starter: 
            job_starter.side_effect = Exception('Boom!')

            r = lam.handler(event, None)
            
            self.check_speak(r)
            self.check_transaction_attrs(r, {"state": "transcribing"})


    status_cnt = -1
    def cycle_status(**kwargs):
        status = ['QUEUED','IN_PROGRESS', 'FAILED', 'COMPLETED']

        Test_Transcribe.status_cnt = (Test_Transcribe.status_cnt + 1) % len(status)
        return { 'TranscriptionJob': {
                    'TranscriptionJobStatus': status[Test_Transcribe.status_cnt]
        }}

    def test_action_successful_transcribing(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = {
            "state": "transcribing",
            "params": {'TranscriptionJobName': 'job-name',
            # sample test settings... can be substituted with others, or completely faked
            "OutputBucketName": "calltranscriberecordingstack-wavfiles98e3397d-1xm2sgmjz2hjl",
            "OutputKey": "4623f486-0feb-476f-97e6-f60b56c4accf/4623f486-0feb-476f-97e6-f60b56c4accf.json"
        }}

        import index as lam
        with patch.object(lam.transcribe_client, 'get_transcription_job') as job_status: 
            job_status.return_value = {
                'TranscriptionJob': {
                    'TranscriptionJobStatus': 'COMPLETED'
                }}

            r = lam.handler(event, None)

            self.check_speak(r)
            self.check_transaction_attrs(r, {"state": "playing"})

    def test_action_successful_transcribing_err(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = {
            "state": "transcribing",
            "params": {'TranscriptionJobName': 'job-name'}}

        import index as lam
        orig = lam.transcribe_client.get_transcription_job
        try:
            lam.transcribe_client.get_transcription_job = Test_Transcribe.cycle_status

            r = lam.handler(event, None)
            
            self.check_speak(r)
            self.check_transaction_attrs(r, {"state": "playing"})

        except Exception as err:
            pass

        finally:
            lam.transcribe_client.get_transcription_job = orig

    def test_action_successful_playing(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = {"state": "playing"}

        self.call_and_test(event,
                    [self.check_schema_10,
                    self.check_pause,
                    self.check_speak,
                    self.check_hangup,
                    lambda r: self.check_transaction_attrs(r, {"state": "finishing"})])


    def test_action_successful_finishing(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = {"state": "finishing"}

        self.call_and_test(event, [self.check_schema_10])

    def test_action_successful_bad_state(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = {"state": "bogus"}

        self.call_and_test(event, [self.check_schema_10])

    def test_action_successful_empty_state(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = {"state": "bogus"}

        self.call_and_test(event, [self.check_schema_10])

    def test_action_failed(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_FAILED"

        self.call_and_test(event, [self.check_schema_10])

    def test_hangup(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "HANGUP"
        self.call_and_test(event, [self.check_schema_10])

    def test_bad_action(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "IMBAAD"
        self.call_and_test(event, [self.check_schema_10])
