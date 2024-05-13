import helpers

def lambda_handler(event, context):
    sessionState = event.get('sessionState', {})
    intent = sessionState.get("intent", {})
    activeContexts = sessionState.get("activeContexts", [])
    sessionAttributes = sessionState.get("sessionAttributes", {})
    requestAttributes = event.get("requestAttributes", {})
    return helpers.elicit_intent_with_retries(intent, activeContexts, sessionAttributes, requestAttributes)