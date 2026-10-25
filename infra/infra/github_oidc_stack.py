from aws_cdk import CfnOutput, Duration, Stack, aws_iam as iam
from constructs import Construct

GITHUB_OIDC_URL = "https://token.actions.githubusercontent.com"
GITHUB_OIDC_HOST = "token.actions.githubusercontent.com"


class GitHubOidcStack(Stack):
    """Lets GitHub Actions deploy PortfolioStack without any stored AWS keys.

    GitHub signs a short-lived token for each workflow run; AWS checks the signature and
    the claims below before handing out credentials that last at most an hour.
    Deployed once by hand: the pipeline can't create the role it needs to log in.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        repo: str,
        repo_subject: str,
        environment: str,
        **kwargs,
    ) -> None:
        """repo_subject is how GitHub names the repo in its tokens' "sub" claim. This repo uses
        immutable subjects ("repo:owner@ownerId/name@repoId"), so a deleted-and-recreated repo
        with the same name can't take over the role. Check it with:
        gh api repos/<owner>/<name>/actions/oidc/customization/sub
        """
        super().__init__(scope, construct_id, **kwargs)

        provider = iam.OidcProviderNative(
            self,
            "GitHubProvider",
            url=GITHUB_OIDC_URL,
            client_ids=["sts.amazonaws.com"],
        )

        role = iam.Role(
            self,
            "DeployRole",
            description=f"Assumed by GitHub Actions in {repo} to deploy PortfolioStack",
            max_session_duration=Duration.hours(1),
            assumed_by=iam.WebIdentityPrincipal(
                provider.oidc_provider_arn,
                conditions={
                    "StringEquals": {
                        f"{GITHUB_OIDC_HOST}:aud": "sts.amazonaws.com",
                        # Only jobs in this repo's approval-gated environment, never a fork,
                        # a pull request, or any other repository.
                        f"{GITHUB_OIDC_HOST}:sub": f"{repo_subject}:environment:{environment}",
                    }
                },
            ),
        )

        # cdk deploy does its work through the roles `cdk bootstrap` created, so the
        # pipeline only needs permission to step into those, not to touch resources itself.
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                resources=[f"arn:aws:iam::{self.account}:role/cdk-hnb659fds-*-{self.account}-{self.region}"],
            )
        )

        CfnOutput(self, "DeployRoleArn", value=role.role_arn)
