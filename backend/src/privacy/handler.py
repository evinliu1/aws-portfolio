import json
import os
import time
import uuid
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

_is_cold_start = True


def _to_json(value):
    """DynamoDB hands numbers back as Decimal; every number stored here is a whole number."""
    if isinstance(value, Decimal):
        return int(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=_to_json),
    }


def _parse_session_id(event):
    """Return the sessionId from the URL path, or raise ValueError if it isn't a UUID."""
    try:
        return str(uuid.UUID((event.get("pathParameters") or {}).get("sessionId")))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("sessionId must be a UUID.")


def _session_items(pk):
    """Every row stored under one visit, following pagination in case there are many."""
    query = {"KeyConditionExpression": Key("pk").eq(pk), "ConsistentRead": True}
    items = []
    while True:
        page = TABLE.query(**query)
        items.extend(page["Items"])
        if "LastEvaluatedKey" not in page:
            return items
        query["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _delete_session(pk, items):
    # The visit row goes first: the events and resume functions refuse to write to a visit
    # without one. A request already in flight could still add a row, but it carries the
    # visit's expiry, so DynamoDB removes it on schedule anyway.
    TABLE.delete_item(Key={"pk": pk, "sk": "META"})
    with TABLE.batch_writer() as batch:
        for item in items:
            if item["sk"] != "META":
                batch.delete_item(Key={"pk": pk, "sk": item["sk"]})


def lambda_handler(event, context):
    global _is_cold_start
    started = time.perf_counter()
    cold_start = _is_cold_start
    _is_cold_start = False

    method = event.get("httpMethod")
    if method not in {"GET", "DELETE"}:
        return _response(405, {"error": "Use GET or DELETE."})

    try:
        session_id = _parse_session_id(event)
    except ValueError as error:
        return _response(400, {"error": str(error)})

    pk = f"SESSION#{session_id}"
    items = _session_items(pk)
    if not items:
        return _response(404, {"error": "Unknown session."})

    if method == "GET":
        body = {"sessionId": session_id, "items": items}
    else:
        _delete_session(pk, items)
        body = {"sessionId": session_id, "deleted": len(items)}

    body.update(
        coldStart=cold_start,
        handlerMs=round((time.perf_counter() - started) * 1000, 1),
    )
    return _response(200, body)
