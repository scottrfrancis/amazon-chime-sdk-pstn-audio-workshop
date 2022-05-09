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
from jsonschema import validate
import unittest

from index import handler


class Test_Lambda_Function(unittest.TestCase):
    
    def __init__(self, methodName: str = ...) -> None:
        super().__init__(methodName)
    
        with open("../../../events/inbound.json") as f:
            self.test_event = json.load(f)

        with open("./test/cases/basic/basic-schema.json") as f:
            self.basic_schema = json.load(f)

        with open("./test/cases/new-call/new-call-schema.json") as f:
            self.new_call_schema = json.load(f)

    def check_validate(self, d, s):
        try:
            validate(instance=d, schema=s)
            self.assert_(True)
        except Exception as e:
            self.assert_(False, e.message)

    def check_schema_10(self, d):
        self.check_validate(d, self.basic_schema)

    def check_new_call_schema(self, d):
        self.check_validate(d, self.new_call_schema)

    def check_pause(self, d):
        rp = list(filter(lambda a: a['Type'] == 'Pause', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertIsNotNone(rp[0]['Parameters']['DurationInMilliseconds'])
        except Exception as e:
            self.assert_(False, e.message)

    def check_play(self, d):
        rp = list(filter(lambda a: a['Type'] == 'PlayAudio', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertIsNotNone(rp[0]['Parameters']['AudioSource'])
        except Exception as e:
            self.assert_(False, e.message)            

    def check_hangup(self, d):
        rp = list(filter(lambda a: a['Type'] == 'Hangup', d['Actions']))
        self.assertEqual(len(rp), 1)
        try:
            self.assertEqual(rp[0]['Parameters']['SipResponseCode'], '0')
        except Exception as e:
            self.assert_(False, e.message)            

    def call_and_test(self, event, tests: array):
        r = handler(event, None)
        [ t(r) for t in tests ]

    #
    # Tests
    #

    def test_empty(self):
        event = {}
        self.call_and_test(event, [self.check_schema_10])

    def test_new_call(self):
        event = self.test_event.copy()
        self.call_and_test(event,
            [ #self.check_schema_10,
              self.check_new_call_schema,
              self.check_pause,
              self.check_play,
              self.check_hangup
        ])

    def test_success_action(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "ACTION_SUCCESSFUL"
        self.call_and_test(event, [self.check_schema_10])

    def test_hangup_action(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "HANGUP"
        self.call_and_test(event, [self.check_schema_10])

    def test_bad_action(self):
        event = self.test_event.copy()
        event['InvocationEventType'] = "IMBAAD"
        self.call_and_test(event, [self.check_schema_10])