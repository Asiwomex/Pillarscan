from __future__ import annotations

import boto3

from scanner.checks import ec2_unassociated_eip
from scanner.findings import Status

from .conftest import MOTO_ACCOUNT_ID, ContextFactory
from .helpers import REGION, launch_instance


def _allocate_address() -> tuple[str, str]:
    allocation_id: str = boto3.client("ec2", region_name=REGION).allocate_address(Domain="vpc")[
        "AllocationId"
    ]
    return allocation_id, f"arn:aws:ec2:{REGION}:{MOTO_ACCOUNT_ID}:elastic-ip/{allocation_id}"


def test_fails_for_unassociated_address(make_ctx: ContextFactory) -> None:
    _, arn = _allocate_address()

    findings = list(ec2_unassociated_eip.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_passes_for_associated_address(make_ctx: ContextFactory) -> None:
    allocation_id, arn = _allocate_address()
    boto3.client("ec2", region_name=REGION).associate_address(
        AllocationId=allocation_id, InstanceId=launch_instance()
    )

    findings = list(ec2_unassociated_eip.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]
