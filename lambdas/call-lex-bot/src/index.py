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
bot_alias = os.getenv('BOT_ARN', 'paste-arn-here')

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

voice_focus_action = {
  'Type': "VoiceFocus",
  'Parameters': {
    'Enable': True, # false         # required
    'CallId': "call-id-1",          # required
  }
}

start_bot_conversation_action = {
  'Type': "StartBotConversation",
  'Parameters': {
    'BotAliasArn': "none",
    'LocaleId': "en_US",
    'Configuration': {
      'SessionState': {
        'DialogAction': {
          'Type': "ElicitIntent"
        }
      },
      'WelcomeMessages': [
        {
          'ContentType': "PlainText",
          'Content': "Welcome to AWS Chime SDK Voice Service. Please say what you would like to do.  For example: I'd like to book a room, or, I'd like to rent a car."
        },
      ]
    }
  },
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

    response['Actions'].append(deepcopy(pause_action))

    voice = deepcopy(voice_focus_action)
    voice['Parameters']['Enable'] = True
    voice['Parameters']['CallId'] = e['CallDetails']['Participants'][0]['CallId']
    response['Actions'].append(voice)

    start_bot = deepcopy(start_bot_conversation_action)
    start_bot['Parameters']['BotAliasArn'] = bot_alias
    response['Actions'].append(start_bot)

    return response

def action_succesful(e):
    response = deepcopy(response_template)

    response['Actions'].append(deepcopy(pause_action))
    last_action = deepcopy(hangup_action)
    try:
        if (e['ActionData']['IntentResult']['SessionState']['Intent']['Name'] == 'FallbackIntent'):
            start_bot = deepcopy(start_bot_conversation_action)
            start_bot['Parameters']['BotAliasArn'] = bot_alias
            last_action = start_bot
    except Exception as err:
        pass

    response['Actions'].append(last_action)

    return response 
    
# message - handler mapping table
action_handlers = {
    'NEW_INBOUND_CALL': new_call_actions,
    'ACTION_SUCCESSFUL': action_succesful
}

def handler(event, context):
    print(f"called with {event}")
    response = deepcopy(response_template)

    try:
        response = action_handlers[event['InvocationEventType']](event)
    except Exception as e:
        print(e)
    
    return response