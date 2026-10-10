from __future__ import annotations

import json
from typing import Any

import boto3
import pytest

from scanner import lambda_handler
from scanner.store import ScanStore

from .conftest import MOTO_ACCOUNT_ID
from .helpers import REGION

ROLE_ARN = f"arn:aws:iam::{MOTO_ACCOUNT_ID}:role/PillarscanAuditRole"
PARAMETER = "/pillarscan/external-id"


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


def test_scans_through_the_role_and_stores_the_result(
    scanner_environment: None, table: Any
) -> None:
    result = lambda_handler.handler({"Records": [{"body": "{}"}]}, None)

    stored = ScanStore(table).get_scan(MOTO_ACCOUNT_ID, result["scan_id"])
    assert stored is not None
    assert len(stored["findings"]) == result["findings"] > 0
    assert len(stored["scan"]["checks_run"]) == 22


def test_scrubs_the_account_id_when_asked(
    scanner_environment: None, table: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SCRUB_OUTPUT", "true")

    lambda_handler.handler({}, None)

    assert ScanStore(table).list_scans(MOTO_ACCOUNT_ID) == []
    (summary,) = ScanStore(table).list_scans("000000000000")
    assert MOTO_ACCOUNT_ID not in json.dumps(table.scan()["Items"], default=str)
    assert summary["account_id"] == "000000000000"
