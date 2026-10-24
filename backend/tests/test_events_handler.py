import json
import uuid

import pytest
from boto3.dynamodb.conditions import Key

SESSION_EXPIRES_AT = 1_900_000_000


@pytest.fixture
def session_id(table):
    """A visit that already exists, as if POST /api/visits had just run."""
    session_id = str(uuid.uuid4())
    table.put_item(
        Item={"pk": f"SESSION#{session_id}", "sk": "META", "expires_at": SESSION_EXPIRES_AT}
    )
    return session_id


def call(events_handler, payload):
    body = payload if isinstance(payload, str) or payload is None else json.dumps(payload)
    event = {"httpMethod": "POST", "path": "/api/events", "body": body}
    response = events_handler.lambda_handler(event, None)
    return response, json.loads(response["body"])


def stored_events(table, session_id):
    return table.query(
        KeyConditionExpression=Key("pk").eq(f"SESSION#{session_id}") & Key("sk").begins_with("EVENT#")
    )["Items"]


def test_heartbeat_returns_201_json(events_handler, session_id):
    response, body = call(events_handler, {"sessionId": session_id, "type": "heartbeat"})

    assert response["statusCode"] == 201
    assert response["headers"]["Content-Type"] == "application/json"
    assert set(body) == {"type", "coldStart", "handlerMs"}
    assert body["type"] == "heartbeat"


def test_heartbeat_is_saved_under_its_session(events_handler, table, session_id):
    call(events_handler, {"sessionId": session_id, "type": "heartbeat"})

    [event] = stored_events(table, session_id)
    assert event["type"] == "heartbeat"
    assert "created_at" in event
    assert "section" not in event


def test_section_view_stores_the_section(events_handler, table, session_id):
    call(events_handler, {"sessionId": session_id, "type": "section_view", "section": "skills"})

    [event] = stored_events(table, session_id)
    assert event["type"] == "section_view"
    assert event["section"] == "skills"


def test_events_expire_with_their_session(events_handler, table, session_id):
    call(events_handler, {"sessionId": session_id, "type": "heartbeat"})

    [event] = stored_events(table, session_id)
    assert event["expires_at"] == SESSION_EXPIRES_AT


def test_events_are_kept_separately_in_time_order(events_handler, table, session_id):
    for section in ["about", "skills", "behind-the-scenes"]:
        call(events_handler, {"sessionId": session_id, "type": "section_view", "section": section})

    events = stored_events(table, session_id)
    assert [e["section"] for e in events] == ["about", "skills", "behind-the-scenes"]


def test_unknown_session_returns_404(events_handler, table):
    response, body = call(events_handler, {"sessionId": str(uuid.uuid4()), "type": "heartbeat"})

    assert response["statusCode"] == 404
    assert "error" in body
    assert table.scan()["Count"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "not json",
        "[]",
        {"type": "heartbeat"},
        {"sessionId": "not-a-uuid", "type": "heartbeat"},
        {"sessionId": 12345, "type": "heartbeat"},
        {"sessionId": "SESSION_ID", "type": "click"},
        {"sessionId": "SESSION_ID", "type": "section_view"},
        {"sessionId": "SESSION_ID", "type": "section_view", "section": "About Me!"},
        {"sessionId": "SESSION_ID", "type": "section_view", "section": "x" * 41},
    ],
    ids=[
        "no-body",
        "not-json",
        "not-an-object",
        "missing-session",
        "bad-session",
        "session-not-a-string",
        "unknown-type",
        "missing-section",
        "bad-section",
        "section-too-long",
    ],
)
def test_bad_requests_return_400_and_store_nothing(events_handler, table, session_id, payload):
    if isinstance(payload, dict) and payload.get("sessionId") == "SESSION_ID":
        payload = {**payload, "sessionId": session_id}

    response, body = call(events_handler, payload)

    assert response["statusCode"] == 400
    assert "error" in body
    assert stored_events(table, session_id) == []


def test_cold_start_only_on_first_call(events_handler, session_id):
    _, first = call(events_handler, {"sessionId": session_id, "type": "heartbeat"})
    _, second = call(events_handler, {"sessionId": session_id, "type": "heartbeat"})

    assert first["coldStart"] is True
    assert second["coldStart"] is False
