from __future__ import annotations

import boto3

from scanner.checks import ebs_default_encryption
from scanner.findings import Status

from .conftest import ContextFactory
from .helpers import REGION


def test_fails_when_default_encryption_is_off(make_ctx: ContextFactory) -> None:
    findings = list(ebs_default_encryption.run(make_ctx(region=REGION)))

    assert [(f.status, f.region) for f in findings] == [(Status.FAIL, REGION)]


def test_passes_when_default_encryption_is_on(make_ctx: ContextFactory) -> None:
    boto3.client("ec2", region_name=REGION).enable_ebs_encryption_by_default()

    findings = list(ebs_default_encryption.run(make_ctx(region=REGION)))

    assert [f.status for f in findings] == [Status.PASS]


def test_the_setting_is_per_region(make_ctx: ContextFactory) -> None:
    boto3.client("ec2", region_name="eu-west-1").enable_ebs_encryption_by_default()

    findings = list(ebs_default_encryption.run(make_ctx(region=REGION)))

    assert [f.status for f in findings] == [Status.FAIL]
