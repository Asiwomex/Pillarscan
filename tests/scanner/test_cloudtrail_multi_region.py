from __future__ import annotations

import boto3

from scanner.checks import cloudtrail_multi_region
from scanner.findings import Status

from .conftest import ContextFactory
from .helpers import REGION


def _create_trail(
    name: str, multi_region: bool, logging: bool, home_region: str = REGION
) -> str:
    boto3.client("s3", region_name=REGION).create_bucket(Bucket=f"{name}-logs")
    cloudtrail = boto3.client("cloudtrail", region_name=home_region)
    arn: str = cloudtrail.create_trail(
        Name=name, S3BucketName=f"{name}-logs", IsMultiRegionTrail=multi_region
    )["TrailARN"]
    if logging:
        cloudtrail.start_logging(Name=name)
    return arn


def test_fails_when_there_are_no_trails(make_ctx: ContextFactory) -> None:
    findings = list(cloudtrail_multi_region.run(make_ctx()))

    assert [f.status for f in findings] == [Status.FAIL]


def test_fails_when_the_only_trail_covers_one_region(make_ctx: ContextFactory) -> None:
    _create_trail("local-trail", multi_region=False, logging=True)

    findings = list(cloudtrail_multi_region.run(make_ctx()))

    assert [f.status for f in findings] == [Status.FAIL]


def test_fails_when_the_multi_region_trail_is_not_logging(make_ctx: ContextFactory) -> None:
    _create_trail("stopped-trail", multi_region=True, logging=False)

    findings = list(cloudtrail_multi_region.run(make_ctx()))

    assert [f.status for f in findings] == [Status.FAIL]


def test_passes_when_a_multi_region_trail_is_logging(make_ctx: ContextFactory) -> None:
    arn = _create_trail("org-trail", multi_region=True, logging=True)

    findings = list(cloudtrail_multi_region.run(make_ctx()))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]


def test_finds_a_trail_homed_in_another_region(make_ctx: ContextFactory) -> None:
    arn = _create_trail("irish-trail", multi_region=True, logging=True, home_region="eu-west-1")

    findings = list(cloudtrail_multi_region.run(make_ctx()))

    assert [(f.status, f.resource_arn, f.region) for f in findings] == [
        (Status.PASS, arn, "eu-west-1")
    ]
