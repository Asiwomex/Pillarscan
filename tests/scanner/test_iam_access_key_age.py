from __future__ import annotations

from datetime import datetime, timedelta, timezone

import boto3

from scanner.checks import iam_access_key_age
from scanner.findings import Status

from .conftest import ContextFactory


def _create_user_with_key(name: str) -> tuple[str, str]:
    iam = boto3.client("iam", region_name="us-east-1")
    arn: str = iam.create_user(UserName=name)["User"]["Arn"]
    key_id: str = iam.create_access_key(UserName=name)["AccessKey"]["AccessKeyId"]
    return arn, key_id


def _days_from_now(days: int) -> datetime:
    # moto stamps keys with the current time, so tests move the scan clock
    # forward instead of backdating the key.
    return datetime.now(timezone.utc) + timedelta(days=days)


def test_fails_for_key_older_than_90_days(make_ctx: ContextFactory) -> None:
    arn, key_id = _create_user_with_key("alice")

    findings = list(iam_access_key_age.run(make_ctx(now=_days_from_now(120))))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]
    assert key_id[-4:] in findings[0].description
    assert key_id not in findings[0].description


def test_passes_for_recent_key(make_ctx: ContextFactory) -> None:
    arn, _ = _create_user_with_key("bob")

    findings = list(iam_access_key_age.run(make_ctx(now=_days_from_now(30))))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]


def test_ignores_inactive_keys(make_ctx: ContextFactory) -> None:
    _, key_id = _create_user_with_key("carol")
    boto3.client("iam", region_name="us-east-1").update_access_key(
        UserName="carol", AccessKeyId=key_id, Status="Inactive"
    )

    assert list(iam_access_key_age.run(make_ctx(now=_days_from_now(120)))) == []


def test_reports_each_key_of_a_user(make_ctx: ContextFactory) -> None:
    _create_user_with_key("dave")
    boto3.client("iam", region_name="us-east-1").create_access_key(UserName="dave")

    findings = list(iam_access_key_age.run(make_ctx(now=_days_from_now(120))))

    assert [finding.status for finding in findings] == [Status.FAIL, Status.FAIL]
