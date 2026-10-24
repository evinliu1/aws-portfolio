import json
import os
import re
import time
import uuid
from datetime import datetime, timezone

import boto3

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
EVENT_TYPES = {"click", "heartbeat", "section_view"}
SECTION_PATTERN = re.compile(r"^[a-z0-9-]{1,40}$")
# Click counts are shown to every visitor, so only these ids are accepted; anything else
# could put arbitrary text on the site. Keep in sync with frontend/src/lib/clickTargets.js.
CLICK_TARGETS = {
    "download-resume",
    "get-in-touch",
    "skill-python",
    "skill-sql",
    "skill-aws-lambda",
    "skill-api-gateway",
    "skill-dynamodb",
    "skill-aws-cdk",
    "skill-pytest",
    "skill-react",
}

_is_cold_start = True


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_request(event):
    """Return (session_id, event_type, details), or raise ValueError explaining what's wrong.

    details holds the type-specific field: {"section": ...} for a section view,
    {"target": ...} for a click, and nothing for a heartbeat.
    """
    try:
        payload = json.loads(event.get("body") or "")
    except json.JSONDecodeError:
        raise ValueError("Body must be JSON.")
    if not isinstance(payload, dict):
        raise ValueError("Body must be a JSON object.")

    try:
        session_id = str(uuid.UUID(payload.get("sessionId")))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("sessionId must be a UUID.")

    event_type = payload.get("type")
    if event_type not in EVENT_TYPES:
        raise ValueError(f"type must be one of: {', '.join(sorted(EVENT_TYPES))}.")

    details = {}
    if event_type == "section_view":
        section = payload.get("section")
        if not isinstance(section, str) or not SECTION_PATTERN.match(section):
            raise ValueError("section must be a short lowercase id like 'skills'.")
        details["section"] = section
    elif event_type == "click":
        target = payload.get("target")
        if not isinstance(target, str) or target not in CLICK_TARGETS:
            raise ValueError("target must be one of the site's tracked elements.")
        details["target"] = target

    return session_id, event_type, details


def _record_click(pk, target, now, expires_at):
    """Count each visitor once per target. Returns (first_click, visitors who have clicked it)."""
    counter_key = {"pk": "STATS", "sk": f"CLICK#{target}"}
    try:
        # One item per visitor per target; the condition makes repeat clicks a no-op.
        TABLE.put_item(
            Item={
                "pk": pk,
                "sk": f"CLICK#{target}",
                "type": "click",
                "target": target,
                "created_at": now,
                "expires_at": expires_at,
            },
            ConditionExpression="attribute_not_exists(pk)",
        )
    except TABLE.meta.client.exceptions.ConditionalCheckFailedException:
        counter = TABLE.get_item(Key=counter_key).get("Item", {})
        return False, int(counter.get("total", 0))

    result = TABLE.update_item(
        Key=counter_key,
        UpdateExpression="ADD #total :one",
        ExpressionAttributeNames={"#total": "total"},
        ExpressionAttributeValues={":one": 1},
        ReturnValues="UPDATED_NEW",
    )
    return True, int(result["Attributes"]["total"])


def lambda_handler(event, context):
    global _is_cold_start
    started = time.perf_counter()
    cold_start = _is_cold_start
    _is_cold_start = False

    try:
        session_id, event_type, details = _parse_request(event)
    except ValueError as error:
        return _response(400, {"error": str(error)})

    pk = f"SESSION#{session_id}"
    session = TABLE.get_item(
        Key={"pk": pk, "sk": "META"},
        ProjectionExpression="expires_at",
        ConsistentRead=True,
    ).get("Item")
    if session is None:
        return _response(404, {"error": "Unknown session."})

    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    # Events share their session's expiry so they disappear together.
    expires_at = session["expires_at"]
    status_code = 201
    body = {"type": event_type}

    if event_type == "click":
        first_click, click_count = _record_click(pk, details["target"], now, expires_at)
        status_code = 201 if first_click else 200
        body.update(firstClick=first_click, clickCount=click_count)
    else:
        TABLE.put_item(
            Item={
                "pk": pk,
                # The random suffix keeps two events in the same millisecond from overwriting each other.
                "sk": f"EVENT#{now}#{uuid.uuid4().hex[:8]}",
                "type": event_type,
                "created_at": now,
                "expires_at": expires_at,
                **details,
            }
        )

    body.update(
        coldStart=cold_start,
        handlerMs=round((time.perf_counter() - started) * 1000, 1),
    )
    return _response(status_code, body)
