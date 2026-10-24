"""GET /api/deals and GET /api/stores: filters, sorting, pagination, validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Deal

_ids = count(1)
NOW = datetime.now(UTC)


def make_deal(**overrides: Any) -> Deal:
    n = next(_ids)
    values: dict[str, Any] = {
        "source": "steam",
        "source_deal_id": f"deal-{n}",
        "store": "Steam",
        "title": f"Game {n}",
        "platform": "pc",
        "original_price": 19.99,
        "currency": "EUR",
        "url": f"https://example.com/deal/{n}",
        "image_url": None,
        "starts_at": NOW - timedelta(days=1),
        "ends_at": NOW + timedelta(days=3),
        "first_seen_at": NOW - timedelta(hours=n),
        "last_seen_at": NOW,
        "expired": False,
    }
    values.update(overrides)
    return Deal(**values)


def add(session: Session, *deals: Deal) -> None:
    session.add_all(deals)
    session.commit()


def titles(response: Any) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["title"] for item in response.json()["items"]]


def assert_error_422(response: Any) -> None:
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["error"]["message"], str)


@pytest.fixture
def catalog(db_session: Session) -> None:
    add(
        db_session,
        make_deal(
            title="Alpha Quest",
            store="Steam",
            platform="pc",
            original_price=10.0,
            ends_at=NOW + timedelta(days=2),
            first_seen_at=NOW - timedelta(days=3),
        ),
        make_deal(
            title="beta Racer",
            store="Epic Games Store",
            source="epic",
            platform="pc",
            original_price=30.0,
            ends_at=None,
            first_seen_at=NOW - timedelta(days=1),
        ),
        make_deal(
            title="Gamma Saga",
            store="PlayStation Store",
            source="playstation",
            platform="ps5",
            original_price=59.99,
            ends_at=NOW + timedelta(days=1),
            first_seen_at=NOW - timedelta(days=2),
        ),
        make_deal(
            title="Delta 100% Edition",
            store="GOG",
            source="gog",
            platform="pc",
            original_price=5.0,
            ends_at=NOW + timedelta(days=5),
            first_seen_at=NOW - timedelta(hours=1),
        ),
        # Never listed: expired, past end date, price 0, foreign platform.
        make_deal(title="Expired Game", expired=True, expired_at=NOW),
        make_deal(title="Ended Game", ends_at=NOW - timedelta(hours=1)),
        make_deal(title="Free To Play", original_price=0.0),
        make_deal(title="Xbox Game", platform="xbox"),
    )


def test_lists_only_current_paid_pc_ps5_deals(client: TestClient, catalog: None) -> None:
    response = client.get("/api/deals")
    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 4
    assert body["limit"] == 20 and body["offset"] == 0
    assert set(titles(response)) == {
        "Alpha Quest",
        "beta Racer",
        "Gamma Saga",
        "Delta 100% Edition",
    }
    for item in body["items"]:
        assert item["original_price"] > 0
        assert item["platform"] in {"pc", "ps5"}
        assert set(item) == {
            "id",
            "title",
            "store",
            "platform",
            "original_price",
            "currency",
            "url",
            "image_url",
            "starts_at",
            "ends_at",
            "first_seen_at",
            "last_seen_at",
        }


def test_default_sort_is_first_seen_desc(client: TestClient, catalog: None) -> None:
    assert titles(client.get("/api/deals")) == [
        "Delta 100% Edition",
        "beta Racer",
        "Gamma Saga",
        "Alpha Quest",
    ]


def test_platform_filter_with_title_sort(client: TestClient, catalog: None) -> None:
    response = client.get("/api/deals", params={"platform": "pc", "sort": "title", "order": "asc"})
    assert titles(response) == ["Alpha Quest", "beta Racer", "Delta 100% Edition"]
    assert response.json()["total"] == 3
    assert titles(client.get("/api/deals", params={"platform": "ps5"})) == ["Gamma Saga"]


def test_title_sort_desc(client: TestClient, catalog: None) -> None:
    response = client.get("/api/deals", params={"sort": "title", "order": "desc"})
    assert titles(response) == ["Gamma Saga", "Delta 100% Edition", "beta Racer", "Alpha Quest"]


def test_query_is_case_insensitive_substring(client: TestClient, catalog: None) -> None:
    assert titles(client.get("/api/deals", params={"q": "BETA"})) == ["beta Racer"]
    assert titles(client.get("/api/deals", params={"q": "saga"})) == ["Gamma Saga"]


def test_query_like_wildcards_match_literally(client: TestClient, catalog: None) -> None:
    assert titles(client.get("/api/deals", params={"q": "100%"})) == ["Delta 100% Edition"]
    assert titles(client.get("/api/deals", params={"q": "%"})) == ["Delta 100% Edition"]
    assert titles(client.get("/api/deals", params={"q": "_"})) == []


def test_sql_injection_looking_query_is_harmless(
    client: TestClient, catalog: None, db_session: Session
) -> None:
    for q in ("' OR '1'='1", "'; DROP TABLE deals; --", '" OR 1=1 --'):
        response = client.get("/api/deals", params={"q": q})
        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}
    assert client.get("/api/deals").json()["total"] == 4


def test_store_filter_is_exact(client: TestClient, catalog: None) -> None:
    assert titles(client.get("/api/deals", params={"store": "GOG"})) == ["Delta 100% Edition"]
    assert titles(client.get("/api/deals", params={"store": "gog"})) == []
    assert titles(client.get("/api/deals", params={"store": "Store"})) == []


def test_price_range_is_inclusive(client: TestClient, catalog: None) -> None:
    response = client.get(
        "/api/deals",
        params={"min_price": "10", "max_price": "30", "sort": "original_price", "order": "asc"},
    )
    assert titles(response) == ["Alpha Quest", "beta Racer"]
    assert titles(client.get("/api/deals", params={"min_price": "59.99"})) == ["Gamma Saga"]
    response = client.get("/api/deals", params={"max_price": "5", "sort": "title"})
    assert titles(response) == ["Delta 100% Edition"]


def test_sort_by_price_both_directions(client: TestClient, catalog: None) -> None:
    asc = titles(client.get("/api/deals", params={"sort": "original_price", "order": "asc"}))
    assert asc == ["Delta 100% Edition", "Alpha Quest", "beta Racer", "Gamma Saga"]
    desc = titles(client.get("/api/deals", params={"sort": "original_price", "order": "desc"}))
    assert desc == list(reversed(asc))


def test_sort_by_ends_at_puts_nulls_last(client: TestClient, catalog: None) -> None:
    asc = titles(client.get("/api/deals", params={"sort": "ends_at", "order": "asc"}))
    assert asc == ["Gamma Saga", "Alpha Quest", "Delta 100% Edition", "beta Racer"]
    desc = titles(client.get("/api/deals", params={"sort": "ends_at", "order": "desc"}))
    assert desc == ["Delta 100% Edition", "Alpha Quest", "Gamma Saga", "beta Racer"]


def test_sort_by_first_seen_asc(client: TestClient, catalog: None) -> None:
    asc = titles(client.get("/api/deals", params={"sort": "first_seen", "order": "asc"}))
    assert asc == ["Alpha Quest", "Gamma Saga", "beta Racer", "Delta 100% Edition"]


def test_pagination_and_total(client: TestClient, db_session: Session) -> None:
    add(db_session, *[make_deal(title=f"Paged {i:02d}") for i in range(25)])
    first = client.get("/api/deals", params={"sort": "title", "order": "asc"}).json()
    assert first["total"] == 25 and len(first["items"]) == 20
    page = client.get(
        "/api/deals", params={"sort": "title", "order": "asc", "limit": 10, "offset": 20}
    ).json()
    assert page["total"] == 25
    assert page["limit"] == 10 and page["offset"] == 20
    assert [item["title"] for item in page["items"]] == [f"Paged {i:02d}" for i in range(20, 25)]
    beyond = client.get("/api/deals", params={"offset": 100}).json()
    assert beyond["items"] == [] and beyond["total"] == 25
    assert len(client.get("/api/deals", params={"limit": 100}).json()["items"]) == 25


@pytest.mark.parametrize(
    "params",
    [
        {"limit": "101"},
        {"limit": "1000"},
        {"limit": "0"},
        {"limit": "abc"},
        {"offset": "-1"},
        {"platform": "xbox"},
        {"platform": ""},
        {"sort": "price; DROP TABLE deals"},
        {"sort": "id"},
        {"order": "up"},
        {"min_price": "cheap"},
        {"max_price": "nan"},
        {"min_price": "-1"},
        {"min_price": "20", "max_price": "10"},
    ],
)
def test_invalid_values_answer_422_error_body(
    client: TestClient, catalog: None, params: dict[str, str]
) -> None:
    assert_error_422(client.get("/api/deals", params=params))


def test_limit_1000_with_platform_filter_is_rejected(client: TestClient, catalog: None) -> None:
    response = client.get(
        "/api/deals", params={"platform": "pc", "sort": "title", "order": "asc", "limit": 1000}
    )
    assert_error_422(response)
    assert response.json()["error"]["details"]


def test_empty_database_lists_nothing(client: TestClient) -> None:
    assert client.get("/api/deals").json() == {"items": [], "total": 0, "limit": 20, "offset": 0}
    assert client.get("/api/stores").json() == {"items": []}


def test_stores_are_distinct_sorted_and_current_only(
    client: TestClient, catalog: None, db_session: Session
) -> None:
    add(
        db_session,
        make_deal(title="Another Steam Game", store="Steam"),
        make_deal(title="Gone", store="Old Store", expired=True),
        make_deal(title="Zero", store="Zero Store", original_price=0.0),
    )
    response = client.get("/api/stores")
    assert response.status_code == 200
    assert response.json() == {"items": ["Epic Games Store", "GOG", "PlayStation Store", "Steam"]}
