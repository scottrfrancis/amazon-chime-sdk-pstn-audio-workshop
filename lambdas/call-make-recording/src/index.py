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
from copy import deepcopy 
import os

# 
# statics
#
response_template = {
    'SchemaVersion': '1.0',
    'Actions': []
}

wav_file_bucket = os.getenv('WAVFILE_BUCKET', None)

pause_action = {
    'Type': "Pause",
    'Parameters': {
        'DurationInMilliseconds': "1000"
    }
}

play_audio_action = {
    'Type': "PlayAudio",
    'Parameters': {
        'Repeat': "1",
        'AudioSource': {
            'Type': "S3",
            'BucketName': wav_file_bucket,
            'Key': "",
        }
    }
}

record_audio_action = {
  'Type': "RecordAudio",
  'Parameters': {
    'DurationInSeconds': "30",
    'CallId': "call-id-1",
    'SilenceDurationInSeconds': 3,
    'SilenceThreshold': 100,
    'RecordingTerminators': [
      "#"
    ],
    'RecordingDestination': {
      'Type': "S3",
      'BucketName': wav_file_bucket,
      'Prefix': ""
    }
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
    response = deepcopy(response_template)
    print(f"actions are {response['Actions']}")

    response['Actions'].append(deepcopy(pause_action))

    speak = deepcopy(speak_action)
    speak['Parameters']['Text'] =  "<speak>Hello!  Please record a message after the tone, and press pound when you are done.</speak>"
    response['Actions'].append(speak)    

    response['TransactionAttributes'] = { "state": "new" }

    return response

def beep_call(e):
    response = deepcopy(response_template)
    print(f"actions are {response['Actions']}")

    response['TransactionAttributes'] = { "state": "beeping" }

    response['Actions'].append(deepcopy(pause_action))

    play = deepcopy(play_audio_action)
    play['Parameters']['AudioSource']['Key'] = "500hz-beep.wav"

    response['Actions'].append(play)

    return response

def record_call(e):
    response = deepcopy(response_template)
    print(f"actions are {response['Actions']}")

    response['TransactionAttributes'] = { "state": "recording" }
    record = deepcopy(record_audio_action)
    try:
        if (record['Parameters']['RecordingDestination']['BucketName'] == None):
            record['Parameters']['RecordingDestination'].pop('BucketName')
    except:
        pass

    record['Parameters']['CallId'] = e['CallDetails']['Participants'][0]['CallId']
    record['Parameters']['RecordingDestination']['Prefix'] = f"{e['CallDetails']['Participants'][0]['CallId']}-"
    response['Actions'].append(record)

    return response

def playback_recording(e):
    response = deepcopy(response_template)
    print(f"actions are {response['Actions']}")

    response['TransactionAttributes'] = { "state": "playing" }

    response['Actions'].append(deepcopy(pause_action))

    speak = deepcopy(speak_action)
    speak['Parameters']['Text'] =   "<speak>Your message said</speak>"
    response['Actions'].append(speak)    

    play = deepcopy(play_audio_action)
    play['Parameters']['AudioSource']['Key'] = e['ActionData']['RecordingDestination']['Key']
    response['Actions'].append(play)

    return response

def end_call(e):
    response = deepcopy(response_template)
    print(f"actions are {response['Actions']}")

    response['TransactionAttributes'] = { "state": "finishing" }
    
    response['Actions'].append(deepcopy(pause_action))

    speak = deepcopy(speak_action)
    speak['Parameters']['Text'] = "<speak>Thank you!  Goodbye!</speak>"
    response['Actions'].append(speak)  

    response['Actions'].append(deepcopy(hangup_action))

    return response

# state transition table - maps current state to next
# the tranisition trigger is the 'ACTION_SUCCESSFUL' event 
transitions = {
    # current: handler to create next state
    'new': beep_call,
    'beeping': record_call,
    'recording': playback_recording,
    'playing': end_call
}
def run_state_machine(e):
    response = deepcopy(response_template)

    try:
        current_state = e['CallDetails']['TransactionAttributes']['state']
        print(f"current state: {current_state}")
        response = transitions[e['CallDetails']['TransactionAttributes']['state']](e)
    except Exception as err:
        print(f"caught {err}")
    
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

    return deepcopy(response_template)


def call_answered(e):
    response = deepcopy(response_template)

    response['Actions'].append(deepcopy(pause_action))

    speak = deepcopy(speak_action)
    speak['Parameters']['Text'] = "<speak>Hello!  I am just calling you back!  Goodbye!</speak>"
    response['Actions'].append(speak)

    response['Actions'].append(deepcopy(pause_action))
    response['Actions'].append(deepcopy(hangup_action))

    return response
    
# message - handler mapping table
action_handlers = {
    'NEW_INBOUND_CALL': new_call_actions,
    'ACTION_SUCCESSFUL': run_state_machine
}

def handler(event, context):
    print(f"called with {event}")
    response = deepcopy(response_template)

    try:
        response = action_handlers[event['InvocationEventType']](event)
    except Exception as e:
        print(e)
    
    print(f"returning {response}")
    return response