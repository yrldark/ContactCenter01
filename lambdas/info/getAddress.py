
import logging
import json
import helpers
import os
import address_helpers
import boto3
import re
import parse_address

logger = logging.getLogger()
logger.setLevel(logging.INFO)

location = boto3.client('location')
db = boto3.resource("dynamodb")

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

    # check for ZipCode slot; elicit it if not available
    zip_code = None
    zip_code_elicited = False
    zipCode = slot_values.get('ZipCode', None)
    if zipCode is not None:
        zip_code = zipCode['value'].get('interpretedValue', None)
        if zip_code is not None:
            if len(zip_code) != 5:
                zip_code = None

    if zip_code is not None:
        zip_code_elicited = True
        logger.debug('<<{}>> ZipCode slot = {}'.format(intent_name, zip_code))
    else:
        response = helpers.elicit_slot_with_retries(intent, activeContexts, sessionAttributes, "ZipCode", requestAttributes)
        logger.info('<<{}>> elicitSlot response = {}'.format(intent_name, json.dumps(response)))
        return response
    
    logger.debug('<<{}>> zip_code = "{}"'.format(intent_name, zip_code))

    # if no StreetAddress slot, elicit for it
    street_address = None
    streetAddress = slot_values.get('StreetAddress', None)
    if streetAddress is not None:
        street_address = streetAddress['value'].get('interpretedValue', None)
        logger.debug('<<{}>> StreetAddress = {}'.format(intent_name, street_address))
    else:
        # give them a little extra time for this response
        sessionAttributes['x-amz-lex:audio:end-timeout-ms:' + intent_name + ':StreetAddress'] = 2000
        response = helpers.elicit_slot_with_retries(intent, activeContexts, sessionAttributes, "StreetAddress", requestAttributes)
        logger.info('<<{}>> elicitSlot response = {}'.format(intent_name, json.dumps(response)))
        return response
        
    # convert text to digits in the street address user utterance
    logger.info('<<{}>> raw StreetAddress transcription = {}'.format(intent_name, street_address))
    street_address = parse_address.parse(street_address)
    logger.info('<<{}>> post-processed StreetAddress transcription = {}'.format(intent_name, street_address))

    sessionAttributes['inputAddress'] = street_address

    # get (latest) spelled street name
    spelled_street_name = None
    spelledStreetName = slot_values.get('SpelledStreetName', None)
    if spelledStreetName is not None:
        spelled_street_name = spelledStreetName['value'].get('interpretedValue', None)
        spelled_street_name = address_helpers.fix_spelled_street_name(spelled_street_name)
        logger.debug('<<{}>> SpelledStreetName slot = {}'.format(intent_name, spelled_street_name))
        
        attribute = helpers.store_value('spelled_street_name', spelled_street_name, sessionAttributes)
        value = helpers.get_latest_value('spelled_street_name', sessionAttributes)
        logger.debug('<<{}>> stored {} = {}'.format(intent_name, attribute, value))
        
        # remove the slot value as we have stored it in a session attribute
        slot_values['SpelledStreetName'] = None
    
    else:
        spelled_street_name = helpers.get_latest_value('spelled_street_name', sessionAttributes)

    # get (latest) said street name, if available
    street_name = None
    streetName = slot_values.get('StreetName', None)
    if streetName is not None:
        street_name = streetName['value'].get('interpretedValue', None)
        logger.debug('<<{}>> StreetName slot = {}'.format(intent_name, street_name))
        
        attribute = helpers.store_value('street_name', street_name, sessionAttributes)
        value = helpers.get_latest_value('street_name', sessionAttributes)
        logger.debug('<<{}>> stored {} = {}'.format(intent_name, attribute, value))

        # remove the slot value as we have stored it in a session attribute
        slot_values['StreetName'] = None
    
    else:
        street_name = helpers.get_latest_value('street_name', sessionAttributes)

    # get (latest) street address number, if available
    street_address_number = None
    streetAddressNumber = slot_values.get('StreetAddressNumber', None)
    if streetAddressNumber is not None:
        street_address_number = streetAddressNumber['value'].get('interpretedValue', None)
        logger.debug('<<{}>> StreetAddressNumber slot = {}'.format(intent_name, street_address_number))
        
        attribute = helpers.store_value('street_address_number', street_address_number, sessionAttributes)
        value = helpers.get_latest_value('street_address_number', sessionAttributes)
        logger.debug('<<{}>> stored {} = {}'.format(intent_name, attribute, value))

        # remove the slot value as we have stored it in a session attribute
        slot_values['StreetAddressNumber'] = None
    
    else:
        street_address_number = helpers.get_latest_value('street_address_number', sessionAttributes)

    # prepare the query for Amazon Location Service
    
    # if spelled or said street name available, prepend it to the street address
    if spelled_street_name is not None:
        logger.debug('<<{}>> prepending spelled street name {}'.format(intent_name, spelled_street_name))
        street_address = spelled_street_name + ' ' + street_address
    elif street_name is not None:
        logger.debug('<<{}>> prepending said street name {}'.format(intent_name, street_name))
        street_address = street_name + ' ' + street_address

    # if street address number is available, substitute it in the street address
    if street_address_number is not None:
        logger.debug('<<{}>> substituting street address number {}'.format(intent_name, street_address_number))
        match = re.search("^([^0-9]*)([0-9]+)([^0-9]*)(.*)$", street_address)
        if match is not None:
            parsed_address = match.groups()
            street_address = parsed_address[0] + ' '+ street_address_number + ' ' + parsed_address[2] + ' ' + parsed_address[3]
        else:
            street_address = street_address_number + ' ' + street_address

    # append zip code to the street address
    street_address = street_address + ' ' + zip_code

    # remove any . characters 
    street_address = street_address.replace('.', '')

    # search for and address, and confirm with the user
    if confirmationStatus == 'None':
        logger.info('<<{}>> sending query to AWS Location Service: "{}"'.format(intent_name, street_address))

        # validate the address using the AWS Location Service
        try:
            location_response = location.search_place_index_for_text(IndexName=os.environ["INDEX_NAME"],Text=street_address)
            logger.info('<<{}>> Location Service response = {}'.format(intent_name, json.dumps(location_response)))
        except location.exceptions.ResourceNotFoundException as e:
            logger.warning('<<{}>> Location service index not found: ... creating'.format(intent_name))

            location_response = location.create_place_index(
                IndexName=os.environ["INDEX_NAME"], Description='Place index for Lex update address example',
                DataSource='Esri', DataSourceConfiguration={'IntendedUse': 'SingleUse'}
            )
            logger.warning('<<{}>> Location service create index response = {}'.format(intent_name, json.dumps(location_response, default=str)))
            
            location_response = location.search_place_index_for_text(IndexName=os.environ["INDEX_NAME"],Text=street_address)
            logger.info('<<{}>> Location Service response = {}'.format(intent_name, json.dumps(location_response)))

        resolvedAddress = None
        addressNumber = None
        street = None
        city = None
        stateProvince = None
        subRegion = None
        postalCode = None

        if location_response.get('Results', None) is not None:
            for address in location_response['Results']:
                if address.get('Place', None) is not None:
                    addressLabel = address['Place'].get('Label', None)
                    logger.debug('<<{}>> checking address = {}'.format(intent_name, addressLabel))
    
                    street = address['Place'].get('Street', None)
                    addressNumber = address['Place'].get('AddressNumber', None)
                    postalCode = address['Place'].get('PostalCode', None)
                    if postalCode is not None:
                        postalCode = postalCode.replace(' ', '-')

                    if street is None:
                        logger.debug('<<{}>> skipping address, no Street'.format(intent_name))
                        continue
                    
                    if addressNumber is None:
                        logger.debug('<<{}>> skipping address, no AddressNumber'.format(intent_name))
                        continue
                    
                    if zip_code is not None:
                        if postalCode[:len(zip_code)] != zip_code:
                            logger.debug('<<{}>> skipping address, wrong PostalCode'.format(intent_name))
                            continue
                        
                    already_tried = False
                    prior_suggestions = helpers.get_all_values('suggested_address', sessionAttributes)
                    for prior_suggestion in prior_suggestions:
                        if addressLabel == prior_suggestion:
                            already_tried = True
                            break
                    
                    if already_tried:
                        logger.debug('<<{}>> skipping address, already tried: {}'.format(intent_name, addressLabel))
                        continue

                    # the first entry with a valid street that was not already tried is the next best guess
                    resolvedAddress = addressLabel
                    addressNumber = address['Place'].get('AddressNumber', None)
                    city = address['Place'].get('Municipality', None)
                    stateProvince = address['Place'].get('Region', None)
                    subRegion = address['Place'].get('SubRegion', None)
                    break

        if resolvedAddress is not None:
            logger.debug('<<{}>> FOUND A POSSIBLE MATCH'.format(intent_name))
            if (event.get('inputMode') == 'Speech'):
                response_string = '<speak>OK, your new address is <say-as interpret-as="address">' + resolvedAddress + '</say-as>.'
                response_string += ' Is that right?</speak>'
                response_message = helpers.format_message_array(response_string, 'SSML')
            else:
                response_string = 'OK, the address you\'d like a brochure mailed to is ' + resolvedAddress + '. Is that right?'
                response_message = helpers.format_message_array(response_string, 'PlainText')
            intent['state'] = 'Fulfilled'

            sessionAttributes['resolvedAddress'] = resolvedAddress
            sessionAttributes['addressNumber'] = addressNumber
            sessionAttributes['street'] = street
            sessionAttributes['city_municipality'] = city
            sessionAttributes['state_province'] = stateProvince
            sessionAttributes['subRegion'] = subRegion
            sessionAttributes['postal_code'] = postalCode
   
            # store this suggested address
            attribute = helpers.store_value('suggested_address', resolvedAddress, sessionAttributes)
            value = helpers.get_latest_value('suggested_address', sessionAttributes)
            logger.debug('<<{}>> stored {} = {}'.format(intent_name, attribute, value))
            
            response = helpers.confirm(intent, activeContexts, sessionAttributes, response_message, requestAttributes)
            logger.info('<<{}>> confirm response = {}'.format(intent_name, json.dumps(response)))
            return response
            
        else:
            return address_helpers.next_retry(event, 'no-match')
            
    elif confirmationStatus == 'Confirmed': 
        #Put in dynamo table  
        try:
            table = db.Table(os.environ["ADDRESS_TABLE"])
            table.put_item(Item={'address':sessionAttributes.get('resolvedAddress'),
                'city': sessionAttributes.get('city_municipality'),
                'state': sessionAttributes.get('state_province')
                })
        except Exception as error:
            print(error)
            response_string = 'Table Insert Confirmation error'
            response_message = helpers.format_message_array(response_string, 'PlainText')
            intent['state'] = 'Fulfilled'
            response = helpers.close(intent, activeContexts, sessionAttributes, response_message, requestAttributes)
            logger.info('<<{}>> close response = {}'.format(intent_name, json.dumps(response)))
            return response

        response_string = 'OK, we will mail a brochure to ' + sessionAttributes.get('resolvedAddress')
        response_message = helpers.format_message_array(response_string, 'PlainText')
        intent['state'] = 'Fulfilled'
        sessionAttributes['addressConfirmed'] = 1

        if sessionAttributes.get('StreetAddress_retries'):
            del sessionAttributes['StreetAddress_retries']

        response = helpers.close(intent, activeContexts, sessionAttributes, response_message, requestAttributes)
        logger.info('<<{}>> close response = {}'.format(intent_name, json.dumps(response)))
        return response

    elif confirmationStatus == 'Denied':

        return address_helpers.next_retry(event, 'incorrect')

    else:
        response_string = 'Confirmation error'
        response_message = helpers.format_message_array(response_string, 'PlainText')
        intent['state'] = 'Fulfilled'
        response = helpers.close(intent, activeContexts, sessionAttributes, response_message, requestAttributes)
        logger.info('<<{}>> close response = {}'.format(intent_name, json.dumps(response)))
        return response

