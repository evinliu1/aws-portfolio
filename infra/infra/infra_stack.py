from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_sns as sns,
)
from constructs import Construct

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"


class InfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        table = dynamodb.Table(
            self,
            "PortfolioTable",
            partition_key=dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.DESTROY,
        )

        visits_fn = self._python_function("Visits", "visits", table)
        table.grant_write_data(visits_fn)

        events_fn = self._python_function("Events", "events", table)
        table.grant_read_write_data(events_fn)  # reads the session before writing an event

        # Private: the only way in is a short-lived link signed by the resume function.
        # The PDF itself is uploaded by hand, so it never has to live in the public repo.
        resume_bucket = s3.Bucket(
            self,
            "ResumeBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        # The email subscription is added with the CLI, so the address stays out of the repo.
        downloads_topic = sns.Topic(
            self, "ResumeDownloadsTopic", display_name="Portfolio resume downloads"
        )

        resume_fn = self._python_function(
            "Resume",
            "resume",
            table,
            environment={
                "RESUME_BUCKET": resume_bucket.bucket_name,
                "TOPIC_ARN": downloads_topic.topic_arn,
            },
        )
        resume_bucket.grant_read(resume_fn, "resume.pdf")  # presigned links use these permissions
        table.grant_write_data(resume_fn)
        downloads_topic.grant_publish(resume_fn)

        api = apigw.RestApi(
            self,
            "PortfolioApi",
            endpoint_types=[apigw.EndpointType.REGIONAL],  # CloudFront is our edge
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=10,
                throttling_burst_limit=20,
            ),
        )
        api_root = api.root.add_resource("api")
        visits = api_root.add_resource("visits")
        visits.add_method("POST", apigw.LambdaIntegration(visits_fn))
        events = api_root.add_resource("events")
        events.add_method("POST", apigw.LambdaIntegration(events_fn))
        resume = api_root.add_resource("resume")
        resume.add_method("POST", apigw.LambdaIntegration(resume_fn))

        api_origin_policy = cloudfront.OriginRequestPolicy(
            self,
            "ApiOriginPolicy",
            header_behavior=cloudfront.OriginRequestHeaderBehavior.allow_list(
                "CloudFront-Viewer-Country",
                "CloudFront-Viewer-Country-Region-Name",
                "CloudFront-Is-Mobile-Viewer",
            ),
            query_string_behavior=cloudfront.OriginRequestQueryStringBehavior.all(),
            cookie_behavior=cloudfront.OriginRequestCookieBehavior.none(),
        )

        site_bucket = s3.Bucket(
            self,
            "SiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        distribution = cloudfront.Distribution(
            self,
            "SiteDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=origins.RestApiOrigin(api),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=api_origin_policy,
                ),
            },
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
        )

        s3deploy.BucketDeployment(
            self,
            "DeploySite",
            sources=[s3deploy.Source.asset(str(FRONTEND_DIST))],
            destination_bucket=site_bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )

        CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "TableName", value=table.table_name)
        CfnOutput(self, "ResumeBucketName", value=resume_bucket.bucket_name)
        CfnOutput(self, "ResumeTopicArn", value=downloads_topic.topic_arn)

    def _python_function(
        self,
        name: str,
        source_dir: str,
        table: dynamodb.Table,
        environment: dict[str, str] | None = None,
    ) -> lambda_.Function:
        """A Lambda running one handler from backend/src, with the settings every API function shares."""
        return lambda_.Function(
            self,
            f"{name}Function",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.ARM_64,  # Graviton: cheaper per ms
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset(str(BACKEND_SRC / source_dir), exclude=["__pycache__"]),
            memory_size=256,
            timeout=Duration.seconds(5),
            environment={"TABLE_NAME": table.table_name, **(environment or {})},
            log_group=logs.LogGroup(
                self,
                f"{name}Logs",
                retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=RemovalPolicy.DESTROY,
            ),
        )
