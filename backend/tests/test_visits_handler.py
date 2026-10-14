import json
import time

SESSION_TTL_SECONDS = 30 * 24 * 60 * 60


def make_event(headers=None):
    return {"httpMethod": "POST", "path": "/api/visits", "headers": headers}


def call(handler, headers=None):
    response = handler.lambda_handler(make_event(headers), None)
    return response, json.loads(response["body"])


def test_returns_201_json(handler):
    response, body = call(handler)

    assert response["statusCode"] == 201
    assert response["headers"]["Content-Type"] == "application/json"
    assert set(body) == {"sessionId", "coldStart", "location", "isMobile", "handlerMs"}


def test_writes_session_item_to_table(handler, table):
    _, body = call(handler)

    item = table.get_item(Key={"pk": f"SESSION#{body['sessionId']}", "sk": "META"})["Item"]
    assert "created_at" in item


def test_reads_cloudfront_headers_case_insensitively(handler, table):
    _, body = call(
        handler,
        {
            "CloudFront-Viewer-Country": "US",
            "cloudfront-viewer-country-region-name": "Washington",
            "CLOUDFRONT-IS-MOBILE-VIEWER": "true",
        },
    )

    assert body["location"] == {"country": "US", "region": "Washington"}
    assert body["isMobile"] is True
    item = table.get_item(Key={"pk": f"SESSION#{body['sessionId']}", "sk": "META"})["Item"]
    assert item["country"] == "US"
    assert item["region"] == "Washington"
    assert item["is_mobile"] is True


def test_missing_headers_are_not_stored(handler, table):
    _, body = call(handler, headers=None)

    assert body["location"] == {"country": None, "region": None}
    assert body["isMobile"] is False
    item = table.get_item(Key={"pk": f"SESSION#{body['sessionId']}", "sk": "META"})["Item"]
    assert "country" not in item
    assert "region" not in item


def test_sets_ttl_about_30_days_out(handler, table):
    before = int(time.time())
    _, body = call(handler)
    after = int(time.time())

    item = table.get_item(Key={"pk": f"SESSION#{body['sessionId']}", "sk": "META"})["Item"]
    assert before + SESSION_TTL_SECONDS <= item["expires_at"] <= after + SESSION_TTL_SECONDS


def test_cold_start_only_on_first_call(handler):
    _, first = call(handler)
    _, second = call(handler)

    assert first["coldStart"] is True
    assert second["coldStart"] is False


def test_each_visit_gets_a_new_session_id(handler):
    _, first = call(handler)
    _, second = call(handler)

    assert first["sessionId"] != second["sessionId"]
