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
import json
from tabnanny import check
from jsonschema import validate
import os
import unittest
from unittest.mock import MagicMock, patch
import sys

import boto3 


class Test_Lambda_Function(unittest.TestCase):
    
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
        os.environ['WAVFILE_BUCKET'] = 'fake-bucket'


    def tearDown(self) -> None:
        # force an import the target function each and every time
        if 'index' in sys.modules:
            del sys.modules["index"]

        # remove env vars
        os.environ.pop('WAVFILE_BUCKET', None)


    def check_validate(self, d, s):
        try:
            validate(instance=d, schema=s)
            self.assertTrue(True)
        except Exception as e:
            self.assertTrue(False, e.message)

    def check_schema_10(self, d):
        self.check_validate(d, self.basic_schema)

    def check_new_call_schema(self, d):
        self.check_validate(d, self.new_call_schema)

    def check_pause(self, d, count=1):
        rp = list(filter(lambda a: a['Type'] == 'Pause', d['Actions']))
        self.assertEqual(len(rp), count)
        try:
            [ self.assertIsNotNone(r['Parameters']['DurationInMilliseconds']) for r in rp ]
        except Exception as e:
            self.assertTrue(False, e.message)

    def check_pause2(self, d):
        self.check_pause(d, count=2)

    def check_play(self, d):
        rp = list(filter(lambda a: a['Type'] == 'PlayAudio', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertIsNotNone(rp[0]['Parameters']['AudioSource'])
        except Exception as e:
            self.assertTrue(False, e.message)    

    def check_speak(self, d):
        rp = list(filter(lambda a: a['Type'] == 'Speak', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertIsNotNone(rp[0]['Parameters'])
            self.assertTrue( (rp[0]['Parameters']['Engine'] == 'neural') or
                (rp[0]['Parameters']['Engine'] == 'standard') )
            self.assertIsNotNone(rp[0]['Parameters']['Text'])
            self.assertIsNotNone(rp[0]['Parameters']['VoiceId'])

        except Exception as e:
            self.assertTrue(False, e.message)   

    def check_record_bucket_opt(self, d, check_bucket=True):
        rp = list(filter(lambda a: a['Type'] == 'RecordAudio', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            # props of Parameters to check for non-None
            [ self.assertIsNotNone(rp[0]['Parameters'][p]) 
                for p in ['DurationInSeconds', 'SilenceDurationInSeconds', 'SilenceThreshold', 'RecordingTerminators' ] ]
            
            dest_params = ['Prefix']
            if check_bucket:
                dest_params.append('BucketName')
            [ self.assertIsNotNone(rp[0]['Parameters']['RecordingDestination'][p]) for p in dest_params ]            
            
        except Exception as e:
            self.assertTrue(False, e.message)

    def check_hangup(self, d):
        rp = list(filter(lambda a: a['Type'] == 'Hangup', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertEqual(rp[0]['Parameters']['SipResponseCode'], '0')
        except Exception as e:
            self.assertTrue(False, e.message)     

    def check_transaction_state(self, d, expected_state):       
        try:
            state = d['TransactionAttributes']['state']
            self.assertEqual(state, expected_state)
        except Exception as e:
            self.assertTrue(False, e.message)

    def call_and_test(self, event, tests: array): 
        # since the static setup is tested separately, need to reload the target
        from index import handler

        r = handler(event, None)
        [ t(r) for t in tests ]

    #
    # Tests
    #

    # patch (spy on) boto to trap the client create
    #
    #   NB: the import is cached, so need to remove module after each test
    #
    @patch('boto3.client')
    def test_static_client(self, client):
        from index import handler
        self.assertTrue(client.called and (client.call_args.args[0] == 'chime'))

    def test_empty(self): 
        event = {}
        self.call_and_test(event, [self.check_schema_10])

    def test_new_call(self):
        event = self.test_event.copy()
        self.call_and_test(event,
            [ self.check_schema_10,
              self.check_new_call_schema,
              self.check_pause,
              self.check_speak,
              lambda d: self.check_transaction_state(d, "new")
        ])

    def test_success_action(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = { "state": "new" }
        self.call_and_test(event, 
            [ self.check_schema_10,
              self.check_pause,
              self.check_play,
              lambda d: self.check_transaction_state(d, "beeping")
            ])

    def test_beeping_with_bucket(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = { "state": "beeping" }

        self.call_and_test(event,
            [ self.check_schema_10,
              lambda d: self.check_record_bucket_opt(d, (os.getenv('WAVFILE_BUCKET', None) != None)),
              lambda d: self.check_transaction_state(d, "recording")
            ])

    def test_beeping_without_bucket(self):
            # unset any env var for the bucket
            os.environ.pop('WAVFILE_BUCKET', None)
            self.test_beeping_with_bucket()

    def test_success_recording(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = { "state": "recording" }
        event['ActionData'] = {  
            "RecordingDestination":{
                "Type":"S3",
                "BucketName": "valid-bucket-name",
                "Prefix":"9ff01357-23c5-4611-9dd3-f05f9d654faa-",
                "Key": "625365bf-d5a5-4237-80fd-f3cf1fb5eaad-/625365bf-d5a5-4237-80fd-f3cf1fb5eaad-0.wav"
        }}

        self.call_and_test(event,
            [ self.check_schema_10,
              self.check_pause,
              self.check_speak,
              self.check_play,
              lambda d: self.check_transaction_state(d, "playing")
            ])

    def test_success_playing(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['CallDetails']['TransactionAttributes'] = { "state": "playing" }

        self.call_and_test(event,
            [ self.check_schema_10,
              self.check_pause,
              self.check_speak,
              self.check_hangup,
              lambda d: self.check_transaction_state(d, "finishing")
            ])

    def test_hangup_action(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "HANGUP"
        # event['CallDetails']['Participants'][0]['Direction'] = "foobar"
        self.call_and_test(event, [self.check_schema_10])

    def test_second_hangup(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "HANGUP"
        event['CallDetails']['Participants'][0]['Direction'] = "foobar"
        self.call_and_test(event, [self.check_schema_10])

    def test_outbound(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "NEW_OUTBOUND_CALL"
        self.call_and_test(event, [self.check_schema_10])

    def test_ringing(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "RINGING"
        self.call_and_test(event, [self.check_schema_10])

    def test_action_failed(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "ACTION_FAILED"
        self.call_and_test(event, [self.check_schema_10])

    def test_bad_action(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "IMBAAD"
        self.call_and_test(event, [self.check_schema_10])