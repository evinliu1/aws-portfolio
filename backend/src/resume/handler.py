import json
import os
import time
import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
S3 = boto3.client("s3", config=Config(signature_version="s3v4"))
SNS = boto3.client("sns")
RESUME_BUCKET = os.environ["RESUME_BUCKET"]
TOPIC_ARN = os.environ["TOPIC_ARN"]
RESUME_KEY = "resume.pdf"
DOWNLOAD_NAME = "Evin Liu Resume.pdf"
LINK_EXPIRES_SECONDS = 5 * 60

_is_cold_start = True


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_session_id(event):
    """Return the optional sessionId from the body, or raise ValueError if it's malformed."""
    if not event.get("body"):
        return None
    try:
        payload = json.loads(event["body"])
    except json.JSONDecodeError:
        raise ValueError("Body must be JSON.")
    if not isinstance(payload, dict):
        raise ValueError("Body must be a JSON object.")
    if payload.get("sessionId") is None:
        return None
    try:
        return str(uuid.UUID(payload["sessionId"]))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("sessionId must be a UUID.")


def _mark_first_download(session_id):
    """Record the download on the visit. True only for a known session's first download."""
    try:
        TABLE.update_item(
            Key={"pk": f"SESSION#{session_id}", "sk": "META"},
            UpdateExpression="SET resume_downloaded_at = :now",
            ConditionExpression="attribute_exists(pk) AND attribute_not_exists(resume_downloaded_at)",
            ExpressionAttributeValues={":now": datetime.now(timezone.utc).isoformat()},
        )
        return True
    except TABLE.meta.client.exceptions.ConditionalCheckFailedException:
        return False  # Unknown session, or this visitor already downloaded it.


def _notify(headers):
    place = ", ".join(
        part
        for part in (
            headers.get("cloudfront-viewer-country-region-name"),
            headers.get("cloudfront-viewer-country"),
        )
        if part
    )
    who = f"Someone in {place}" if place else "Someone"
    try:
        SNS.publish(
            TopicArn=TOPIC_ARN,
            Subject="Your resume was downloaded",
            Message=f"{who} just downloaded your resume from your portfolio site.",
        )
        return True
    except (BotoCoreError, ClientError) as error:
        # The visitor still gets the resume; a missed notification only shows up in the logs.
        print(f"Could not publish download notification: {error}")
        return False


def lambda_handler(event, context):
    global _is_cold_start
    started = time.perf_counter()
    cold_start = _is_cold_start
    _is_cold_start = False

    try:
        session_id = _parse_session_id(event)
    except ValueError as error:
        return _response(400, {"error": str(error)})

    url = S3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": RESUME_BUCKET,
            "Key": RESUME_KEY,
            "ResponseContentDisposition": f'attachment; filename="{DOWNLOAD_NAME}"',
        },
        ExpiresIn=LINK_EXPIRES_SECONDS,
    )

    first_download = bool(session_id) and _mark_first_download(session_id)
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    notified = first_download and _notify(headers)

    return _response(
        200,
        {
            "url": url,
            "expiresInSeconds": LINK_EXPIRES_SECONDS,
            "firstDownload": first_download,
            "notified": notified,
            "coldStart": cold_start,
            "handlerMs": round((time.perf_counter() - started) * 1000, 1),
        },
    )
