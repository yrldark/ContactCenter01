#
# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import logging
import json
import helpers
import re

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# see RETRY_ACTIONS dict at the bottom for configuring the sequence in next_retry()
def next_retry(event, prompt_type):
    logger.debug('<<next_retry>> starting, prompt_type = {}'.format(prompt_type))
    sessionState = event.get('sessionState', {})
    sessionAttributes = sessionState.get("sessionAttributes", {})

    retry_actions = RETRY_ACTIONS.get(prompt_type, None)
    if retry_actions is not None:
        for action in retry_actions:
            for attribute in action.keys():
                logger.debug("<<next_retry>> checking for attribute = {}, prompt_type = {}".format(attribute, prompt_type))
                session_attribute = sessionAttributes.get(attribute, None)
                if session_attribute is None:
                    retries = sessionAttributes.get('elicitation_retries', '')
                    if attribute not in retries:  # only try each action once
                        method = action[attribute].get('method', None)
                        prompt = action[attribute].get('prompt', None)
                        style = action[attribute].get('style', None)
                        if method is not None and prompt is not None:
                            sessionAttributes['elicitation_retries'] = retries + attribute + '|'
                            response = method(attribute, prompt, style, event)
                            logger.debug('<<next_retry>> attribute {} not found, method {} returns response {}'.format(attribute, action[attribute]['method'], json.dumps(response)))
                            return response
        
    logger.debug('<<next_retry>> no actions for prompt_type = {}'.format(prompt_type))
    intent = sessionState.get("intent", {})
    activeContexts = sessionState.get("activeContexts", [])
    requestAttributes = event.get("requestAttributes", {})

    response_string = 'next action error'
    response_message = helpers.format_message_array(response_string, 'PlainText')
    intent['state'] = 'Fulfilled'
    response = helpers.close(intent, activeContexts, sessionAttributes, response_message, requestAttributes)
    logger.error('<<next_retry>> close response = ' + json.dumps(response))
    return response


def elicit_email_address(attribute, prompt, style, event):
    logger.debug('<<elicit_email_address>> starting, attribute={}, style={}'.format(attribute, style))
    
    sessionState = event.get('sessionState', {})
    sessionAttributes = sessionState.get("sessionAttributes", {})

    intent = sessionState.get("intent", {})
    intent.pop('state', None)

    activeContexts = sessionState.get("activeContexts", [])
    intent_name = intent['name']

    requestAttributes = event.get("requestAttributes", {})

    response_message = helpers.format_message_array(prompt, 'PlainText')
    slotElicitationStyle = style
    response = helpers.elicit_slot(intent, activeContexts, sessionAttributes, "EmailAddress", requestAttributes, slotElicitationStyle, response_message)
    logger.info('<<{}>> elicit_email_address - elicitSlot response = {}'.format(intent_name, json.dumps(response)))

    return response


def route_to_agent(attribute, prompt, style, event):
    logger.debug('<<route_to_agent>> starting, attribute={}'.format(attribute))
    
    sessionState = event.get('sessionState', {})
    sessionAttributes = sessionState.get("sessionAttributes", {})

    intent = sessionState.get("intent", {})
    intent.pop('state', None)

    activeContexts = sessionState.get("activeContexts", [])
    intent_name = intent['name']

    requestAttributes = event.get("requestAttributes", {})
    response_message = helpers.format_message_array(prompt, 'PlainText')
    
    intent['state'] = 'Fulfilled'
    sessionAttributes['sendToAgent'] = 1
    sessionAttributes['addressConfirmed'] = 0

    response = helpers.close(intent, activeContexts, sessionAttributes, response_message, requestAttributes)

    return response


def validate_email_address(email_address):
    return '@' in email_address


letter_pronounciations = {
    'b': 'b like bob', 
    'c': 'c like charlie',
    'd': 'd like dog', 
    'f': 'f like farmer', 
    'm': 'm like mary', 
    'n': 'n like nancy', 
    'p': 'p like peter', 
    's': 's like sam', 
    't': 't like tom', 
    'z': 'z like zulu'
}

def transform_email_for_speech(email_address):
    match = re.search("^([^@]+)(@)([^@]+)$", email_address)
    if match is not None:
        parsed_address = match.groups()
        if len(parsed_address) == 3:
            email_address = '<prosody rate="slow"> '
            email_address += ', '.join(parsed_address[0]) + ', '
            email_address += '</prosody> at; ' 
            email_address += parsed_address[2].replace('.', ' dot ')
    
    email_address = ' ' + email_address.replace('.,', 'dot;')
    for letter in letter_pronounciations:
        email_address = email_address.replace(
            ' ' + letter + ',', 
            ' ' + letter_pronounciations[letter] + ','
        )

    return email_address


RETRY_ACTIONS = {
    "no-match": [
        { "email_initial_prompt": {
              "method": elicit_email_address,
              "style": None,
              "prompt": "Please tell me your email address."
           }
        },
        { "email_no_match": {
              "method": elicit_email_address,
              "style": None,
              "prompt": "I didn't catch that. Can you tell me your email address again?"
           }
        },
        { "email_last_try": {
              "method": elicit_email_address,
              "style": None,
              "prompt": "Sorry, let's try again. Can you please tell me your email address? Please make sure to clearly say the, at."
           }
        },
        { "agent": {
              "method": route_to_agent, 
              "style": None,
              "prompt": "Sorry, I was not able to understand your email address. Let me get you to an agent."
           }
        }
    ],
    "incorrect": [
        { "email_incorrect_spell_by_letter": {
              "method": elicit_email_address,
              "style": "SpellByLetter",
              "prompt": "Let's try again. Can you please spell your email address for me? For example, you could say something like, dee, ay, enn, eight, nine, at gmail dot com"
           }
        },
        { "email_incorrect_spell_by_word": {
              "method": elicit_email_address,
              "style": "SpellByWord",
              "prompt": "All right, one last try. Can you please spell your email address again? You can use words for letters, such as a as in apple, or b like bob."
           }
        },
        { "agent": {
              "method": route_to_agent, 
              "style": None,
              "prompt": "Sorry, I was not able to get your email address right. Let me get you to an agent."
           }
        }
    ]
}
