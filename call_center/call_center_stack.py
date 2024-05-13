from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    aws_dynamodb as dynamodb,
    aws_sns as sns,
    aws_lambda as _lambda,
    aws_sns_subscriptions as subscriptions,
    aws_location_alpha as location,
    aws_iam as iam
)
import boto3

#ssm = boto3.client('ssm')



class CallCenterStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a new DynamoDB table
        nametable = dynamodb.Table(self, "nameTable", partition_key=dynamodb.Attribute(name="name", type=dynamodb.AttributeType.STRING))

#-----------------------------------------
        #SNS
#-----------------------------------------

        emailSubscriptionTopic = sns.Topic(self, "emailSubscriptionTopic",
            display_name="Email Subscription Topic"
        )
        #destinationEmail = ssm.get_parameter(
        #    Name='infoEmail',
        #   WithDecryption=False
        #)
        emailSubscriptionArn = emailSubscriptionTopic.topic_arn

#---------------------------------------
        #PLACE
#---------------------------------------

        place_index = location.PlaceIndex(self, "AddressPlaceIndex",
            place_index_name="AddressPlaceIndex"
        )

#---------------------------------------
        #DYNAMODB
#---------------------------------------

        addresstable = dynamodb.Table(self, "addressTable", partition_key=dynamodb.Attribute(name="address", type=dynamodb.AttributeType.STRING))

#---------------------------------------
        #LAMBDAS
#---------------------------------------
        #GETNAME LAMBDA
        getName=_lambda.Function(
            self, 'getName',
            runtime=_lambda.Runtime.PYTHON_3_12,
            code = _lambda.Code.from_asset("lambdas"),
            environment={ 
                "NAME_TABLE": nametable.table_name
            },
            handler='getName.handler'
        )

        nametable.grant_read_data(getName)

    
        #GETADDRESS LAMBDA
        getInfo =_lambda.Function(
            self, 'getInfo',
            runtime=_lambda.Runtime.PYTHON_3_12,
            code = _lambda.Code.from_asset("lambdas/info"),
            environment={ 
                "INDEX_NAME": place_index.place_index_name,
                "ADDRESS_TABLE": addresstable.table_name,
                "TOPIC_ARN": emailSubscriptionArn
            },
            handler='handler.handler'
        )

        

        place_index.grant(getInfo, "geo:CreatePlaceIndex")
        place_index.grant(getInfo, "geo:SearchPlaceIndexForText")
        addresstable.grant_write_data(getInfo)
        getInfoRole = getInfo.role

        getInfoRole.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sns:Subscribe"],
            resources=[emailSubscriptionArn],
        ))
