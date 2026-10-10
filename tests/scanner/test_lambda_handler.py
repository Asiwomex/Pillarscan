from __future__ import annotations

import json
from typing import Any

import boto3
import pytest
from botocore.exceptions import ClientError

from scanner import lambda_handler
from scanner.accounts import AccountStore, tenant_key
from scanner.store import ScanStore

from .conftest import MOTO_ACCOUNT_ID
from .helpers import REGION

ROLE_ARN = f"arn:aws:iam::{MOTO_ACCOUNT_ID}:role/PillarscanAuditRole"
PARAMETER = "/pillarscan/external-id"
USER = "user-1"


def _request(**body: str) -> dict[str, Any]:
    return {"Records": [{"body": json.dumps(body)}]}


@pytest.fixture
def scanner_environment(monkeypatch: pytest.MonkeyPatch, table: Any) -> None:
    trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{MOTO_ACCOUNT_ID}:root"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    boto3.client("iam", region_name=REGION).create_role(
        RoleName="PillarscanAuditRole", AssumeRolePolicyDocument=json.dumps(trust)
    )
    boto3.client("ssm", region_name=REGION).put_parameter(
        Name=PARAMETER, Value="an-external-id-for-tests", Type="SecureString"
    )
    monkeypatch.setenv("AUDIT_ROLE_ARN", ROLE_ARN)
    monkeypatch.setenv("EXTERNAL_ID_PARAMETER", PARAMETER)
    # Keep the test to one region; a full scan of every moto region is slow.
    monkeypatch.setattr(lambda_handler, "run_scan", _scan_one_region)


def _scan_one_region(session: boto3.Session) -> Any:
    from scanner.engine import run_scan

    return run_scan(session, regions=[REGION])


def test_public_scan_is_stored_scrubbed(scanner_environment: None, table: Any) -> None:
    result = lambda_handler.handler(_request(source="schedule"), None)

    (scan,) = result["scans"]
    stored = ScanStore(table).get_scan("000000000000", scan["scan_id"])
    assert stored is not None
    assert len(stored["findings"]) == scan["findings"] > 0
    assert len(stored["scan"]["checks_run"]) == 22
    assert MOTO_ACCOUNT_ID not in json.dumps(table.scan()["Items"], default=str)


def test_an_event_without_records_runs_one_public_scan(
    scanner_environment: None, table: Any
) -> None:
    result = lambda_handler.handler({}, None)

    assert len(result["scans"]) == 1
    assert len(ScanStore(table).list_scans("000000000000")) == 1


def test_duplicate_public_requests_run_one_scan(scanner_environment: None, table: Any) -> None:
    event = {"Records": [{"body": "{}"}, {"body": "{}"}]}

    result = lambda_handler.handler(event, None)

    assert len(result["scans"]) == 1


def test_connected_account_scan_is_stored_for_its_owner_only(
    scanner_environment: None, table: Any
) -> None:
    accounts = AccountStore(table)
    accounts.connect(USER, MOTO_ACCOUNT_ID)

    result = lambda_handler.handler(_request(user_id=USER, aws_account_id=MOTO_ACCOUNT_ID), None)

    (scan,) = result["scans"]
    store = ScanStore(table)
    stored = store.get_scan(tenant_key(USER, MOTO_ACCOUNT_ID), scan["scan_id"])
    assert stored is not None
    # A user's own scan keeps the real account ID; nothing is scrubbed.
    assert stored["scan"]["account_id"] == MOTO_ACCOUNT_ID
    assert store.list_scans("000000000000") == []
    assert store.list_scans(tenant_key("someone-else", MOTO_ACCOUNT_ID)) == []

    account = accounts.get(USER, MOTO_ACCOUNT_ID)
    assert account is not None
    assert (account["status"], account["last_scan_id"]) == ("connected", scan["scan_id"])


def test_a_role_that_cannot_be_assumed_is_recorded_not_retried(
    scanner_environment: None, table: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    accounts = AccountStore(table)
    accounts.connect(USER, MOTO_ACCOUNT_ID)

    def deny(*args: Any, **kwargs: Any) -> None:
        raise ClientError({"Error": {"Code": "AccessDenied", "Message": "no"}}, "AssumeRole")

    monkeypatch.setattr(lambda_handler, "assume_role_session", deny)

    # Returning normally, rather than raising, takes the message off the queue.
    result = lambda_handler.handler(_request(user_id=USER, aws_account_id=MOTO_ACCOUNT_ID), None)

    assert result["scans"] == [{"failed": MOTO_ACCOUNT_ID}]
    account = accounts.get(USER, MOTO_ACCOUNT_ID)
    assert account is not None
    assert account["status"] == "error"
    assert "could not assume the role" in account["last_error"]
    assert ScanStore(table).list_scans(tenant_key(USER, MOTO_ACCOUNT_ID)) == []


def test_a_role_in_another_account_is_refused(scanner_environment: None, table: Any) -> None:
    claimed = "111111111111"
    accounts = AccountStore(table)
    accounts.connect(USER, claimed)
    # Point the stored role at a different account from the one claimed.
    table.update_item(
        Key={"PK": f"USER#{USER}", "SK": f"ACCOUNT#{claimed}"},
        UpdateExpression="SET role_arn = :arn",
        ExpressionAttributeValues={":arn": ROLE_ARN},
    )

    result = lambda_handler.handler(_request(user_id=USER, aws_account_id=claimed), None)

    assert result["scans"] == [{"failed": claimed}]
    account = accounts.get(USER, claimed)
    assert account is not None
    assert "different AWS account" in account["last_error"]
    assert ScanStore(table).list_scans(tenant_key(USER, claimed)) == []


def test_a_request_for_an_unknown_account_is_skipped(
    scanner_environment: None, table: Any
) -> None:
    result = lambda_handler.handler(_request(user_id=USER, aws_account_id=MOTO_ACCOUNT_ID), None)

    assert result["scans"] == [{"skipped": MOTO_ACCOUNT_ID}]
