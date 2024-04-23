import aws_cdk as core
import aws_cdk.assertions as assertions
from call_center.call_center_stack import CallCenterStack

def test_table_created():
    app = core.App()
    stack = CallCenterStack(app, "call-center")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::DynamoDB::Table", 1)
