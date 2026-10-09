"""The two volume checks read the same describe call, so they share a test file."""

from __future__ import annotations

import boto3

from scanner.checks import ebs_gp2_volume, ebs_unattached_volume
from scanner.findings import Status

from .conftest import MOTO_ACCOUNT_ID, ContextFactory
from .helpers import REGION, launch_instance, statuses


def _create_volume(volume_type: str = "gp3") -> tuple[str, str]:
    volume_id: str = boto3.client("ec2", region_name=REGION).create_volume(
        Size=1, AvailabilityZone=f"{REGION}a", VolumeType=volume_type
    )["VolumeId"]
    return volume_id, f"arn:aws:ec2:{REGION}:{MOTO_ACCOUNT_ID}:volume/{volume_id}"


def test_unattached_volume_fails(make_ctx: ContextFactory) -> None:
    _, arn = _create_volume()

    findings = list(ebs_unattached_volume.run(make_ctx(region=REGION)))

    assert statuses(findings, arn) == [Status.FAIL]


def test_attached_volume_passes(make_ctx: ContextFactory) -> None:
    volume_id, arn = _create_volume()
    boto3.client("ec2", region_name=REGION).attach_volume(
        VolumeId=volume_id, InstanceId=launch_instance(), Device="/dev/sdf"
    )

    findings = list(ebs_unattached_volume.run(make_ctx(region=REGION)))

    assert statuses(findings, arn) == [Status.PASS]


def test_gp2_volume_fails(make_ctx: ContextFactory) -> None:
    _, arn = _create_volume("gp2")

    findings = list(ebs_gp2_volume.run(make_ctx(region=REGION)))

    assert statuses(findings, arn) == [Status.FAIL]


def test_gp3_volume_passes(make_ctx: ContextFactory) -> None:
    _, arn = _create_volume("gp3")

    findings = list(ebs_gp2_volume.run(make_ctx(region=REGION)))

    assert statuses(findings, arn) == [Status.PASS]


def test_other_volume_types_are_out_of_scope(make_ctx: ContextFactory) -> None:
    _, arn = _create_volume("st1")

    findings = list(ebs_gp2_volume.run(make_ctx(region=REGION)))

    assert statuses(findings, arn) == []
