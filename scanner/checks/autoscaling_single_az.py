"""Auto scaling groups that span a single availability zone."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="autoscaling_single_az",
    title="Auto scaling group in a single availability zone",
    pillar=Pillar.RELIABILITY,
    severity=Severity.MEDIUM,
    resource_type="AWS::AutoScaling::AutoScalingGroup",
    scope=Scope.REGIONAL,
    remediation=(
        "Add subnets from at least one more availability zone to the group. "
        "Spreading instances across zones costs nothing extra."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    autoscaling = ctx.client("autoscaling")
    for page in autoscaling.get_paginator("describe_auto_scaling_groups").paginate():
        for group in page["AutoScalingGroups"]:
            name = group["AutoScalingGroupName"]
            zones = group["AvailabilityZones"]
            if len(zones) > 1:
                yield ctx.finding(
                    META,
                    Status.PASS,
                    group["AutoScalingGroupARN"],
                    f"Group {name} spans {len(zones)} availability zones.",
                )
            else:
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    group["AutoScalingGroupARN"],
                    f"Group {name} launches instances only in "
                    f"{', '.join(zones)}. If that zone has an outage the "
                    "group cannot replace its instances anywhere else.",
                )
