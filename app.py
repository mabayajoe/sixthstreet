#!/usr/bin/env python3
import aws_cdk as cdk  # type: ignore
from sixthstreet.s3_event_processor_stack import S3EventProcessorStack

app = cdk.App()

S3EventProcessorStack(
    app,
    "SixthStreetS3EventProcessorStack",
    description="CDK stack for S3 single-line file processing with Lambda.",
)

app.synth()
