"""gp2 volumes that could be gp3."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="ebs_gp2_volume",
    title="gp2 volume that could be gp3",
    pillar=Pillar.COST,
    severity=Severity.LOW,
    resource_type="AWS::EC2::Volume",
    scope=Scope.REGIONAL,
    remediation=(
        "Modify the volume and change its type to gp3. The change happens "
        "online with no downtime. For gp2 volumes larger than 1,000 GiB, "
        "set gp3 IOPS to match what gp2 provided (3 IOPS per GiB)."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    ec2 = ctx.client("ec2")
    for page in ec2.get_paginator("describe_volumes").paginate():
        for volume in page["Volumes"]:
            volume_id = volume["VolumeId"]
            arn = ctx.arn("ec2", f"volume/{volume_id}")
            # Only general purpose SSDs are in scope; io1, st1 and the rest
            # are chosen for reasons this check cannot judge.
            if volume["VolumeType"] == "gp2":
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    arn,
                    f"Volume {volume_id} ({volume['Size']} GiB) is gp2. gp3 "
                    "costs about 20% less per GiB and gives 3,000 IOPS at any "
                    "size, where gp2 performance depends on volume size.",
                )
            elif volume["VolumeType"] == "gp3":
                yield ctx.finding(META, Status.PASS, arn, f"Volume {volume_id} is gp3.")
