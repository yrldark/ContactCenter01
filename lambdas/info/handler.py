import getAddress
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


HANDLERS = {
    'RequestBrochure': getAddress.lambda_handler
}

def handler(event, context):
    sessionState = event.get('sessionState', {})
    intent = sessionState.get("intent", {})
    intent_name = intent['name']
    logger.debug('<<handler>> handler function intent_name \"%s\"', intent_name)
    if intent_name in HANDLERS:
        return HANDLERS[intent_name](event, context)
    else:
        print("HANDLER: no intent found")