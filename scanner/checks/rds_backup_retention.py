"""RDS instances with automated backups disabled."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="rds_backup_retention",
    title="RDS automated backups disabled",
    pillar=Pillar.RELIABILITY,
    severity=Severity.HIGH,
    resource_type="AWS::RDS::DBInstance",
    scope=Scope.REGIONAL,
    remediation=(
        "Modify the instance and set the backup retention period to at "
        "least 7 days. Backup storage up to the size of the database is "
        "included in the instance price."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    rds = ctx.client("rds")
    for page in rds.get_paginator("describe_db_instances").paginate():
        for instance in page["DBInstances"]:
            # Aurora backups belong to the cluster and cannot be turned off.
            if instance.get("DBClusterIdentifier"):
                continue
            name = instance["DBInstanceIdentifier"]
            days = instance["BackupRetentionPeriod"]
            # A retention period of 0 is how RDS represents "backups off".
            if days > 0:
                yield ctx.finding(
                    META,
                    Status.PASS,
                    instance["DBInstanceArn"],
                    f"Database {name} keeps automated backups for {days} days.",
                )
            else:
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    instance["DBInstanceArn"],
                    f"Database {name} has automated backups turned off. There "
                    "is no point-in-time restore, so a bad migration or a "
                    "deleted table cannot be undone.",
                )
