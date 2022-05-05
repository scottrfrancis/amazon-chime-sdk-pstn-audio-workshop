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

import os

# 
# statics
#
response_template = {
    'SchemaVersion': '1.0',
    'Actions': []
}

wav_file_bucket = os.environ.get('WAVFILE_BUCKET')

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

def new_call_actions(e):
    response = response_template.copy()

    response['Actions'].append(pause_action.copy())

    play_action = play_audio_action.copy()
    play_action['Parameters']['AudioSource']['Key'] = "hello-goodbye.wav"
    response['Actions'].append(play_action)

    response['Actions'].append(hangup_action.copy())

    response['TransactionAttributes'] = {
        "key1": "val1*",
        "key2": "val2*",
        "key3": "val3*"
      }

    return response
    
# message - handler mapping table
action_handlers = {
    'NEW_INBOUND_CALL': new_call_actions
}

def handler(event, context):
    response = response_template.copy()

    try:
        response = action_handlers[event['InvocationEventType']](event)
    except Exception as e:
        print(e)
    
    return response