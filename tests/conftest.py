from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import boto3
import pytest
from moto import mock_aws

TABLE_NAME = "pillarscan-test"


@pytest.fixture(autouse=True)
def aws(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Mock AWS for every test and make sure real credentials are never used."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    with mock_aws():
        yield


@pytest.fixture
def table(monkeypatch: pytest.MonkeyPatch) -> Any:
    """The scans table, with the same keys as infra/platform creates."""
    monkeypatch.setenv("TABLE_NAME", TABLE_NAME)
    return boto3.resource("dynamodb", region_name="us-east-1").create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )


def make_report(started_at: str, statuses: list[tuple[str, str]]) -> dict[str, Any]:
    """A scan report in the scanner's output shape, from (status, severity) pairs."""
    return {
        "scan": {
            "account_id": "000000000000",
            "started_at": started_at,
            "finished_at": started_at,
            "regions": ["us-east-1"],
            "checks_run": ["iam_root_mfa", "s3_versioning"],
        },
        "findings": [
            {
                "check_id": "s3_versioning",
                "title": "S3 bucket without versioning",
                "pillar": "reliability",
                "severity": severity,
                "status": status,
                "resource_arn": f"arn:aws:s3:::bucket-{index}",
                "resource_type": "AWS::S3::Bucket",
                "region": "us-east-1",
                "account_id": "000000000000",
                "description": "What is wrong.",
                "remediation": "How to fix it.",
                "scanned_at": started_at,
            }
            for index, (status, severity) in enumerate(statuses)
        ],
    }
