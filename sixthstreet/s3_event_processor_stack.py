from constructs import Construct
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    Tags,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_s3_notifications as s3_notifications,
    aws_logs as logs,
)


class S3EventProcessorStack(Stack):
    """Creates an S3 landing bucket and a Python Lambda processor.

    The Lambda is invoked when a file lands in the inbound/ prefix. It reads a
    single-line object from S3, parses the line, and writes structured logs.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        landing_bucket = s3.Bucket(
            self,
            "LandingBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
            event_bridge_enabled=False,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
        )

        # Explicit bucket policy included because the assignment asks for one.
        # enforce_ssl=True also synthesizes a deny-insecure-transport policy;
        # this statement makes the security intent clear during code review.
        landing_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="DenyInsecureTransport",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:*"],
                resources=[landing_bucket.bucket_arn, landing_bucket.arn_for_objects("*")],
                conditions={"Bool": {"aws:SecureTransport": "false"}},
            )
        )

        processor_log_group = logs.LogGroup(
            self,
            "ProcessorLogGroup",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        processor_fn = _lambda.Function(
            self,
            "SingleLineFileProcessor",
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.ARM_64,
            handler="processor.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=256,
            log_group=processor_log_group,
            environment={
                "POWERTOOLS_SERVICE_NAME": "sixthstreet-s3-processor",
                "LOG_LEVEL": "INFO",
            },
        )

        landing_bucket.grant_read(processor_fn)

        landing_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notifications.LambdaDestination(processor_fn),
            s3.NotificationKeyFilter(prefix="inbound/"),
        )

        Tags.of(self).add("Application", "sixthstreet-assessment")
        Tags.of(self).add("Owner", "cloud-engineering")
