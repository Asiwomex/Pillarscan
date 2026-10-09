from __future__ import annotations

import boto3

from scanner.checks import elb_no_targets
from scanner.findings import Status

from .conftest import ContextFactory
from .helpers import REGION, launch_instance


def _create_load_balancer(name: str) -> str:
    subnets = boto3.client("ec2", region_name=REGION).describe_subnets()["Subnets"]
    # An application load balancer needs subnets in two availability zones.
    by_zone = {subnet["AvailabilityZone"]: subnet["SubnetId"] for subnet in subnets}
    response = boto3.client("elbv2", region_name=REGION).create_load_balancer(
        Name=name, Subnets=list(by_zone.values())[:2], Type="application"
    )
    arn: str = response["LoadBalancers"][0]["LoadBalancerArn"]
    return arn


def _attach_target_group(load_balancer_arn: str, name: str) -> str:
    vpc_id = boto3.client("ec2", region_name=REGION).describe_vpcs()["Vpcs"][0]["VpcId"]
    elb = boto3.client("elbv2", region_name=REGION)
    group_arn: str = elb.create_target_group(
        Name=name, Protocol="HTTP", Port=80, VpcId=vpc_id, TargetType="instance"
    )["TargetGroups"][0]["TargetGroupArn"]
    elb.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": group_arn}],
    )
    return group_arn


def test_fails_for_load_balancer_without_target_groups(make_ctx: ContextFactory) -> None:
    arn = _create_load_balancer("bare")

    findings = list(elb_no_targets.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_fails_when_the_target_group_is_empty(make_ctx: ContextFactory) -> None:
    arn = _create_load_balancer("empty")
    _attach_target_group(arn, "empty-targets")

    findings = list(elb_no_targets.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_passes_when_a_target_is_registered(make_ctx: ContextFactory) -> None:
    arn = _create_load_balancer("busy")
    group_arn = _attach_target_group(arn, "busy-targets")
    boto3.client("elbv2", region_name=REGION).register_targets(
        TargetGroupArn=group_arn, Targets=[{"Id": launch_instance()}]
    )

    findings = list(elb_no_targets.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]
