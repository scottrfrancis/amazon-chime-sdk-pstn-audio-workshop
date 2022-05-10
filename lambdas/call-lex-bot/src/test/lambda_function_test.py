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
from copy import deepcopy
import json
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

    def tearDown(self):
        # force an import the target function each and every time
        if 'index' in sys.modules:
            del sys.modules["index"]


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

    def check_voice_focus(self, d):
        rp = list(filter(lambda a: a['Type'] == 'VoiceFocus', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertTrue(rp[0]['Parameters']['Enable'])
            self.assertIsNotNone(rp[0]['Parameters']['CallId'])
            
        except Exception as e:
            self.assertTrue(False, e.message)

    def check_start_bot_conversation(self, d):
        rp = list(filter(lambda a: a['Type'] == 'StartBotConversation', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertIsNotNone(rp[0]['Parameters']['Configuration']['SessionState']['DialogAction']['Type'])
            self.assertIsNotNone(rp[0]['Parameters']['Configuration']['WelcomeMessages'][0]['ContentType'])
            self.assertIsNotNone(rp[0]['Parameters']['Configuration']['WelcomeMessages'][0]['Content'])
            self.assertIsNotNone(rp[0]['Parameters']['LocaleId'])
            self.assertIsNotNone(rp[0]['Parameters']['BotAliasArn'])
            
        except Exception as e:
            self.assertTrue(False, e)

    def check_hangup(self, d):
        rp = list(filter(lambda a: a['Type'] == 'Hangup', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertEqual(rp[0]['Parameters']['SipResponseCode'], '0')
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

    def test_load_arn_from_env(self):
        os.environ['BOT_ARN'] = 'a::fake:::arn'
        import index

        self.assertEqual(index.bot_alias, 'a::fake:::arn')

    def test_new_call(self):
        event = deepcopy(self.test_event)
        self.call_and_test(event,
            [ self.check_schema_10,
              self.check_new_call_schema,
              self.check_pause,
              self.check_voice_focus,
              self.check_start_bot_conversation
        ])

    def test_success_no_fallback(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        self.call_and_test(event, 
            [ self.check_schema_10,
              self.check_pause,
              self.check_hangup
            ])

    def test_success_with_fallback(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        event['ActionData'] = {'IntentResult':{'SessionState':{'Intent':{'Name':"FallbackIntent"}}}}

        self.call_and_test(event, 
            [ self.check_schema_10,
              self.check_pause,
              self.check_start_bot_conversation
            ])

    def test_hangup_action(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "HANGUP"
        self.call_and_test(event, [self.check_schema_10])

    def test_bad_action(self):
        event = deepcopy(self.test_event)
        event['InvocationEventType'] = "IMBAAD"
        self.call_and_test(event, [self.check_schema_10])