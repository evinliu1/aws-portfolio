import json
import uuid

import boto3
import pytest

from conftest import RESUME_BUCKET

SESSION_EXPIRES_AT = 1_900_000_000
CLOUDFRONT_HEADERS = {
    "CloudFront-Viewer-Country": "US",
    "CloudFront-Viewer-Country-Region-Name": "Washington",
}


@pytest.fixture
def session_id(table):
    """A visit that already exists, as if POST /api/visits had just run."""
    session_id = str(uuid.uuid4())
    table.put_item(
        Item={"pk": f"SESSION#{session_id}", "sk": "META", "expires_at": SESSION_EXPIRES_AT}
    )
    return session_id


@pytest.fixture
def inbox(resume_topic_arn):
    """An SQS queue subscribed to the topic, so tests can read what SNS sent."""
    sqs = boto3.client("sqs")
    queue_url = sqs.create_queue(QueueName="test-inbox")["QueueUrl"]
    queue_arn = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])[
        "Attributes"
    ]["QueueArn"]
    boto3.client("sns").subscribe(TopicArn=resume_topic_arn, Protocol="sqs", Endpoint=queue_arn)

    def read():
        messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10).get(
            "Messages", []
        )
        return [json.loads(m["Body"]) for m in messages]

    return read


def call(resume_handler, payload=None, headers=None):
    body = payload if isinstance(payload, str) or payload is None else json.dumps(payload)
    event = {"httpMethod": "POST", "path": "/api/resume", "body": body, "headers": headers}
    response = resume_handler.lambda_handler(event, None)
    return response, json.loads(response["body"])


def test_returns_a_short_lived_download_link(resume_handler):
    response, body = call(resume_handler)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"
    assert set(body) == {
        "url",
        "expiresInSeconds",
        "firstDownload",
        "notified",
        "coldStart",
        "handlerMs",
    }
    assert body["expiresInSeconds"] == 300
    url = body["url"]
    assert RESUME_BUCKET in url
    assert "/resume.pdf?" in url
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in url
    assert "X-Amz-Expires=300" in url
    assert "response-content-disposition=attachment" in url


def test_works_without_a_session_but_notifies_nobody(resume_handler, inbox):
    _, body = call(resume_handler)

    assert body["firstDownload"] is False
    assert body["notified"] is False
    assert inbox() == []


def test_first_download_is_recorded_and_notifies(resume_handler, table, session_id, inbox):
    _, body = call(resume_handler, {"sessionId": session_id}, CLOUDFRONT_HEADERS)

    assert body["firstDownload"] is True
    assert body["notified"] is True
    item = table.get_item(Key={"pk": f"SESSION#{session_id}", "sk": "META"})["Item"]
    assert "resume_downloaded_at" in item
    [message] = inbox()
    assert message["Subject"] == "Your resume was downloaded"
    assert message["Message"].startswith("Someone in Washington, US just downloaded")


def test_repeat_download_does_not_notify_again(resume_handler, session_id, inbox):
    call(resume_handler, {"sessionId": session_id})
    _, second = call(resume_handler, {"sessionId": session_id})

    assert second["firstDownload"] is False
    assert second["notified"] is False
    assert "url" in second
    assert len(inbox()) == 1


def test_unknown_session_gets_the_link_but_stores_nothing(resume_handler, table, inbox):
    _, body = call(resume_handler, {"sessionId": str(uuid.uuid4())})

    assert "url" in body
    assert body["notified"] is False
    assert table.scan()["Count"] == 0
    assert inbox() == []


def test_notification_without_location(resume_handler, session_id, inbox):
    call(resume_handler, {"sessionId": session_id})

    [message] = inbox()
    assert message["Message"].startswith("Someone just downloaded")


def test_failed_notification_still_returns_the_link(
    resume_handler, session_id, monkeypatch
):
    monkeypatch.setattr(
        resume_handler, "TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:does-not-exist"
    )

    response, body = call(resume_handler, {"sessionId": session_id})

    assert response["statusCode"] == 200
    assert "url" in body
    assert body["firstDownload"] is True
    assert body["notified"] is False


@pytest.mark.parametrize(
    "payload",
    ["not json", "[]", {"sessionId": "not-a-uuid"}, {"sessionId": 12345}],
    ids=["not-json", "not-an-object", "bad-session", "session-not-a-string"],
)
def test_bad_requests_return_400(resume_handler, payload):
    response, body = call(resume_handler, payload)

    assert response["statusCode"] == 400
    assert "error" in body


def test_cold_start_only_on_first_call(resume_handler):
    _, first = call(resume_handler)
    _, second = call(resume_handler)

    assert first["coldStart"] is True
    assert second["coldStart"] is False
