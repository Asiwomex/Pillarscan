from __future__ import annotations

from typing import Any

import boto3
import pytest

from scanner.checks import ec2_security_group_open_admin_ports as check
from scanner.findings import Status

from .conftest import MOTO_ACCOUNT_ID, ContextFactory
from .helpers import REGION, statuses

ANYWHERE_V4 = {"IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
ANYWHERE_V6 = {"Ipv6Ranges": [{"CidrIpv6": "::/0"}]}
OFFICE = {"IpRanges": [{"CidrIp": "203.0.113.0/24"}]}


def _create_group(name: str, permission: dict[str, Any]) -> str:
    ec2 = boto3.client("ec2", region_name=REGION)
    group_id = ec2.create_security_group(GroupName=name, Description=name)["GroupId"]
    ec2.authorize_security_group_ingress(GroupId=group_id, IpPermissions=[permission])
    return f"arn:aws:ec2:{REGION}:{MOTO_ACCOUNT_ID}:security-group/{group_id}"


@pytest.mark.parametrize(
    ("permission", "expected"),
    [
        ({"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, **ANYWHERE_V4}, Status.FAIL),
        ({"IpProtocol": "tcp", "FromPort": 3389, "ToPort": 3389, **ANYWHERE_V6}, Status.FAIL),
        ({"IpProtocol": "tcp", "FromPort": 0, "ToPort": 65535, **ANYWHERE_V4}, Status.FAIL),
        ({"IpProtocol": "-1", **ANYWHERE_V4}, Status.FAIL),
        ({"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, **ANYWHERE_V4}, Status.PASS),
        ({"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, **OFFICE}, Status.PASS),
        ({"IpProtocol": "udp", "FromPort": 22, "ToPort": 22, **ANYWHERE_V4}, Status.PASS),
    ],
)
def test_rule_shapes(
    make_ctx: ContextFactory, permission: dict[str, Any], expected: Status
) -> None:
    arn = _create_group("under-test", permission)

    findings = list(check.run(make_ctx(region=REGION)))

    assert statuses(findings, arn) == [expected]


def test_names_every_exposed_port(make_ctx: ContextFactory) -> None:
    arn = _create_group(
        "wide-open", {"IpProtocol": "tcp", "FromPort": 0, "ToPort": 65535, **ANYWHERE_V4}
    )

    finding = next(f for f in check.run(make_ctx(region=REGION)) if f.resource_arn == arn)

    assert "22 (SSH)" in finding.description
    assert "3389 (RDP)" in finding.description
    assert finding.region == REGION
