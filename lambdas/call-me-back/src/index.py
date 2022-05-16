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

import boto3
import os

# 
# statics
#
response_template = {
    'SchemaVersion': '1.0',
    'Actions': []
}

pause_action = {
    'Type': "Pause",
    'Parameters': {
        'DurationInMilliseconds': "1000"
    }
}


speak_action = {
  'Type': "Speak",
  'Parameters': {
    'Engine': "neural",     #Required. Either standard or neural
    'LanguageCode': "en-US", # Optional
    'Text': "",             # Required
    'TextType': "ssml",     # Optional. Defaults to text
    'VoiceId': "Matthew"    # Required
  }
}

hangup_action = {
    'Type': "Hangup",
    'Parameters': {
        'SipResponseCode': "0",
        'ParticipantTag': ""
    }
}


#
# handlers
#

chime_client = boto3.client('chime')

def new_call_actions(e):
    print("new call action")
    response = response_template.copy()

    response['Actions'].append(pause_action.copy())

    speak = speak_action.copy()
    speak['Parameters']['Text'] = "<speak>Hello!  I will call you back!  Goodbye!</speak>"
    response['Actions'].append(speak)    

    response['Actions'].append(hangup_action.copy())

    response['TransactionAttributes'] = {
        "key1": "val1*",
        "key2": "val2*",
        "key3": "val3*"
      }

    return response

def hangup_and_new_call(e):
    params = {
        'FromPhoneNumber': e['CallDetails']['Participants'][0]['To'],
        'SipMediaApplicationId': e['CallDetails']['SipMediaApplicationId'],
        'ToPhoneNumber': e['CallDetails']['Participants'][0]['From'],
        'SipHeaders': {},
    }
    response = chime_client.create_sip_media_application_call(**params)
    print(response)

    return response_template.copy()


def call_answered(e):
    response = response_template.copy()

    response['Actions'].append(pause_action.copy())

    speak = speak_action.copy()
    speak['Parameters']['Text'] = "<speak>Hello!  I am just calling you back!  Goodbye!</speak>"
    response['Actions'].append(speak)

    response['Actions'].append(pause_action.copy())
    response['Actions'].append(hangup_action.copy())

    return response
    
# message - handler mapping table
action_handlers = {
    'NEW_INBOUND_CALL': new_call_actions,
    'HANGUP': hangup_and_new_call,
    'CALL_ANSWERED': call_answered
}

def handler(event, context):
    print(f"called with {event}")
    response = response_template.copy()

    try:
        response = action_handlers[event['InvocationEventType']](event)
    except Exception as e:
        print(e)
    
    return response