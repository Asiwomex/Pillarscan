from __future__ import annotations

from datetime import datetime, timedelta, timezone

import boto3

from scanner.checks import ebs_old_snapshot
from scanner.findings import Status

from .conftest import ContextFactory
from .helpers import REGION, statuses


def _create_snapshot() -> str:
    ec2 = boto3.client("ec2", region_name=REGION)
    volume_id = ec2.create_volume(Size=1, AvailabilityZone=f"{REGION}a")["VolumeId"]
    snapshot_id = ec2.create_snapshot(VolumeId=volume_id)["SnapshotId"]
    return f"arn:aws:ec2:{REGION}::snapshot/{snapshot_id}"


def _days_from_now(days: int) -> datetime:
    # moto stamps snapshots with the current time, so tests move the scan
    # clock forward instead of backdating the snapshot.
    return datetime.now(timezone.utc) + timedelta(days=days)


def test_fails_for_snapshot_older_than_90_days(make_ctx: ContextFactory) -> None:
    arn = _create_snapshot()

    findings = list(ebs_old_snapshot.run(make_ctx(region=REGION, now=_days_from_now(120))))

    assert statuses(findings, arn) == [Status.FAIL]


def test_passes_for_recent_snapshot(make_ctx: ContextFactory) -> None:
    arn = _create_snapshot()

    findings = list(ebs_old_snapshot.run(make_ctx(region=REGION, now=_days_from_now(30))))

    assert statuses(findings, arn) == [Status.PASS]

