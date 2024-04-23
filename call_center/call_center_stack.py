from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
)



class CallCenterStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a new DynamoDB table
        nametable = dynamodb.Table(self, "nameTable", partition_key=dynamodb.Attribute(name="name", type=dynamodb.AttributeType.STRING))

        #LAMBDAS

        #GETNAME
        getName=_lambda.Function(
            self, 'getName',
            runtime=_lambda.Runtime.PYTHON_3_12,
            code = _lambda.Code.from_asset("lambda"),
            environment={ 
                "NAME_TABLE": nametable.table_name
            },
            handler='getName.handler'
        )

        nametable.grant_read_data(getName)
        