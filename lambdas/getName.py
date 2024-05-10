import boto3
import os
import random

dynamodb = boto3.client("dynamodb", region_name = "us-east-1")

def handler(event, context):
    name = event["Details"]["Parameters"]["nameInput"]
    dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
    table = dynamodb.Table(os.environ["NAME_TABLE"])

    response = table.get_item(
        Key={
            'name': name
        }
    )

    pseudonym = choosePseudonym(response['Item']['pseudonym'])

    return {
        "name": pseudonym
    }

def choosePseudonym(pseudonymList):
    if len(pseudonymList) == 1:
        return pseudonymList[0]
    else:
        return random.choice(pseudonymList)