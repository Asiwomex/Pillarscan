"""S3 buckets without versioning."""

from __future__ import annotations

from collections.abc import Iterable

from botocore.exceptions import ClientError

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status
from scanner.s3 import bucket_arn, bucket_names, bucket_region

META = CheckMeta(
    check_id="s3_versioning",
    title="S3 bucket without versioning",
    pillar=Pillar.RELIABILITY,
    severity=Severity.LOW,
    resource_type="AWS::S3::Bucket",
    scope=Scope.GLOBAL,
    remediation=(
        "Enable versioning on buckets that hold data you cannot regenerate, "
        "and add a lifecycle rule that expires old versions so storage cost "
        "does not grow without limit."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    s3 = ctx.client("s3")
    for name in bucket_names(s3):
        arn = bucket_arn(name)
        try:
            region = bucket_region(s3, name)
            # Status is absent when versioning was never enabled.
            status = s3.get_bucket_versioning(Bucket=name).get("Status")
        except ClientError as exc:
            yield ctx.error(META, arn, exc)
            continue

        if status == "Enabled":
            yield ctx.finding(
                META, Status.PASS, arn, f"Bucket {name} has versioning enabled.", region=region
            )
        else:
            yield ctx.finding(
                META,
                Status.FAIL,
                arn,
                f"Bucket {name} has versioning {'suspended' if status else 'off'}. "
                "An overwrite or delete, accidental or malicious, is then "
                "permanent.",
                region=region,
            )
