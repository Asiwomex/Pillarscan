"""Elastic IPs not associated with anything."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="ec2_unassociated_eip",
    title="Unassociated Elastic IP",
    pillar=Pillar.COST,
    severity=Severity.LOW,
    resource_type="AWS::EC2::EIP",
    scope=Scope.REGIONAL,
    remediation=(
        "Release the address under EC2 > Elastic IPs if nothing needs it. "
        "Releasing gives the address back to AWS, so check first that no "
        "DNS record or firewall allow-list still points at it."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    # describe_addresses is not a paginated API.
    for address in ctx.client("ec2").describe_addresses()["Addresses"]:
        public_ip = address["PublicIp"]
        arn = ctx.arn("ec2", f"elastic-ip/{address['AllocationId']}")
        if address.get("AssociationId"):
            yield ctx.finding(
                META, Status.PASS, arn, f"Elastic IP {public_ip} is associated with a resource."
            )
        else:
            yield ctx.finding(
                META,
                Status.FAIL,
                arn,
                f"Elastic IP {public_ip} is not associated with any resource. "
                "Every public IPv4 address is billed by the hour (about $3.60 "
                "a month), in use or not.",
            )
