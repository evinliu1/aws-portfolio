import importlib
import sys

import boto3
import pytest
from moto import mock_aws

TABLE_NAME = "test-visits"


@pytest.fixture
def aws_env(monkeypatch):
    """Fake credentials so boto3 can never reach a real AWS account."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("TABLE_NAME", TABLE_NAME)


@pytest.fixture
def table(aws_env):
    """A moto-backed DynamoDB table shaped like the real one."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


def _fresh_import(module_name):
    """Import a handler fresh for each test.

    Each module creates its boto3 Table and cold-start flag at import time,
    so reloading gives every test a clean cold start pointed at the mock table.
    """
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


@pytest.fixture
def visits_handler(table):
    return _fresh_import("visits.handler")


@pytest.fixture
def events_handler(table):
    return _fresh_import("events.handler")
