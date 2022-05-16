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
import json
import logging
import os


# Set LogLevel using environment variable, fallback to INFO if not present
logger = logging.getLogger()
log_level = os.getenv('LogLevel', 'INFO')
if log_level not in ['INFO', 'DEBUG']:
    log_level = 'INFO'
logger.setLevel(log_level)
log_prefix = ''


#
# statics
#
wav_file_bucket = os.getenv('WAVFILE_BUCKET', None)

transcribe_client = boto3.client('transcribe')
s3_client = boto3.client('s3')



# To read more on customizing the Pause action, see https://docs.aws.amazon.com/chime/latest/dg/pause.html
def pause_action(call_id=None):
    a = {
        'Type': 'Pause',
        'Parameters': {
                # 'CallId': call_id,
                'DurationInMilliseconds': '3000'
        }
    }
    if call_id is not None:
        a['Parameters']['CallId'] = call_id

    return a


def speak_action(speak_text):
    return {
        'Type': "Speak",
        'Parameters': {
            'Engine': "neural",         # Required. Either standard or neural
            'LanguageCode': "en-US",    # Optional
            'Text': speak_text,         # Required
            'TextType': "ssml",         # Optional. Defaults to text
            'VoiceId': "Matthew"        # Required
        }
    }


def play_audio_action(key):
    return {
        'Type': "PlayAudio",
        'Parameters': {
            'Repeat': "1",
            'AudioSource': {
                'Type': "S3",
                'BucketName': wav_file_bucket,
                'Key': key,
            },
        },
    }


def record_audio_action(call_id, prefix):
    return {
        'Type': "RecordAudio",
        'Parameters': {
            'CallId': call_id,
            'DurationInSeconds': "30",
            'SilenceDurationInSeconds': 3,
            'SilenceThreshold': 100,
            'RecordingTerminators': ["#"],
            'RecordingDestination': {
                'Type': "S3",
                'BucketName': wav_file_bucket,
                'Prefix': prefix
            }}}

def transcribe_params(call_id, uri):
    return {
        'TranscriptionJobName': call_id,
        'LanguageCode': "en-US",
        'MediaFormat': "wav",
        'Media': {
            'MediaFileUri': uri,
        },
        'OutputBucketName': wav_file_bucket,
        'OutputKey': f"{call_id}/{call_id}",
    }

def hangup_action():
    return {
        'Type': "Hangup",
        'Parameters': {
            'SipResponseCode': "0",
            'ParticipantTag': "",
  },
}

###


def speak_and_get_digits_action(call_id, regex, speak_text):
    return {
        'Type': 'SpeakAndGetDigits',
        'Parameters': {
            'CallId': call_id,
            'InputDigitsRegex': regex,
            'SpeechParameters': {
                'Text': speak_text,
                'Engine': "neural",
                'LanguageCode': "en-US",
                'TextType': "ssml",
                'VoiceId': "Joanna"
            },
            'FailureSpeechParameters': {
                'Text': "<speak>Sorry, there was an error.</speak>",
                'Engine': "neural",
                'LanguageCode': "en-US",
                'TextType': "ssml",
                'VoiceId': "Joanna"
            },
            'MinNumberOfDigits': 11,
            'MaxNumberOfDigits': 11,
            'TerminatorDigits': ['#'],
            'InBetweenDigitsDurationInMilliseconds': 5000,
            'Repeat': 3,
            'RepeatDurationInMilliseconds': 10000
        }
    }


# To read more on customizing the VoiceFocus action, see https://docs.aws.amazon.com/chime/latest/dg/voicefocus.html
def voicefocus_action(call_id, enabled=True):
    return {
        'Type': 'VoiceFocus',
        "Parameters": {
                'Enable': enabled,
                'CallId': call_id,
        }
    }


# To read more on customizing the ReceiveDigits action, see https://docs.aws.amazon.com/chime/latest/dg/listen-to-digits.html
def receive_digits_action(call_id):
    return {
        'Type': 'ReceiveDigits',
        'Parameters': {
                'CallId': call_id,
                'InputDigitsRegex': '[0-1]$',
                'InBetweenDigitsDurationInMilliseconds': 1000,
                'FlushDigitsDurationInMilliseconds': 10000
        }
    }


# To read more on customizing the CallAndBridge action, see https://docs.aws.amazon.com/chime/latest/dg/call-and-bridge.html
def call_and_bridge_action(caller_id, destination):
    return {
        'Type': 'CallAndBridge',
        'Parameters': {
            'CallTimeoutSeconds': 30,
            'CallerIdNumber': caller_id,
            'RingbackTone': {
                'Type': "S3",
                'BucketName': wav_file_bucket,
                'Key': "ringback.wav"
            },
            'Endpoints':
            [
                {
                    'Uri': destination,
                    'BridgeEndpointType': 'PSTN'
                }
            ]
        }
    }


# A wrapper for all responses back to the service
def response(*actions):
    return {
        'SchemaVersion': '1.0',
        'Actions': [*actions]
    }

#
# handlers
#


# For new incoming calls, speak a greeting and collect digits of destination number.
# Regex for digits entered allows US calling, except for premium rate numbers
def new_call_handler(e):
    resp = response(
        pause_action(),
        speak_action(
            "<speak>Hello!  Please record a message after the tone, and press pound when you are done.</speak>")
    )
    resp['TransactionAttributes'] = {"state": "new"}

    return resp


def place_call(e):
    call_id = e['CallDetails']['Participants'][0]['CallId']
    from_number = e['CallDetails']['Participants'][0]['From']
    received_digits = f"+{e['ActionData']['ReceivedDigits']}"

    return [
        pause_action(call_id),
        call_and_bridge_action(from_number, received_digits)
    ]


