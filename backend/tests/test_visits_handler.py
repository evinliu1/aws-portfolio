import json
import time

SESSION_TTL_SECONDS = 30 * 24 * 60 * 60


def make_event(headers=None):
    return {"httpMethod": "POST", "path": "/api/visits", "headers": headers}


def call(visits_handler, headers=None):
    response = visits_handler.lambda_handler(make_event(headers), None)
    return response, json.loads(response["body"])


def test_returns_201_json(visits_handler):
    response, body = call(visits_handler)

    assert response["statusCode"] == 201
    assert response["headers"]["Content-Type"] == "application/json"
    assert set(body) == {
        "sessionId",
        "visitorNumber",
        "coldStart",
        "location",
        "isMobile",
        "handlerMs",
    }


def test_writes_session_item_to_table(visits_handler, table):
    _, body = call(visits_handler)

    item = table.get_item(Key={"pk": f"SESSION#{body['sessionId']}", "sk": "META"})["Item"]
    assert "created_at" in item


def test_reads_cloudfront_headers_case_insensitively(visits_handler, table):
    _, body = call(
        visits_handler,
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


def test_missing_headers_are_not_stored(visits_handler, table):
    _, body = call(visits_handler, headers=None)

    assert body["location"] == {"country": None, "region": None}
    assert body["isMobile"] is False
    item = table.get_item(Key={"pk": f"SESSION#{body['sessionId']}", "sk": "META"})["Item"]
    assert "country" not in item
    assert "region" not in item


def test_sets_ttl_about_30_days_out(visits_handler, table):
    before = int(time.time())
    _, body = call(visits_handler)
    after = int(time.time())

    item = table.get_item(Key={"pk": f"SESSION#{body['sessionId']}", "sk": "META"})["Item"]
    assert before + SESSION_TTL_SECONDS <= item["expires_at"] <= after + SESSION_TTL_SECONDS


def test_cold_start_only_on_first_call(visits_handler):
    _, first = call(visits_handler)
    _, second = call(visits_handler)

    assert first["coldStart"] is True
    assert second["coldStart"] is False


def test_each_visit_gets_a_new_session_id(visits_handler):
    _, first = call(visits_handler)
    _, second = call(visits_handler)

    assert first["sessionId"] != second["sessionId"]


def test_visitors_are_numbered_in_order(visits_handler):
    numbers = [call(visits_handler)[1]["visitorNumber"] for _ in range(3)]

    assert numbers == [1, 2, 3]


def test_visitor_counter_never_expires(visits_handler, table):
    call(visits_handler)

    counter = table.get_item(Key={"pk": "STATS", "sk": "VISITORS"})["Item"]
    assert counter["total"] == 1
    assert "expires_at" not in counter
