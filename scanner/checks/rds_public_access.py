"""RDS instances that are publicly accessible."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="rds_public_access",
    title="Publicly accessible RDS instance",
    pillar=Pillar.SECURITY,
    severity=Severity.HIGH,
    resource_type="AWS::RDS::DBInstance",
    scope=Scope.REGIONAL,
    remediation=(
        "Modify the instance and set Public access to No, and keep it in "
        "private subnets. Reach it from your machine through Session "
        "Manager port forwarding or a VPN instead of the open internet."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    rds = ctx.client("rds")
    for page in rds.get_paginator("describe_db_instances").paginate():
        for instance in page["DBInstances"]:
            name = instance["DBInstanceIdentifier"]
            if instance["PubliclyAccessible"]:
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    instance["DBInstanceArn"],
                    f"Database {name} has a public endpoint. Only its "
                    "security group and password stand between the data and "
                    "anyone on the internet.",
                )
            else:
                yield ctx.finding(
                    META,
                    Status.PASS,
                    instance["DBInstanceArn"],
                    f"Database {name} is not publicly accessible.",
                )
