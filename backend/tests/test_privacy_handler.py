import json
import uuid

import pytest
from boto3.dynamodb.conditions import Key

SESSION_EXPIRES_AT = 1_900_000_000


def add_visit(table, session_id):
    """A visit with one of each kind of row the other functions write."""
    pk = f"SESSION#{session_id}"
    table.put_item(
        Item={
            "pk": pk,
            "sk": "META",
            "created_at": "2026-10-24T17:00:00+00:00",
            "country": "US",
            "region": "Georgia",
            "is_mobile": False,
            "expires_at": SESSION_EXPIRES_AT,
        }
    )
    table.put_item(
        Item={
            "pk": pk,
            "sk": "EVENT#2026-10-24T17:00:15.000+00:00#abcd1234",
            "type": "heartbeat",
            "created_at": "2026-10-24T17:00:15.000+00:00",
            "expires_at": SESSION_EXPIRES_AT,
        }
    )
    table.put_item(
        Item={
            "pk": pk,
            "sk": "CLICK#skill-python",
            "type": "click",
            "target": "skill-python",
            "created_at": "2026-10-24T17:00:20.000+00:00",
            "expires_at": SESSION_EXPIRES_AT,
        }
    )


@pytest.fixture
def session_id(table):
    session_id = str(uuid.uuid4())
    add_visit(table, session_id)
    return session_id


def call(privacy_handler, method, session_id):
    event = {
        "httpMethod": method,
        "path": f"/api/sessions/{session_id}",
        "pathParameters": {"sessionId": session_id},
    }
    response = privacy_handler.lambda_handler(event, None)
    return response, json.loads(response["body"])


def rows(table, session_id):
    return table.query(KeyConditionExpression=Key("pk").eq(f"SESSION#{session_id}"))["Items"]


def test_get_returns_200_json(privacy_handler, session_id):
    response, body = call(privacy_handler, "GET", session_id)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"
    assert set(body) == {"sessionId", "items", "coldStart", "handlerMs"}
    assert body["sessionId"] == session_id


def test_get_returns_every_row_of_the_visit(privacy_handler, session_id):
    _, body = call(privacy_handler, "GET", session_id)

    assert [item["sk"] for item in body["items"]] == [
        "CLICK#skill-python",
        "EVENT#2026-10-24T17:00:15.000+00:00#abcd1234",
        "META",
    ]
    meta = body["items"][-1]
    assert meta["region"] == "Georgia"
    assert meta["expires_at"] == SESSION_EXPIRES_AT  # a plain number, not a Decimal string


def test_get_leaves_out_other_visits_and_counters(privacy_handler, table, session_id):
    add_visit(table, str(uuid.uuid4()))
    table.put_item(Item={"pk": "STATS", "sk": "VISITORS", "total": 2})

    _, body = call(privacy_handler, "GET", session_id)

    assert {item["pk"] for item in body["items"]} == {f"SESSION#{session_id}"}


def test_delete_removes_every_row_of_the_visit(privacy_handler, table, session_id):
    response, body = call(privacy_handler, "DELETE", session_id)

    assert response["statusCode"] == 200
    assert body["deleted"] == 3
    assert rows(table, session_id) == []


def test_delete_keeps_other_visits_and_counters(privacy_handler, table, session_id):
    other = str(uuid.uuid4())
    add_visit(table, other)
    table.put_item(Item={"pk": "STATS", "sk": "VISITORS", "total": 2})

    call(privacy_handler, "DELETE", session_id)

    assert len(rows(table, other)) == 3
    assert table.get_item(Key={"pk": "STATS", "sk": "VISITORS"})["Item"]["total"] == 2


def test_deleted_visit_is_gone_for_good(privacy_handler, session_id):
    call(privacy_handler, "DELETE", session_id)

    get_response, _ = call(privacy_handler, "GET", session_id)
    delete_response, _ = call(privacy_handler, "DELETE", session_id)

    assert get_response["statusCode"] == 404
    assert delete_response["statusCode"] == 404


def test_deleted_visit_accepts_no_new_events(privacy_handler, events_handler, session_id):
    call(privacy_handler, "DELETE", session_id)

    event = {"body": json.dumps({"sessionId": session_id, "type": "heartbeat"})}
    response = events_handler.lambda_handler(event, None)

    assert response["statusCode"] == 404


@pytest.mark.parametrize("method", ["GET", "DELETE"])
def test_unknown_session_is_404(privacy_handler, table, method):
    response, body = call(privacy_handler, method, str(uuid.uuid4()))

    assert response["statusCode"] == 404
    assert body == {"error": "Unknown session."}


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "", None])
def test_bad_session_id_is_400(privacy_handler, bad_id):
    response, body = call(privacy_handler, "GET", bad_id)

    assert response["statusCode"] == 400
    assert body == {"error": "sessionId must be a UUID."}


def test_missing_path_parameters_is_400(privacy_handler):
    response = privacy_handler.lambda_handler({"httpMethod": "GET", "pathParameters": None}, None)

    assert response["statusCode"] == 400


def test_other_methods_are_405(privacy_handler, session_id, table):
    response, _ = call(privacy_handler, "POST", session_id)

    assert response["statusCode"] == 405
    assert len(rows(table, session_id)) == 3


def test_cold_start_only_on_first_call(privacy_handler, session_id):
    _, first = call(privacy_handler, "GET", session_id)
    _, second = call(privacy_handler, "GET", session_id)

    assert first["coldStart"] is True
    assert second["coldStart"] is False
