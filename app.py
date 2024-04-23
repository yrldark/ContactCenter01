#!/usr/bin/env python3

import aws_cdk as cdk

from call_center.call_center_stack import CallCenterStack


app = cdk.App()
CallCenterStack(app, "CallCenterStack")

app.synth()
