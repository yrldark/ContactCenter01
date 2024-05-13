
import logging
import json
import helpers
import email_helpers
import boto3
import re
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns = boto3.client('sns')

def lambda_handler(event, context):
    sessionState = event.get('sessionState', {})
    sessionAttributes = sessionState.get("sessionAttributes", {})

    intent = sessionState.get("intent", {})
    intent.pop('state', None)

    activeContexts = sessionState.get("activeContexts", [])
    intent_name = intent['name']
    slot_values = intent['slots']
    confirmationStatus = intent.get('confirmationState', 'None')
   
    requestAttributes = event.get("requestAttributes", {})

    logger.info('[{}] - Lex event info {} '.format(intent_name, json.dumps(event)))

    # if no EmailAddress slot, elicit for it
    email_address = None
    emailAddress = slot_values.get('EmailAddress', None)
    if emailAddress is not None:
        email_address = emailAddress['value'].get('interpretedValue', None)
        
        if email_address is not None:
            if not email_helpers.validate_email_address(email_address):
                email_address = None
        
        if email_address is None:
            original_value = emailAddress['value'].get('originalValue', '<none>')
            logger.info('<<{}>> no match on EmailAddress slot, originalValue = {}'.format(intent_name, email_address))
            return email_helpers.next_retry(event, 'no-match')

        logger.info('<<{}>> EmailAddress = {}'.format(intent_name, email_address))
    else:
        # give them a little extra time to say their email address
        sessionAttributes['x-amz-lex:audio:end-timeout-ms:' + intent_name + ':EmailAddress'] = 2000
        return email_helpers.next_retry(event, 'no-match')

    # post-process the email address recognized by Lex
    logger.info('<<{}>> EmailAddress transcription = {}'.format(intent_name, email_address))
    sessionAttributes['inputEmailAddress'] = email_address
    
    if not email_helpers.validate_email_address(email_address):
          return address_helpers.next_retry(event, 'no-match')
            
    if confirmationStatus == 'None':
        if (event.get('inputMode') == 'Speech'):
            spoken_email_address = email_helpers.transform_email_for_speech(email_address)

            response_string = '<speak>OK, your new email address is, ' + spoken_email_address + '.'
            response_string += ' Is that right?</speak>'
            response_message = helpers.format_message_array(response_string, 'SSML')
        else:
            response_string = 'OK, your new email address is ' + email_address + '. Is that right?'
            response_message = helpers.format_message_array(response_string, 'PlainText')
        intent['state'] = 'Fulfilled'

        sessionAttributes['resolvedEmailAddress'] = email_address

        # store this suggested address
        attribute = helpers.store_value('suggested_email_address', email_address, sessionAttributes)
        value = helpers.get_latest_value('suggested_email_address', sessionAttributes)
        logger.info('<<{}>> stored {} = {}'.format(intent_name, attribute, value))
        
        response = helpers.confirm(intent, activeContexts, sessionAttributes, response_message, requestAttributes)
        logger.info('<<{}>> confirm response = {}'.format(intent_name, json.dumps(response)))
        return response

    elif confirmationStatus == 'Confirmed':
        
        response = sns.subscribe(
            TopicArn=os.environ["TOPIC_ARN"],
            Protocol='email',
            Endpoint=email_address,
            ReturnSubscriptionArn=False
        )
        response_string = 'Thank you for subscribing to our email messages.'
        response_message = helpers.format_message_array(response_string, 'PlainText')
        intent['state'] = 'Fulfilled'
        sessionAttributes['emailAddressConfirmed'] = 1

        response = helpers.close(intent, activeContexts, sessionAttributes, response_message, requestAttributes)
        logger.info('<<{}>> close response = {}'.format(intent_name, json.dumps(response)))
        return response

    elif confirmationStatus == 'Denied':
        return email_helpers.next_retry(event, 'incorrect')

    else:
        response_string = 'Confirmation error'
        response_message = helpers.format_message_array(response_string, 'PlainText')
        intent['state'] = 'Fulfilled'
        response = helpers.close(intent, activeContexts, sessionAttributes, response_message, requestAttributes)
        logger.info('<<{}>> close response = {}'.format(intent_name, json.dumps(response)))
        return response