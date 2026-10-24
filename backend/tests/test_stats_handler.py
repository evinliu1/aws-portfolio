import json


def call(stats_handler):
    event = {"httpMethod": "GET", "path": "/api/stats"}
    response = stats_handler.lambda_handler(event, None)
    return response, json.loads(response["body"])


def add_counter(table, sk, total):
    table.put_item(Item={"pk": "STATS", "sk": sk, "total": total})


def test_returns_200_json(stats_handler):
    response, body = call(stats_handler)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"
    assert set(body) == {"visitors", "clicks", "coldStart", "handlerMs"}


def test_empty_table_has_zero_stats(stats_handler):
    _, body = call(stats_handler)

    assert body["visitors"] == 0
    assert body["clicks"] == []


def test_reads_visitor_count(stats_handler, table):
    add_counter(table, "VISITORS", 42)

    _, body = call(stats_handler)

    assert body["visitors"] == 42


def test_clicks_are_sorted_most_clicked_first(stats_handler, table):
    add_counter(table, "CLICK#skill-sql", 3)
    add_counter(table, "CLICK#get-in-touch", 9)
    add_counter(table, "CLICK#skill-python", 3)

    _, body = call(stats_handler)

    assert body["clicks"] == [
        {"target": "get-in-touch", "count": 9},
        {"target": "skill-python", "count": 3},
        {"target": "skill-sql", "count": 3},
    ]


def test_ignores_visit_records(stats_handler, table):
    table.put_item(Item={"pk": "SESSION#abc", "sk": "CLICK#skill-python", "target": "skill-python"})

    _, body = call(stats_handler)

    assert body["clicks"] == []


def test_cold_start_only_on_first_call(stats_handler):
    _, first = call(stats_handler)
    _, second = call(stats_handler)

    assert first["coldStart"] is True
    assert second["coldStart"] is False
