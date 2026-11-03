import pytest


def add_securities(client):
    for ticker, name, shares in [("AAA", "Alpha Corp", 100), ("BBB", "Beta Ltd", 200)]:
        response = client.post(
            "/securities", json={"ticker": ticker, "name": name, "shares_outstanding": shares}
        )
        assert response.status_code == 201


def add_prices(client, rows):
    payload = {"prices": [{"ticker": t, "price_date": d, "close": c} for t, d, c in rows]}
    return client.post("/prices", json=payload)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_list_securities(client):
    add_securities(client)
    body = client.get("/securities").json()
    assert [s["ticker"] for s in body] == ["AAA", "BBB"]


def test_ticker_is_normalised_to_uppercase(client):
    response = client.post(
        "/securities", json={"ticker": " aaa ", "name": "Alpha", "shares_outstanding": 10}
    )
    assert response.json()["ticker"] == "AAA"


def test_duplicate_security_returns_409(client):
    add_securities(client)
    response = client.post(
        "/securities", json={"ticker": "AAA", "name": "Again", "shares_outstanding": 1}
    )
    assert response.status_code == 409


@pytest.mark.parametrize("shares", [0, -5])
def test_non_positive_shares_rejected(client, shares):
    response = client.post(
        "/securities", json={"ticker": "ZZZ", "name": "Bad", "shares_outstanding": shares}
    )
    assert response.status_code == 422


def test_prices_for_unknown_ticker_return_404(client):
    response = add_prices(client, [("NOPE", "2026-01-01", 10.0)])
    assert response.status_code == 404


def test_non_positive_price_rejected(client):
    add_securities(client)
    response = add_prices(client, [("AAA", "2026-01-01", 0)])
    assert response.status_code == 422


def test_price_upsert_inserts_then_updates(client):
    add_securities(client)
    first = add_prices(client, [("AAA", "2026-01-01", 10.0)])
    assert first.json() == {"inserted": 1, "updated": 0}
    second = add_prices(client, [("AAA", "2026-01-01", 12.0)])
    assert second.json() == {"inserted": 0, "updated": 1}


def test_index_levels_end_to_end(client):
    add_securities(client)
    add_prices(
        client,
        [
            ("AAA", "2026-01-01", 10.0),
            ("BBB", "2026-01-01", 5.0),
            ("AAA", "2026-01-02", 11.0),
            ("BBB", "2026-01-02", 5.5),
        ],
    )
    body = client.get("/index/levels").json()
    assert [row["as_of"] for row in body] == ["2026-01-01", "2026-01-02"]
    assert body[0]["level"] == pytest.approx(1000.0)
    assert body[0]["daily_return"] is None
    assert body[1]["level"] == pytest.approx(1100.0)
    assert body[1]["daily_return"] == pytest.approx(0.10)


def test_index_levels_date_filter_keeps_original_base(client):
    add_securities(client)
    add_prices(
        client,
        [
            ("AAA", "2026-01-01", 10.0),
            ("BBB", "2026-01-01", 5.0),
            ("AAA", "2026-01-02", 11.0),
            ("BBB", "2026-01-02", 5.5),
        ],
    )
    body = client.get("/index/levels", params={"start": "2026-01-02"}).json()
    assert len(body) == 1
    assert body[0]["level"] == pytest.approx(1100.0)


def test_index_levels_with_incomplete_data_returns_422(client):
    add_securities(client)
    add_prices(client, [("AAA", "2026-01-01", 10.0), ("BBB", "2026-01-01", 5.0)])
    add_prices(client, [("AAA", "2026-01-02", 11.0)])  # BBB missing on day 2
    response = client.get("/index/levels")
    assert response.status_code == 422
    assert "missing prices" in response.json()["detail"]


def test_index_levels_without_securities_returns_409(client):
    assert client.get("/index/levels").status_code == 409


def test_invalid_date_range_rejected(client):
    add_securities(client)
    response = client.get("/index/levels", params={"start": "2026-02-01", "end": "2026-01-01"})
    assert response.status_code == 422
