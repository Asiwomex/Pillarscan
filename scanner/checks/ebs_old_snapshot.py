"""EBS snapshots older than 90 days."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

MAX_SNAPSHOT_AGE = timedelta(days=90)

META = CheckMeta(
    check_id="ebs_old_snapshot",
    title="EBS snapshot older than 90 days",
    pillar=Pillar.COST,
    severity=Severity.LOW,
    resource_type="AWS::EC2::Snapshot",
    scope=Scope.REGIONAL,
    remediation=(
        "Delete snapshots you no longer need (a snapshot backing a "
        "registered AMI must have the AMI deregistered first). Use Data "
        "Lifecycle Manager to expire snapshots automatically, or move ones "
        "kept for compliance to the cheaper archive tier."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    ec2 = ctx.client("ec2")
    # Without OwnerIds the API returns every public snapshot in the region.
    pages = ec2.get_paginator("describe_snapshots").paginate(OwnerIds=["self"])
    for page in pages:
        for snapshot in page["Snapshots"]:
            snapshot_id = snapshot["SnapshotId"]
            # Snapshot ARNs have no account ID segment.
            arn = f"arn:aws:ec2:{ctx.region}::snapshot/{snapshot_id}"
            age = ctx.now - snapshot["StartTime"]
            if age > MAX_SNAPSHOT_AGE:
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    arn,
                    f"Snapshot {snapshot_id} of a {snapshot['VolumeSize']} GiB "
                    f"volume is {age.days} days old. Forgotten snapshots are "
                    "billed every month for as long as they exist.",
                )
            else:
                yield ctx.finding(
                    META, Status.PASS, arn, f"Snapshot {snapshot_id} is {age.days} days old."
                )
