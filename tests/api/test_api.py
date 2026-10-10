from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.app import app, current_user, get_accounts, get_scan_queue, get_store
from scanner.accounts import AccountStore, tenant_key
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


# --- Routes for signed-in users --------------------------------------------

AWS_ACCOUNT = "111111111111"


@pytest.fixture
def signed_in(
    table: Any, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, list[dict[str, str]], dict[str, str]]]:
    """A client signed in as user-1, the scan requests it sent, and a switch
    to become another user."""
    monkeypatch.setenv("ROLE_TEMPLATE_URL", "https://example-bucket.s3.amazonaws.com/role.yaml")
    monkeypatch.setenv("SCANNER_ROLE_ARN", "arn:aws:iam::000000000000:role/pillarscan-scanner")
    sent: list[dict[str, str]] = []
    who = {"user": "user-1"}
    app.dependency_overrides[get_store] = lambda: ScanStore(table)
    app.dependency_overrides[get_accounts] = lambda: AccountStore(table)
    app.dependency_overrides[get_scan_queue] = lambda: sent.append
    app.dependency_overrides[current_user] = lambda: who["user"]
    yield TestClient(app), sent, who
    app.dependency_overrides.clear()


def test_private_routes_refuse_requests_without_a_verified_token(table: Any) -> None:
    app.dependency_overrides[get_accounts] = lambda: AccountStore(table)
    try:
        response = TestClient(app).get("/me/accounts")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_connecting_an_account_returns_a_launch_link(
    signed_in: tuple[TestClient, list[dict[str, str]], dict[str, str]],
) -> None:
    client, _, _ = signed_in

    response = client.post("/me/accounts", json={"aws_account_id": AWS_ACCOUNT})

    assert response.status_code == 201
    account = response.json()
    assert account["status"] == "pending"
    assert "external_id" not in account
    link = account["launch_url"]
    assert "stacks/quickcreate" in link
    assert "param_ExternalId=" in link
    assert "param_ScannerPrincipalArn=arn%3Aaws%3Aiam%3A%3A000000000000%3Arole%2Fpillarscan-scanner" in link
    assert client.get("/me/accounts").json()["accounts"][0]["aws_account_id"] == AWS_ACCOUNT


def test_account_ids_are_validated(
    signed_in: tuple[TestClient, list[dict[str, str]], dict[str, str]],
) -> None:
    client, _, _ = signed_in

    assert client.post("/me/accounts", json={"aws_account_id": "12345"}).status_code == 422
    assert client.post("/me/accounts", json={"aws_account_id": "abc"}).status_code == 422
    assert client.post("/me/accounts/not-an-id/scans").status_code == 422


def test_requesting_a_scan_queues_it_once(
    signed_in: tuple[TestClient, list[dict[str, str]], dict[str, str]],
) -> None:
    client, sent, _ = signed_in
    client.post("/me/accounts", json={"aws_account_id": AWS_ACCOUNT})

    first = client.post(f"/me/accounts/{AWS_ACCOUNT}/scans")
    second = client.post(f"/me/accounts/{AWS_ACCOUNT}/scans")

    assert first.status_code == 202
    assert second.status_code == 429
    assert sent == [{"user_id": "user-1", "aws_account_id": AWS_ACCOUNT}]


def test_a_user_cannot_touch_an_account_they_did_not_connect(
    signed_in: tuple[TestClient, list[dict[str, str]], dict[str, str]], table: Any
) -> None:
    client, sent, who = signed_in
    client.post("/me/accounts", json={"aws_account_id": AWS_ACCOUNT})
    ScanStore(table).put_scan(
        make_report("2026-10-09T06:00:00Z", [("fail", "high")]),
        owner=tenant_key("user-1", AWS_ACCOUNT),
    )
    assert len(client.get(f"/me/accounts/{AWS_ACCOUNT}/scans").json()["scans"]) == 1

    who["user"] = "user-2"

    assert client.get("/me/accounts").json() == {"accounts": []}
    assert client.get(f"/me/accounts/{AWS_ACCOUNT}/scans").status_code == 404
    assert client.get(f"/me/accounts/{AWS_ACCOUNT}/scans/latest").status_code == 404
    assert client.post(f"/me/accounts/{AWS_ACCOUNT}/scans").status_code == 404
    assert sent == []


def test_a_users_scans_are_not_in_the_public_list(
    signed_in: tuple[TestClient, list[dict[str, str]], dict[str, str]], table: Any
) -> None:
    client, _, _ = signed_in
    client.post("/me/accounts", json={"aws_account_id": AWS_ACCOUNT})
    ScanStore(table).put_scan(
        make_report("2026-10-09T06:00:00Z", [("fail", "high")]),
        owner=tenant_key("user-1", AWS_ACCOUNT),
    )

    assert client.get("/scans").json() == {"scans": []}
    scan = client.get(f"/me/accounts/{AWS_ACCOUNT}/scans/latest").json()
    assert scan["scan"]["scan_id"] == "20261009T060000Z"


def test_disconnecting_removes_the_account_and_its_scans(
    signed_in: tuple[TestClient, list[dict[str, str]], dict[str, str]], table: Any
) -> None:
    client, _, _ = signed_in
    client.post("/me/accounts", json={"aws_account_id": AWS_ACCOUNT})
    store = ScanStore(table)
    for day in ("08", "09"):
        store.put_scan(
            make_report(f"2026-10-{day}T06:00:00Z", [("fail", "high"), ("pass", "low")]),
            owner=tenant_key("user-1", AWS_ACCOUNT),
        )
    # A public scan, which must survive.
    store.put_scan(make_report("2026-10-09T07:00:00Z", [("pass", "low")]))

    response = client.delete(f"/me/accounts/{AWS_ACCOUNT}")

    assert response.status_code == 200
    body = response.json()
    assert body["scans_deleted"] == 2
    assert body["stack_name"].startswith("pillarscan-audit-role-")
    assert client.get("/me/accounts").json() == {"accounts": []}
    assert store.list_scans(tenant_key("user-1", AWS_ACCOUNT)) == []
    # Only the public scan's two items are left in the table.
    assert len(table.scan()["Items"]) == 2
    assert len(client.get("/scans").json()["scans"]) == 1


def test_connecting_again_after_disconnecting_starts_fresh(
    signed_in: tuple[TestClient, list[dict[str, str]], dict[str, str]],
) -> None:
    client, _, _ = signed_in
    first = client.post("/me/accounts", json={"aws_account_id": AWS_ACCOUNT}).json()
    client.delete(f"/me/accounts/{AWS_ACCOUNT}")

    second = client.post("/me/accounts", json={"aws_account_id": AWS_ACCOUNT}).json()

    # A new role name and external ID, so the old role is no use to anyone.
    assert second["role_arn"] != first["role_arn"]
    assert second["launch_url"] != first["launch_url"]
    assert second["status"] == "pending"


def test_a_user_cannot_disconnect_someone_elses_account(
    signed_in: tuple[TestClient, list[dict[str, str]], dict[str, str]],
) -> None:
    client, _, who = signed_in
    client.post("/me/accounts", json={"aws_account_id": AWS_ACCOUNT})

    who["user"] = "user-2"
    assert client.delete(f"/me/accounts/{AWS_ACCOUNT}").status_code == 404

    who["user"] = "user-1"
    assert len(client.get("/me/accounts").json()["accounts"]) == 1
