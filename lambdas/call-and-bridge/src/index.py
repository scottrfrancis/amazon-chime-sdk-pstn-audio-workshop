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
    call_id = e['CallDetails']['Participants'][0]['CallId']

    logger.info('SEND {} {}'.format(
        log_prefix, 'Sending PlayAndGetDigits action to get Destination Number'))

    return response(
        pause_action(call_id),
        speak_and_get_digits_action(
            call_id,
            "^[1][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]",
            "<speak>Hello!  Please enter the number you would like to call, starting with a one followed by ten digits</speak>"
        ))


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


# If we receive an ACTION_SUCCESSFUL event we can take further actions,
# or default to responding with a NoOp (empty set of actions)
action_handlers = {
    'SpeakAndGetDigits': place_call,
    'CallAndBridge': connect_call,
    # 'ReceiveDigits': _,
    # 'VoiceFocus': _
}
def action_succesful_handler(e):
    actions = []

    try:
        actions = action_handlers[e['ActionData']['Type']](e)
    except KeyError:
        pass
    except Exception as err:
        logger.error('Exception with Action Handler. Error: ', exc_info=err)
    
    return response(*actions)


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
    'DIGITS_RECEIVED': digits_recevied_handler,
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
