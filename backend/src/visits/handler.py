import json
import os
import time
import uuid
from datetime import datetime, timezone

import boto3

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60 


_is_cold_start = True


def _count_visitor():
    """Add one to the all-time visitor count and return the new total.

    ADD is atomic, so two visitors arriving at once can't overwrite each other's increment.
    The counter item has no expires_at, so it outlives the 30-day visit records.
    """
    result = TABLE.update_item(
        Key={"pk": "STATS", "sk": "VISITORS"},
        UpdateExpression="ADD #total :one",
        ExpressionAttributeNames={"#total": "total"},
        ExpressionAttributeValues={":one": 1},
        ReturnValues="UPDATED_NEW",
    )
    return int(result["Attributes"]["total"])


def lambda_handler(event, context):
    global _is_cold_start
    started = time.perf_counter()
    cold_start = _is_cold_start
    _is_cold_start = False

    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    country = headers.get("cloudfront-viewer-country")
    region = headers.get("cloudfront-viewer-country-region-name")
    is_mobile = headers.get("cloudfront-is-mobile-viewer") == "true"

    session_id = str(uuid.uuid4())
    item = {
        "pk": f"SESSION#{session_id}",
        "sk": "META",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "country": country,
        "region": region,
        "is_mobile": is_mobile,
        "expires_at": int(time.time()) + SESSION_TTL_SECONDS,
    }
    TABLE.put_item(Item={k: v for k, v in item.items() if v is not None})
    visitor_number = _count_visitor()

    body = {
        "sessionId": session_id,
        "visitorNumber": visitor_number,
        "coldStart": cold_start,
        "location": {"country": country, "region": region},
        "isMobile": is_mobile,
        "handlerMs": round((time.perf_counter() - started) * 1000, 1),
    }
    return {
        "statusCode": 201,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }