from __future__ import annotations

import boto3
import pytest
from botocore.stub import Stubber

from scanner.check import CheckContext
from scanner.checks import iam_root_mfa
from scanner.findings import Status

from .conftest import MOTO_ACCOUNT_ID, ContextFactory


def test_fails_when_root_has_no_mfa(make_ctx: ContextFactory) -> None:
    # moto reports AccountMFAEnabled = 0 for a fresh account.
    findings = list(iam_root_mfa.run(make_ctx()))

    assert len(findings) == 1
    assert findings[0].status is Status.FAIL
    assert findings[0].resource_arn == f"arn:aws:iam::{MOTO_ACCOUNT_ID}:root"
    assert findings[0].region == "global"


def test_passes_when_root_has_mfa(
    make_ctx: ContextFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    # moto cannot enable root MFA, so stub the one response the check reads.
    iam = boto3.client("iam", region_name="us-east-1")
    monkeypatch.setattr(CheckContext, "client", lambda self, service: iam)
    with Stubber(iam) as stubber:
        stubber.add_response("get_account_summary", {"SummaryMap": {"AccountMFAEnabled": 1}})
        findings = list(iam_root_mfa.run(make_ctx()))

    assert [finding.status for finding in findings] == [Status.PASS]
