import os

import aws_cdk as cdk

from infra.github_oidc_stack import GitHubOidcStack
from infra.infra_stack import InfraStack

app = cdk.App()
env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION"),
)

InfraStack(app, "PortfolioStack", env=env)

GitHubOidcStack(
    app,
    "GitHubOidcStack",
    repo="evinliu1/aws-portfolio",
    repo_subject="repo:evinliu1@84590384/aws-portfolio@1400898589",
    environment="production",
    env=env,
)

app.synth()
