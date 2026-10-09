from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import boto3
import pytest

from scanner.__main__ import main
from scanner.session import assume_role_session

from .conftest import MOTO_ACCOUNT_ID
from .helpers import REGION

ROLE_ARN = f"arn:aws:iam::{MOTO_ACCOUNT_ID}:role/PillarscanAuditRole"
EXTERNAL_ID = "an-external-id-for-tests"


def _create_audit_role() -> None:
    trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{MOTO_ACCOUNT_ID}:root"},
                "Action": "sts:AssumeRole",
                "Condition": {"StringEquals": {"sts:ExternalId": EXTERNAL_ID}},
            }
        ],
    }
    boto3.client("iam", region_name=REGION).create_role(
        RoleName="PillarscanAuditRole", AssumeRolePolicyDocument=json.dumps(trust)
    )


def test_always_sends_the_external_id() -> None:
    # moto does not enforce trust policy conditions, so check the request itself.
    base = Mock(region_name=REGION)
    base.client.return_value.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "role-key",
            "SecretAccessKey": "role-secret",
            "SessionToken": "role-token",
        }
    }

    session = assume_role_session(base, ROLE_ARN, EXTERNAL_ID)

    base.client.return_value.assume_role.assert_called_once_with(
        RoleArn=ROLE_ARN, RoleSessionName="pillarscan-scan", ExternalId=EXTERNAL_ID
    )
    assert session.get_credentials().access_key == "role-key"
    assert session.region_name == REGION


def test_scan_runs_with_the_role_credentials(session: boto3.Session) -> None:
    _create_audit_role()

    role_session = assume_role_session(session, ROLE_ARN, EXTERNAL_ID)

    identity = role_session.client("sts", region_name=REGION).get_caller_identity()
    assert ":assumed-role/PillarscanAuditRole/" in identity["Arn"]


def test_cli_scans_through_the_role(tmp_path: Path) -> None:
    _create_audit_role()
    out = tmp_path / "findings.json"

    exit_code = main(
        [
            "--out", str(out),
            "--regions", REGION,
            "--role-arn", ROLE_ARN,
            "--external-id", EXTERNAL_ID,
        ]
    )

    assert exit_code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["scan"]["account_id"] == MOTO_ACCOUNT_ID


def test_cli_refuses_a_role_without_an_external_id() -> None:
    with pytest.raises(SystemExit) as error:
        main(["--role-arn", ROLE_ARN])

    assert error.value.code == 2
