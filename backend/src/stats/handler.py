import json
import os
import time

import boto3
from boto3.dynamodb.conditions import Key

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

_is_cold_start = True


def lambda_handler(event, context):
    global _is_cold_start
    started = time.perf_counter()
    cold_start = _is_cold_start
    _is_cold_start = False

    # Every counter shares the "STATS" partition, so one query reads them all.
    items = TABLE.query(KeyConditionExpression=Key("pk").eq("STATS"))["Items"]

    visitors = 0
    clicks = []
    for item in items:
        if item["sk"] == "VISITORS":
            visitors = int(item["total"])
        elif item["sk"].startswith("CLICK#"):
            clicks.append({"target": item["sk"].removeprefix("CLICK#"), "count": int(item["total"])})
    clicks.sort(key=lambda click: (-click["count"], click["target"]))

    body = {
        "visitors": visitors,
        "clicks": clicks,
        "coldStart": cold_start,
        "handlerMs": round((time.perf_counter() - started) * 1000, 1),
    }
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
