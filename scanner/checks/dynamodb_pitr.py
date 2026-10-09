"""DynamoDB tables without point-in-time recovery."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="dynamodb_pitr",
    title="DynamoDB table without point-in-time recovery",
    pillar=Pillar.RELIABILITY,
    severity=Severity.MEDIUM,
    resource_type="AWS::DynamoDB::Table",
    scope=Scope.REGIONAL,
    remediation=(
        "Enable point-in-time recovery under the table's Backups tab. It is "
        "billed per GB of table size per month, which is negligible for "
        "small tables."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    dynamodb = ctx.client("dynamodb")
    for page in dynamodb.get_paginator("list_tables").paginate():
        for table in page["TableNames"]:
            backups = dynamodb.describe_continuous_backups(TableName=table)
            recovery = backups["ContinuousBackupsDescription"].get(
                "PointInTimeRecoveryDescription", {}
            )
            arn = ctx.arn("dynamodb", f"table/{table}")
            if recovery.get("PointInTimeRecoveryStatus") == "ENABLED":
                yield ctx.finding(
                    META, Status.PASS, arn, f"Table {table} has point-in-time recovery on."
                )
            else:
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    arn,
                    f"Table {table} has point-in-time recovery off. A buggy "
                    "deploy that overwrites or deletes items cannot be rolled "
                    "back to the moment before it ran.",
                )