def connect_call(e):
    caller = list(filter(lambda p: p['Direction'] ==
                  "Inbound", e['CallDetails']['Participants']))[0]
    recipient = list(filter(
        lambda p: p['Direction'] == "Outbound", e['CallDetails']['Participants']))[0]

    return [voicefocus_action(caller['CallId'], False),
            voicefocus_action(recipient['CallId'], False),
            receive_digits_action(caller['CallId'])
            ]

###


def beep_call(e):
    resp = response(
        pause_action(),
        play_audio_action("500hz-beep.wav")
    )
    resp['TransactionAttributes'] = {'state': 'beeping'}

    return resp


def record_call(e):
    call_id = e['CallDetails']['Participants'][0]['CallId']
    resp = response(
        record_audio_action(call_id, call_id)
    )
    resp['TransactionAttributes'] = {'state': 'recording'}

    return resp


def transcribe_recording(e):
    s3_uri = f"s3://{e['ActionData']['RecordingDestination']['BucketName']}/{e['ActionData']['RecordingDestination']['Key']}"
    call_id = e['CallDetails']['Participants'][0]['CallId']
    params = transcribe_params(call_id, s3_uri)

    try:
        r = transcribe_client.start_transcription_job(**params)

    except Exception as err:
        logger.error('Exception with Action Handler. Error: ', exc_info=err)

    resp = response(
        speak_action("<speak>Transcribing recording, please wait.  This may take up to fifteen seconds.</speak>")
    )
    resp['TransactionAttributes'] = {'state': 'transcribing',
                                     "params": params }

    return resp


def get_read_and_parse_json_object(bucket, key):
    result = s3_client.get_object(Bucket=bucket, Key=key)
    data = json.loads(result['Body'].read())

    return data


def playback_recording(e):
    # WIP
    resp = response(
        speak_action("<speak>Sorry, we encountered an error transcribing your message</speak>")
    )
    resp['TransactionAttributes'] = {'state': 'playing'}

    job_name = e['CallDetails']['TransactionAttributes']['params']['TranscriptionJobName']

    result = {}
    status = "QUEUED"
    while (status not in ("FAILED","COMPLETED")):
        try:
            result = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            status = result['TranscriptionJob']['TranscriptionJobStatus']

        except Exception as err:
            logger.error('Exception with Action Handler. Error: ', exc_info=err)
            status = 'FAILED'
            break

    if (status == 'FAILED'):
        logger.error(f"transcribe FAILED: {result}")
        return resp

    logger.info(f"transcribe complete: {result}")

    try:
        bucket = e['CallDetails']['TransactionAttributes']['params']['OutputBucketName']
        key = e['CallDetails']['TransactionAttributes']['params']['OutputKey']
        data = get_read_and_parse_json_object(bucket, key)

        resp = response(
            speak_action(f"<speak>Your message says, {data['results']['transcripts'][0]['transcript']}</speak>")
        )
        resp['TransactionAttributes'] = {'state': 'playing'}

    except Exception as err:
        logger.error('Exception getting transcription. Error: ', exc_info=err)

    return resp


def end_call(e):
    resp = response(
        pause_action(),
        speak_action("<speak>Thank you!  Goodbye!</speak>"),
        hangup_action()
    )
    resp['TransactionAttributes'] = {'state': 'finishing'}

    return resp


# If we receive an ACTION_SUCCESSFUL event we can take further actions,
# or default to responding with a NoOp (empty set of actions)
action_handlers = {
    'new': beep_call,
    'beeping': record_call,
    'recording': transcribe_recording,
    'transcribing': playback_recording,
    'playing': end_call
}


def action_succesful_handler(e):
    resp = response()

    try:
        resp = action_handlers[e['CallDetails']
                               ['TransactionAttributes']['state']](e)
    except KeyError:
        pass
    except Exception as err:
        logger.error('Exception with Action Handler. Error: ', exc_info=err)

    return resp


def digits_recevied_handler(e):
    actions = []

    try:
        if (e['ActionData']['Type'] != 'ReceivedDigits'):
            raise Exception('Action Type is not ReceivedDigits')

        caller = list(filter(
            lambda p: p['Direction'] == "Inbound", e['CallDetails']['Participants']))[0]
        recipient = list(filter(
            lambda p: p['Direction'] == "Outbound", e['CallDetails']['Participants']))[0]

        disable = e['ActionData']['ReceivedDigits'] == "0"
        enable = e['ActionData']['ReceivedDigits'] == "1"

        if not(disable ^ enable):
            raise Exception('digit not [0|1]')

        actions = [
            voicefocus_action(caller, (enable and not disable)),
            voicefocus_action(recipient, (enable and not disable)),
            receive_digits_action(caller)
        ]

    except Exception as err:
        logger.error(f"Exception in digits received.", exc_info=err)

    return response(*actions)


# message - handler mapping table
event_handlers = {
    'NEW_INBOUND_CALL': new_call_handler,
    'ACTION_SUCCESSFUL': action_succesful_handler,
    # 'HANGUP': response()
}


def handler(event, context):
    logger.info(f"called with {json.dumps(event, indent=2)}")

    resp = response()
    try:
        resp = event_handlers[event['InvocationEventType']](event)
    except KeyError:
        pass
    except Exception as e:
        logger.error(f"exception in Event Handler:", exc_info=e)

    logger.info(f"returning {json.dumps(resp, indent=2)}")
    return resp
