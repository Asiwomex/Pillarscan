"""EBS encryption by default turned off in a region."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="ebs_default_encryption",
    title="EBS default encryption off",
    pillar=Pillar.SECURITY,
    severity=Severity.MEDIUM,
    resource_type="AWS::::Account",
    # The setting is per region, not per account.
    scope=Scope.REGIONAL,
    remediation=(
        "Turn on EBS encryption by default under EC2 > Settings > Data "
        "protection and security in each region. It is free with the "
        "AWS managed key and applies to new volumes only; existing "
        "unencrypted volumes must be copied to encrypted ones."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    response = ctx.client("ec2").get_ebs_encryption_by_default()
    if response["EbsEncryptionByDefault"]:
        yield ctx.finding(
            META,
            Status.PASS,
            ctx.account_arn,
            f"New EBS volumes in {ctx.region} are encrypted by default.",
        )
    else:
        yield ctx.finding(
            META,
            Status.FAIL,
            ctx.account_arn,
            f"EBS encryption by default is off in {ctx.region}. Any volume or "
            "snapshot created without an explicit encryption flag stores its "
            "data in plain text, and an unencrypted snapshot can be shared "
            "with other accounts.",
        )
