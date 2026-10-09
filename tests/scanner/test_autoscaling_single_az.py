from __future__ import annotations

import boto3

from scanner.checks import autoscaling_single_az
from scanner.findings import Status

from .conftest import ContextFactory
from .helpers import REGION


def _create_group(name: str, zones: list[str]) -> str:
    image_id = boto3.client("ec2", region_name=REGION).describe_images(Owners=["amazon"])[
        "Images"
    ][0]["ImageId"]
    autoscaling = boto3.client("autoscaling", region_name=REGION)
    autoscaling.create_launch_configuration(
        LaunchConfigurationName=f"{name}-config", ImageId=image_id, InstanceType="t3.micro"
    )
    autoscaling.create_auto_scaling_group(
        AutoScalingGroupName=name,
        LaunchConfigurationName=f"{name}-config",
        MinSize=0,
        MaxSize=0,
        AvailabilityZones=zones,
    )
    groups = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[name])
    arn: str = groups["AutoScalingGroups"][0]["AutoScalingGroupARN"]
    return arn


def test_fails_for_group_in_one_zone(make_ctx: ContextFactory) -> None:
    arn = _create_group("lonely", ["us-east-1a"])

    findings = list(autoscaling_single_az.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]
    assert "us-east-1a" in findings[0].description


def test_passes_for_group_across_zones(make_ctx: ContextFactory) -> None:
    arn = _create_group("spread", ["us-east-1a", "us-east-1b"])

    findings = list(autoscaling_single_az.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]
