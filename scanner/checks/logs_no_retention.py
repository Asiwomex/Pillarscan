"""CloudWatch log groups that keep logs forever."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="logs_no_retention",
    title="CloudWatch log group with no retention set",
    pillar=Pillar.COST,
    severity=Severity.LOW,
    resource_type="AWS::Logs::LogGroup",
    scope=Scope.REGIONAL,
    remediation=(
        "Set a retention period on the log group; 30 or 90 days suits most "
        "application logs. Set it in the Terraform or CloudFormation that "
        "creates the group so new groups do not default to never expiring."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    logs = ctx.client("logs")
    for page in logs.get_paginator("describe_log_groups").paginate():
        for group in page["logGroups"]:
            name = group["logGroupName"]
            # The API returns the ARN with a ":*" suffix meaning "all streams".
            arn = group["arn"].removesuffix(":*")
            # retentionInDays is absent when logs never expire.
            days = group.get("retentionInDays")
            if days:
                yield ctx.finding(
                    META, Status.PASS, arn, f"Log group {name} keeps logs for {days} days."
                )
            else:
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    arn,
                    f"Log group {name} never expires its logs. Stored log "
                    "data is billed per GB every month and only ever grows.",
                )
