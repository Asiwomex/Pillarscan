from __future__ import annotations

import boto3

from scanner.checks import s3_public_access_block
from scanner.findings import Status

from .conftest import MOTO_ACCOUNT_ID, ContextFactory
from .helpers import REGION

ALL_ON = {
    "BlockPublicAcls": True,
    "IgnorePublicAcls": True,
    "BlockPublicPolicy": True,
    "RestrictPublicBuckets": True,
}


def _create_bucket(name: str) -> str:
    boto3.client("s3", region_name=REGION).create_bucket(Bucket=name)
    return f"arn:aws:s3:::{name}"


def test_fails_for_bucket_without_a_block(make_ctx: ContextFactory) -> None:
    arn = _create_bucket("open-bucket")

    findings = list(s3_public_access_block.run(make_ctx()))

    assert [(f.status, f.resource_arn, f.region) for f in findings] == [
        (Status.FAIL, arn, "us-east-1")
    ]


def test_passes_when_bucket_has_all_four_settings(make_ctx: ContextFactory) -> None:
    _create_bucket("locked-bucket")
    boto3.client("s3", region_name=REGION).put_public_access_block(
        Bucket="locked-bucket", PublicAccessBlockConfiguration=ALL_ON
    )

    findings = list(s3_public_access_block.run(make_ctx()))

    assert [f.status for f in findings] == [Status.PASS]


def test_fails_and_names_the_missing_settings(make_ctx: ContextFactory) -> None:
    _create_bucket("half-bucket")
    boto3.client("s3", region_name=REGION).put_public_access_block(
        Bucket="half-bucket",
        PublicAccessBlockConfiguration={**ALL_ON, "BlockPublicPolicy": False},
    )

    findings = list(s3_public_access_block.run(make_ctx()))

    assert [f.status for f in findings] == [Status.FAIL]
    assert "BlockPublicPolicy" in findings[0].description
    assert "BlockPublicAcls" not in findings[0].description


def test_account_level_block_covers_buckets_without_their_own(make_ctx: ContextFactory) -> None:
    _create_bucket("covered-bucket")
    boto3.client("s3control", region_name=REGION).put_public_access_block(
        AccountId=MOTO_ACCOUNT_ID, PublicAccessBlockConfiguration=ALL_ON
    )

    findings = list(s3_public_access_block.run(make_ctx()))

    assert [f.status for f in findings] == [Status.PASS]


def test_reports_the_bucket_region(make_ctx: ContextFactory) -> None:
    boto3.client("s3", region_name="eu-west-1").create_bucket(
        Bucket="irish-bucket",
        CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
    )

    findings = list(s3_public_access_block.run(make_ctx()))

    assert [f.region for f in findings] == ["eu-west-1"]
