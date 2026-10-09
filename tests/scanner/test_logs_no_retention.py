from __future__ import annotations

import boto3

from scanner.checks import logs_no_retention
from scanner.findings import Status

from .conftest import MOTO_ACCOUNT_ID, ContextFactory
from .helpers import REGION


def _create_log_group(name: str, retention_days: int | None = None) -> str:
    logs = boto3.client("logs", region_name=REGION)
    logs.create_log_group(logGroupName=name)
    if retention_days:
        logs.put_retention_policy(logGroupName=name, retentionInDays=retention_days)
    return f"arn:aws:logs:{REGION}:{MOTO_ACCOUNT_ID}:log-group:{name}"


def test_fails_when_logs_never_expire(make_ctx: ContextFactory) -> None:
    arn = _create_log_group("/app/forever")

    findings = list(logs_no_retention.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_passes_when_retention_is_set(make_ctx: ContextFactory) -> None:
    arn = _create_log_group("/app/tidy", retention_days=30)

    findings = list(logs_no_retention.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]
    assert "30 days" in findings[0].description
