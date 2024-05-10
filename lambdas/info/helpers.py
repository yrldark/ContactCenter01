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
import os
import base64
import gzip
import io
import re
import handler

logger = logging.getLogger()
logger.setLevel(logging.INFO)

IDENTIFICATION_SLOTS = {
    'accountId': {
        'intent_name': 'GetAccountIDHelper',
        'context': 'get_account_id',
        'context_turns': 1,
        'context_seconds': 120
    },
    'customerNumber': {
        'intent_name': 'GetCustomerNumberHelper',
        'context': 'get_customer_number',
        'context_turns': 1,
        'context_seconds': 120
    },
    'userPhone': {
        # capture attribute only
    }
}

SLOT_PROMPTS = {
    'userPhone': {
        'slotElicitationStyle': 'Default',
        'prompts': [
            'I didn\'t get that, please say or enter your 10-digit phone number',
            'Your phone number should include the area code, and be ten digits in length',
            'Sorry, I was not able to understand your phone number.'
        ]
    },
    'FullAddress': {
        'slotElicitationStyle': None,
        'prompts': [
            'OK, please tell me your address, including the street, city, state, and zip code.',
            'I didn\'t get that, please tell me your new address, including the street, city, state, and zip code.',
            'Sorry, I was not able to understand your address.'
        ]
    },
    'StreetAddress': {
        'slotElicitationStyle': None,
        'prompts': [
            'OK, what\'s your street address?',
            'I didn\'t get that, please tell me your street address, including the number and the street.',
            'Sorry, I was not able to understand your address.'
        ]
    },
    'ZipCode': {
        'slotElicitationStyle': None,
        'prompts': [
            'Please tell me your zip code.',
            'I didn\'t get that, please tell me your 5-digit zip code.',
            'Sorry, I was not able to understand your zip code.'
        ]
    },
    'EmailAddress': {
        'slotElicitationStyle': None,
        'prompts': [
            'Please tell me your new email address.',
            'I didn\'t get that, please tell me your new email address. Make sure to clearly say the at.',
            'Sorry, I was not able to understand your email address.'
        ]
    }
}


def callback_original_intent_handler(event, session_attributes, context):
    logger.debug('<<helpers>> in callback_original_intent_handler')

    callback_event = decode_data(session_attributes['callback_event'].encode('utf-8'))
    logger.debug('<<helpers>> callback_encoded = ' + session_attributes['callback_event'])
    logger.debug('<<helpers>> callback_decoded = ' + json.dumps(callback_event))

    callback_session_attributes = callback_event['sessionState'].get('sessionAttributes', {})
    for attribute in IDENTIFICATION_SLOTS:
        callback_session_attributes[attribute] = session_attributes.get(attribute, None)
        
    if welcome_message := session_attributes.get('welcomeMessage', None):
        callback_session_attributes['welcomeMessage'] = welcome_message

    callback_event['sessionState']['sessionAttributes'] = callback_session_attributes
        
    sessionState = callback_event.get('sessionState', {})
    intent = sessionState.get("intent", {})
    intent_name = intent['name']

    callback_event['invocationSource'] = 'FulfillmentCodeHook'
    return handler.HANDLERS[intent_name]['handler'](callback_event, context)


def elicit_slot(intent, activeContexts, sessionAttributes, slot, requestAttributes, slotElicitationStyle, messages=None):
    response = \
    {
        'sessionState': {
            'activeContexts': activeContexts,
            'sessionAttributes': sessionAttributes,
            'dialogAction': {
                'slotToElicit': slot,
                'type': 'ElicitSlot'
            },
            'intent': intent,
            'state': 'InProgress'
        },
        'requestAttributes': requestAttributes,
    }
    
    if slotElicitationStyle is not None:
        response['sessionState']['dialogAction']['slotElicitationStyle'] = slotElicitationStyle

    if messages:
        response['messages'] = messages    
        
    logger.debug('<<helpers>> elicit_slot response = %s', json.dumps(response))
    return response


def elicit_slot_with_retries(intent, activeContexts, sessionAttributes, slotToElicit, requestAttributes):
    slotElicitationStyle = 'Default'
    required_slot = slotToElicit.split(':')[0]
    
    slot_rule = SLOT_PROMPTS.get(slotToElicit, None)
    if not slot_rule:
        return elicit_slot(intent, activeContexts, sessionAttributes, required_slot, requestAttributes, slotElicitationStyle)

    slotElicitationStyle = slot_rule.get('slotElicitationStyle', 'Default')
    prompts = slot_rule.get('prompts', None)
    if not prompts:
        return elicit_slot(intent, activeContexts, sessionAttributes, required_slot, requestAttributes, slotElicitationStyle)

    tries = sessionAttributes.get(slotToElicit+'_retries', None)
    if not tries:
        tries = "0"

    num_tries = int(tries)
    num_prompts = len(prompts)

    # give up with final message
    if (num_tries+1) >= num_prompts:
        message = prompts[num_prompts-1]
        response_message = format_message_array(message, 'PlainText')
        del sessionAttributes[slotToElicit+'_retries']
        intent['state'] = 'Failed'
        return close(intent, activeContexts, sessionAttributes, response_message, requestAttributes)
    else:
        sessionAttributes[slotToElicit+'_retries'] = str(num_tries+1)
        message = prompts[num_tries]
        
        welcome_message = sessionAttributes.get('welcomeMessage', None)
        if welcome_message is not None:
            message = welcome_message + message
            del sessionAttributes['welcomeMessage']
            
        response_message = format_message_array(message, 'PlainText')
        return elicit_slot(intent, activeContexts, sessionAttributes, required_slot, requestAttributes, slotElicitationStyle, response_message)


