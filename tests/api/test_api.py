from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.app import app, get_store
from scanner.store import ScanStore

from ..conftest import make_report


@pytest.fixture
def client(table: Any) -> Iterator[TestClient]:
    store = ScanStore(table)
    store.put_scan(make_report("2026-10-08T06:00:00Z", [("pass", "low")]))
    store.put_scan(make_report("2026-10-09T06:00:00Z", [("fail", "high"), ("pass", "low")]))
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_lists_scans_newest_first(client: TestClient) -> None:
    scans = client.get("/scans").json()["scans"]

    assert [scan["scan_id"] for scan in scans] == ["20261009T060000Z", "20261008T060000Z"]
    assert scans[0]["failed"] == 1
    assert scans[0]["score"] == 14


def test_limit_is_respected_and_validated(client: TestClient) -> None:
    assert len(client.get("/scans", params={"limit": 1}).json()["scans"]) == 1
    assert client.get("/scans", params={"limit": 0}).status_code == 422
    assert client.get("/scans", params={"limit": 1000}).status_code == 422


def test_returns_one_scan_with_its_findings(client: TestClient) -> None:
    scan = client.get("/scans/20261008T060000Z").json()

    assert scan["scan"]["started_at"] == "2026-10-08T06:00:00Z"
    assert [finding["status"] for finding in scan["findings"]] == ["pass"]


def test_latest_returns_the_newest_scan(client: TestClient) -> None:
    scan = client.get("/scans/latest").json()

    assert scan["scan"]["scan_id"] == "20261009T060000Z"
    assert len(scan["findings"]) == 2


def test_unknown_scan_is_a_404(client: TestClient) -> None:
    response = client.get("/scans/20200101T000000Z")

    assert response.status_code == 404
    assert response.json() == {"detail": "No such scan."}


def test_there_is_no_way_to_write(client: TestClient) -> None:
    assert client.post("/scans").status_code == 405
    assert client.delete("/scans/20261008T060000Z").status_code == 405
