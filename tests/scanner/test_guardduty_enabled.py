from __future__ import annotations

import boto3

from scanner.checks import guardduty_enabled
from scanner.findings import Status

from .conftest import MOTO_ACCOUNT_ID, ContextFactory
from .helpers import REGION


def test_fails_when_there_is_no_detector(make_ctx: ContextFactory) -> None:
    findings = list(guardduty_enabled.run(make_ctx(region=REGION)))

    assert [(f.status, f.region) for f in findings] == [(Status.FAIL, REGION)]


def test_fails_when_the_detector_is_suspended(make_ctx: ContextFactory) -> None:
    boto3.client("guardduty", region_name=REGION).create_detector(Enable=False)

    findings = list(guardduty_enabled.run(make_ctx(region=REGION)))

    assert [f.status for f in findings] == [Status.FAIL]


def test_passes_when_the_detector_is_enabled(make_ctx: ContextFactory) -> None:
    detector_id = boto3.client("guardduty", region_name=REGION).create_detector(Enable=True)[
        "DetectorId"
    ]

    findings = list(guardduty_enabled.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [
        (Status.PASS, f"arn:aws:guardduty:{REGION}:{MOTO_ACCOUNT_ID}:detector/{detector_id}")
    ]


def test_a_detector_in_one_region_does_not_cover_another(make_ctx: ContextFactory) -> None:
    boto3.client("guardduty", region_name="eu-west-1").create_detector(Enable=True)

    findings = list(guardduty_enabled.run(make_ctx(region=REGION)))

    assert [f.status for f in findings] == [Status.FAIL]
