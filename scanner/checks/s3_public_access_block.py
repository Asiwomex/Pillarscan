"""S3 buckets not fully covered by a public access block."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from botocore.exceptions import ClientError

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status
from scanner.s3 import bucket_arn, bucket_names, bucket_region

SETTINGS = ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")
NOT_CONFIGURED = "NoSuchPublicAccessBlockConfiguration"

META = CheckMeta(
    check_id="s3_public_access_block",
    title="S3 bucket without public access block",
    pillar=Pillar.SECURITY,
    severity=Severity.HIGH,
    resource_type="AWS::S3::Bucket",
    # Buckets are listed once for the whole account; each finding carries
    # the bucket's own region.
    scope=Scope.GLOBAL,
    remediation=(
        "Turn on all four Block Public Access settings for the bucket, or "
        "once for the whole account under S3 > Block Public Access settings "
        "for this account. Serve public content through CloudFront with "
        "origin access control instead of a public bucket."
    ),
)


def _settings_or_empty(call: Any, **kwargs: Any) -> dict[str, bool]:
    try:
        config: dict[str, bool] = call(**kwargs)["PublicAccessBlockConfiguration"]
    except ClientError as exc:
        if exc.response["Error"]["Code"] == NOT_CONFIGURED:
            return {}
        raise
    return config


def run(ctx: CheckContext) -> Iterable[Finding]:
    s3 = ctx.client("s3")
    # A setting applies if it is on at either level, so the account-level
    # block can cover buckets that have none of their own.
    account_block = _settings_or_empty(
        ctx.client("s3control").get_public_access_block, AccountId=ctx.account_id
    )
    for name in bucket_names(s3):
        arn = bucket_arn(name)
        # One unreadable bucket (a bucket policy can deny even auditors)
        # should not hide the rest.
        try:
            region = bucket_region(s3, name)
            bucket_block = _settings_or_empty(s3.get_public_access_block, Bucket=name)
        except ClientError as exc:
            yield ctx.error(META, arn, exc)
            continue

        missing = [
            setting
            for setting in SETTINGS
            if not (bucket_block.get(setting) or account_block.get(setting))
        ]
        if missing:
            yield ctx.finding(
                META,
                Status.FAIL,
                arn,
                f"Bucket {name} does not enforce: {', '.join(missing)}. Without "
                "these, one bad ACL or bucket policy can expose every object "
                "to the internet.",
                region=region,
            )
        else:
            yield ctx.finding(
                META,
                Status.PASS,
                arn,
                f"Bucket {name} is covered by all four Block Public Access settings.",
                region=region,
            )