def elicit_intent(intent, activeContexts, sessionAttributes, message, requestAttributes):
    response = \
    {
        'messages': message,
        'requestAttributes': requestAttributes,
        'sessionState': {
            'activeContexts': activeContexts,
            'intent': intent,
            'sessionAttributes': sessionAttributes,
            'dialogAction': {
                'type': 'ElicitIntent'
            }
        }
    }
    logger.debug('<<helpers>> elicit_intent response = ' + json.dumps(response))
    return response


def close(intent, activeContexts, sessionAttributes, message, requestAttributes):
    response = \
    {
        'messages': message,
        'requestAttributes': requestAttributes,
        'sessionState': {
            'activeContexts': activeContexts,
            'intent': intent,
            'sessionAttributes': sessionAttributes,
            'dialogAction': {
                'type': 'Close'
            }
        }
    }
    
    logger.debug('<<helpers>> close response = ' + json.dumps(response))
    return response


def delegate(intent, activeContexts, sessionAttributes, messages, requestAttributes):
    response = \
    {
        'messages': messages,
        'requestAttributes': requestAttributes,
        'sessionState': {
            'activeContexts': activeContexts,
            'intent': intent,
            'sessionAttributes': sessionAttributes,
            'dialogAction': {
                'type': 'Delegate'
            }
        }
    }
    logger.debug('<<helpers>> delegate response = ' + json.dumps(response))
    return response


def confirm(intent, activeContexts, sessionAttributes, messages, requestAttributes):
    response = \
    {
        'messages': messages,
        'requestAttributes': requestAttributes,
        'sessionState': {
            'activeContexts': activeContexts,
            'intent': intent,
            'sessionAttributes': sessionAttributes,
            'dialogAction': {
                'type': 'ConfirmIntent'
             }
        }
    }
    logger.debug('<<helpers>> confirm response = ' + json.dumps(response))
    return response


def format_message_array(message, contentType, response_card=None):
    if response_card:
        return [{'contentType': contentType, 'content': message, 'imageResponseCard': response_card}]
    else: 
        return [{'contentType': contentType, 'content': message}]


def get_attribute_safely(attribute_path, data_dict):
    return_value = None
    sub_dict = data_dict
    path = attribute_path.split(":")
    if len(path) > 0:
        for item in path:
            if sub_dict.get(item):
                next_item = sub_dict[item]
                if str(type(next_item)) == "<type 'unicode'>":
                    return next_item
                sub_dict = next_item
                return_value = next_item
            else:
                # can't walk the whole path
                return None

    return return_value


def store_value(name, value, sessionAttributes):
    counter = 1
    while sessionAttributes.get(name + '_' + str(counter), None):
        counter += 1
    attribute_name = name + '_' + str(counter)
    sessionAttributes[attribute_name] = value
    return attribute_name


def get_latest_value(name, sessionAttributes):
    stored_value = None
    counter = 1
    while tmp_value := sessionAttributes.get(name + '_' + str(counter), None):
        counter += 1
        stored_value = tmp_value
    return stored_value
    

def get_all_values(name, sessionAttributes):
    all_values = []
    counter = 1
    while tmp_value := sessionAttributes.get(name + '_' + str(counter), None):
        counter += 1
        all_values.append(tmp_value)
    return all_values


def encode_data(json_data):
    text = json.dumps(json_data)
    bytes = text.encode('utf-8')
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="w") as f:
        f.write(bytes)
    return base64.b64encode(out.getvalue()).decode('utf8')


def decode_data(encoded_str):
    data = base64.b64decode(encoded_str)
    striodata = io.BytesIO(data)
    with gzip.GzipFile(fileobj=striodata, mode='r') as f:
        data = json.loads(f.read())
    return data


def validate_number(value, length):
    if len(value) != length:
        return False

    expr = '[0-9]{' + str(length) + ',' + str(length) + '}'
    digits = re.match(expr, value)
    if not digits:
        return False

    return True


def validate_alphanumeric(value, length):
    if len(value) != length:
        return False

    expr = '[0-9A-Z]{' + str(length) + ',' + str(length) + '}'
    digits = re.match(expr, value)
    if not digits:
        return False

    return True
