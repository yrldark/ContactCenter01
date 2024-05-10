import logging
import json
import helpers

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# see RETRY_ACTIONS dict at the bottom for configuring the sequence in next_retry()
def next_retry(event, prompt_type):
    logger.debug('<<next_retry>> starting')
    sessionState = event.get('sessionState', {})
    sessionAttributes = sessionState.get("sessionAttributes", {})

    for action in RETRY_ACTIONS:
       for attribute in action.keys():
           logger.debug("<<next_retry>> checking for attribute = {}, method = {}".format(attribute, action[attribute]['method']))
           session_attribute = sessionAttributes.get(attribute, None)
           if session_attribute is None:
               retries = sessionAttributes.get('elicitation_retries', '')
               if attribute not in retries:  # only try each action once
                   method = action[attribute].get('method', None)
                   prompt = action[attribute].get(prompt_type, None)
                   style = action[attribute].get('style', None)
                   if method is not None and prompt is not None:
                       sessionAttributes['elicitation_retries'] = retries + attribute + '|'
                       response = method(attribute, prompt, style, event)
                       logger.debug('<<next_retry>> attribute {} not found, method {} returns response {}'.format(attribute, action[attribute]['method'], json.dumps(response)))
                       return response
    
    response_string = 'next action error'
    response_message = helpers.format_message_array(response_string, 'PlainText')
    intent['state'] = 'Fulfilled'
    response = helpers.close(intent, activeContexts, sessionAttributes, response_message, requestAttributes)
    logger.error('<<next_retry>> close response = ' + json.dumps(response))
    return response


def elicit_spelled_street(attribute, prompt, style, event):
    logger.debug('<<elicit_spelled_street>> starting, attribute={}'.format(attribute))
    
    sessionState = event.get('sessionState', {})
    sessionAttributes = sessionState.get("sessionAttributes", {})

    intent = sessionState.get("intent", {})
    intent.pop('state', None)

    activeContexts = sessionState.get("activeContexts", [])
    intent_name = intent['name']

    requestAttributes = event.get("requestAttributes", {})

    response_message = helpers.format_message_array(prompt, 'PlainText')
    slotElicitationStyle = style
    response = helpers.elicit_slot(intent, activeContexts, sessionAttributes, "SpelledStreetName", requestAttributes, slotElicitationStyle, response_message)
    logger.info('<<{}>> elicit_spelled_street - elicitSlot response = {}'.format(intent_name, json.dumps(response)))

    return response


def elicit_street_address_number(attribute, prompt, style, event):
    logger.debug('<<elicit_street_address_number>> starting, attribute={}'.format(attribute))
    
    sessionState = event.get('sessionState', {})
    sessionAttributes = sessionState.get("sessionAttributes", {})

    intent = sessionState.get("intent", {})
    intent.pop('state', None)

    activeContexts = sessionState.get("activeContexts", [])
    intent_name = intent['name']

    requestAttributes = event.get("requestAttributes", {})

    response_message = helpers.format_message_array(prompt, 'PlainText')
    slotElicitationStyle = style
    response = helpers.elicit_slot(intent, activeContexts, sessionAttributes, "StreetAddressNumber", requestAttributes, slotElicitationStyle, response_message)
    logger.info('<<{}>> elicit_street_address_number - elicitSlot response = {}'.format(intent_name, json.dumps(response)))

    return response


def elicit_street_name(attribute, prompt, style, event):
    logger.debug('<<elicit_street_name>> starting, attribute={}'.format(attribute))
    
    sessionState = event.get('sessionState', {})
    sessionAttributes = sessionState.get("sessionAttributes", {})

    intent = sessionState.get("intent", {})
    intent.pop('state', None)

    activeContexts = sessionState.get("activeContexts", [])
    intent_name = intent['name']

    requestAttributes = event.get("requestAttributes", {})
    
    response_message = helpers.format_message_array(prompt, 'PlainText')
    slotElicitationStyle = style
    response = helpers.elicit_slot(intent, activeContexts, sessionAttributes, "StreetName", requestAttributes, slotElicitationStyle, response_message)
    logger.info('<<{}>> elicit_street_name - elicitSlot response = {}'.format(intent_name, json.dumps(response)))

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
    logger.info('<<{}>> route_to_agent - close response = {}'.format(intent_name, json.dumps(response)))

    return response


def fix_spelled_street_name(street_name):
    letters = list(street_name)

    for index, letter in enumerate(letters):
        if letter == '0':
            replaceWithLetter = False
            if index > 0:
                if letters[index-1].isdigit() == False:
                    replaceWithLetter = True
            if index < len(letters) - 1:
                if letters[index+1].isdigit() == False:
                    replaceWithLetter = True
            if replaceWithLetter:
                letters[index] = 'o'

    return ''.join(letters)
    

RETRY_ACTIONS = [
    { "street_name": {
          "method": elicit_street_name,
          "style": None,
          "no-match": "Thank you. To make sure I get it right, can you tell me just the name of your street?",
          "incorrect": "Let's try again. Can you tell me just the name of your street?"
       }
    },
    { "street_name_spelled_by_letter": {
          "method": elicit_spelled_street, 
          "style": "SpellByLetter",
          "no-match": "Let's try a different way. Can you please spell just the name of your street?",
          "incorrect": "Let's try a different way. Can you please spell just the name of your street?"
       }
    },
    { "street_address_number": {
          "method": elicit_street_address_number, 
          "style": None,
          "no-match": "I didn't find a matching address. Can you please tell me your street address number?",
          "incorrect": "OK, let's try your street address number. Can you tell me that once more?"
       }
    },
    { "street_name_spelled_by_word": {
          "method": elicit_spelled_street, 
          "style": "SpellByWord",
          "no-match": "Let's try one last time. Please spell the name of your street. You can use words for letters, such as a as in apple, or b like bob.",
          "incorrect": "Let's try one last time. Please spell the name of your street. You can use words for letters, such as a as in apple, or b like bob."
       }
    },
    { "agent": {
          "method": route_to_agent, 
          "style": None,
          "no-match": "Sorry, I was not able to find a match for your address. Let me get you to an agent.",
          "incorrect": "Sorry, I was not able to find a match for your address. Let me get you to an agent."
       }
    }
]
