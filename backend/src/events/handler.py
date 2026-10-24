import json
import os
import re
import time
import uuid
from datetime import datetime, timezone

import boto3

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
EVENT_TYPES = {"heartbeat", "section_view"}
SECTION_PATTERN = re.compile(r"^[a-z0-9-]{1,40}$")

_is_cold_start = True


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_request(event):
    """Return (session_id, event_type, section), or raise ValueError explaining what's wrong."""
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

    section = None
    if event_type == "section_view":
        section = payload.get("section")
        if not isinstance(section, str) or not SECTION_PATTERN.match(section):
            raise ValueError("section must be a short lowercase id like 'skills'.")

    return session_id, event_type, section


def lambda_handler(event, context):
    global _is_cold_start
    started = time.perf_counter()
    cold_start = _is_cold_start
    _is_cold_start = False

    try:
        session_id, event_type, section = _parse_request(event)
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
    item = {
        "pk": pk,
        # The random suffix keeps two events in the same millisecond from overwriting each other.
        "sk": f"EVENT#{now}#{uuid.uuid4().hex[:8]}",
        "type": event_type,
        "section": section,
        "created_at": now,
        # Events share their session's expiry so they disappear together.
        "expires_at": session["expires_at"],
    }
    TABLE.put_item(Item={k: v for k, v in item.items() if v is not None})

    return _response(
        201,
        {
            "type": event_type,
            "coldStart": cold_start,
            "handlerMs": round((time.perf_counter() - started) * 1000, 1),
        },
    )
