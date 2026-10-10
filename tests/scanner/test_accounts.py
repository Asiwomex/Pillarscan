from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from scanner.accounts import (
    MAX_ACCOUNTS_PER_USER,
    AccountStore,
    ScanRequestedTooSoon,
    TooManyAccounts,
    tenant_key,
)
from scanner.findings import format_timestamp

ACCOUNT = "111111111111"


def test_connecting_generates_a_role_name_and_external_id(table: Any) -> None:
    account = AccountStore(table).connect("user-1", ACCOUNT)

    assert account["status"] == "pending"
    assert account["role_arn"].startswith(f"arn:aws:iam::{ACCOUNT}:role/PillarscanAuditRole-")
    assert account["role_arn"].endswith(account["role_name_suffix"])
    assert len(account["external_id"]) >= 32


def test_connecting_twice_keeps_the_first_external_id(table: Any) -> None:
    accounts = AccountStore(table)

    first = accounts.connect("user-1", ACCOUNT)
    second = accounts.connect("user-1", ACCOUNT)

    assert second["external_id"] == first["external_id"]
    assert len(accounts.list("user-1")) == 1


def test_each_user_gets_a_different_external_id_for_the_same_account(table: Any) -> None:
    accounts = AccountStore(table)

    mine = accounts.connect("user-1", ACCOUNT)
    theirs = accounts.connect("user-2", ACCOUNT)

    # Knowing an account ID is not enough to be let into its role.
    assert mine["external_id"] != theirs["external_id"]
    assert mine["role_arn"] != theirs["role_arn"]
    assert tenant_key("user-1", ACCOUNT) != tenant_key("user-2", ACCOUNT)


def test_users_only_see_their_own_accounts(table: Any) -> None:
    accounts = AccountStore(table)
    accounts.connect("user-1", ACCOUNT)

    assert accounts.list("user-2") == []
    assert accounts.get("user-2", ACCOUNT) is None


def test_refuses_more_accounts_than_the_limit(table: Any) -> None:
    accounts = AccountStore(table)
    for index in range(MAX_ACCOUNTS_PER_USER):
        accounts.connect("user-1", f"{index:012d}")

    with pytest.raises(TooManyAccounts):
        accounts.connect("user-1", ACCOUNT)


def test_a_second_scan_request_straight_away_is_refused(table: Any) -> None:
    accounts = AccountStore(table)
    accounts.connect("user-1", ACCOUNT)

    accounts.mark_scan_requested("user-1", ACCOUNT)

    with pytest.raises(ScanRequestedTooSoon):
        accounts.mark_scan_requested("user-1", ACCOUNT)


def test_a_scan_can_be_requested_again_after_the_wait(table: Any) -> None:
    accounts = AccountStore(table)
    accounts.connect("user-1", ACCOUNT)
    earlier = format_timestamp(datetime.now(timezone.utc) - timedelta(minutes=10))
    table.update_item(
        Key={"PK": "USER#user-1", "SK": f"ACCOUNT#{ACCOUNT}"},
        UpdateExpression="SET last_requested_at = :earlier",
        ExpressionAttributeValues={":earlier": earlier},
    )

    accounts.mark_scan_requested("user-1", ACCOUNT)

    account = accounts.get("user-1", ACCOUNT)
    assert account is not None
    assert account["last_requested_at"] > earlier


def test_a_scan_cannot_be_requested_for_an_unconnected_account(table: Any) -> None:
    with pytest.raises(ScanRequestedTooSoon):
        AccountStore(table).mark_scan_requested("user-1", ACCOUNT)

    # The refused request must not have created the account as a side effect.
    assert AccountStore(table).get("user-1", ACCOUNT) is None


def test_a_successful_scan_clears_an_earlier_error(table: Any) -> None:
    accounts = AccountStore(table)
    accounts.connect("user-1", ACCOUNT)
    accounts.record_failure("user-1", ACCOUNT, "Could not assume the role.")

    accounts.record_scan("user-1", ACCOUNT, "20261010T100000Z")

    account = accounts.get("user-1", ACCOUNT)
    assert account is not None
    assert account["status"] == "connected"
    assert "last_error" not in account
