"""RDS instances running in a single availability zone."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="rds_multi_az",
    title="RDS instance without Multi-AZ",
    pillar=Pillar.RELIABILITY,
    severity=Severity.MEDIUM,
    resource_type="AWS::RDS::DBInstance",
    scope=Scope.REGIONAL,
    remediation=(
        "Modify the instance and enable Multi-AZ for production databases. "
        "It roughly doubles the instance cost, so leaving it off for "
        "development databases is a reasonable choice."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    rds = ctx.client("rds")
    for page in rds.get_paginator("describe_db_instances").paginate():
        for instance in page["DBInstances"]:
            # Aurora handles availability at the cluster level; the MultiAZ
            # flag on its member instances says nothing useful.
            if instance.get("DBClusterIdentifier"):
                continue
            name = instance["DBInstanceIdentifier"]
            if instance["MultiAZ"]:
                yield ctx.finding(
                    META,
                    Status.PASS,
                    instance["DBInstanceArn"],
                    f"Database {name} has a standby in another availability zone.",
                )
            else:
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    instance["DBInstanceArn"],
                    f"Database {name} runs in one availability zone. If that "
                    "zone or the instance fails, the database is down until "
                    "it is restored by hand.",
                )
