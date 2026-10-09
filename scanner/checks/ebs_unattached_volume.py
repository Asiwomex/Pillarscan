"""EBS volumes not attached to any instance."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="ebs_unattached_volume",
    title="Unattached EBS volume",
    pillar=Pillar.COST,
    severity=Severity.MEDIUM,
    resource_type="AWS::EC2::Volume",
    scope=Scope.REGIONAL,
    remediation=(
        "Delete the volume if the data is not needed. If it might be, take "
        "a snapshot first: snapshots are stored compressed and cost much "
        "less than a provisioned volume."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    ec2 = ctx.client("ec2")
    for page in ec2.get_paginator("describe_volumes").paginate():
        for volume in page["Volumes"]:
            volume_id = volume["VolumeId"]
            arn = ctx.arn("ec2", f"volume/{volume_id}")
            # "available" is the state of a volume nothing is attached to.
            if volume["State"] == "available":
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    arn,
                    f"Volume {volume_id} ({volume['Size']} GiB "
                    f"{volume['VolumeType']}) is not attached to an instance. "
                    "It is billed for its full provisioned size whether or "
                    "not anything uses it.",
                )
            else:
                yield ctx.finding(
                    META, Status.PASS, arn, f"Volume {volume_id} is attached to an instance."
                )
