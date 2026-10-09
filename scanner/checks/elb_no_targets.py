"""Load balancers with no registered targets."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="elb_no_targets",
    title="Load balancer with no targets",
    pillar=Pillar.COST,
    severity=Severity.MEDIUM,
    resource_type="AWS::ElasticLoadBalancingV2::LoadBalancer",
    scope=Scope.REGIONAL,
    remediation=(
        "Delete the load balancer if the service behind it is gone, along "
        "with its now-empty target groups. If it should be serving traffic, "
        "register targets or fix the auto scaling group that should."
    ),
)


def _load_balancers_with_targets(elb: Any) -> set[str]:
    """ARNs of load balancers that have at least one registered target."""
    serving: set[str] = set()
    for page in elb.get_paginator("describe_target_groups").paginate():
        for group in page["TargetGroups"]:
            # describe_target_health is not a paginated API.
            health = elb.describe_target_health(TargetGroupArn=group["TargetGroupArn"])
            if health["TargetHealthDescriptions"]:
                serving.update(group["LoadBalancerArns"])
    return serving


def run(ctx: CheckContext) -> Iterable[Finding]:
    # elbv2 covers application, network and gateway load balancers.
    elb = ctx.client("elbv2")
    serving = _load_balancers_with_targets(elb)
    for page in elb.get_paginator("describe_load_balancers").paginate():
        for load_balancer in page["LoadBalancers"]:
            name = load_balancer["LoadBalancerName"]
            arn = load_balancer["LoadBalancerArn"]
            if arn in serving:
                yield ctx.finding(
                    META, Status.PASS, arn, f"Load balancer {name} has registered targets."
                )
            else:
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    arn,
                    f"Load balancer {name} has no registered targets, so it "
                    "can serve no traffic. It still costs about $16 a month "
                    "in hourly charges plus its public IPv4 addresses.",
                )
