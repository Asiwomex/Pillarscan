"""Security groups that open SSH or RDP to the whole internet."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

ADMIN_PORTS = {22: "SSH", 3389: "RDP"}

META = CheckMeta(
    check_id="ec2_security_group_open_admin_ports",
    title="Security group open to the internet on port 22 or 3389",
    pillar=Pillar.SECURITY,
    severity=Severity.HIGH,
    resource_type="AWS::EC2::SecurityGroup",
    scope=Scope.REGIONAL,
    remediation=(
        "Remove the 0.0.0.0/0 rule. Use Systems Manager Session Manager, "
        "which needs no inbound port at all, or restrict the rule to a known "
        "IP range or a VPN."
    ),
)


def _open_to_world(permission: dict[str, Any]) -> bool:
    return any(r.get("CidrIp") == "0.0.0.0/0" for r in permission.get("IpRanges", [])) or any(
        r.get("CidrIpv6") == "::/0" for r in permission.get("Ipv6Ranges", [])
    )


def _covers_port(permission: dict[str, Any], port: int) -> bool:
    protocol = permission["IpProtocol"]
    if protocol == "-1":  # all protocols, all ports
        return True
    if protocol != "tcp":
        return False
    return bool(permission["FromPort"] <= port <= permission["ToPort"])


def exposed_admin_ports(group: dict[str, Any]) -> list[int]:
    open_rules = [p for p in group.get("IpPermissions", []) if _open_to_world(p)]
    return [port for port in ADMIN_PORTS if any(_covers_port(p, port) for p in open_rules)]


def run(ctx: CheckContext) -> Iterable[Finding]:
    ec2 = ctx.client("ec2")
    for page in ec2.get_paginator("describe_security_groups").paginate():
        for group in page["SecurityGroups"]:
            arn = ctx.arn("ec2", f"security-group/{group['GroupId']}")
            label = f"Security group {group['GroupId']} ({group['GroupName']})"
            exposed = exposed_admin_ports(group)
            if exposed:
                ports = ", ".join(f"{port} ({ADMIN_PORTS[port]})" for port in exposed)
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    arn,
                    f"{label} allows inbound traffic from anywhere on port "
                    f"{ports}. Bots scan the whole internet for these ports "
                    "and try stolen and default credentials within minutes.",
                )
            else:
                yield ctx.finding(
                    META,
                    Status.PASS,
                    arn,
                    f"{label} does not expose port 22 or 3389 to the internet.",
                )
