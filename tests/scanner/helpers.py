"""Resource builders shared by the check tests. Everything here hits moto."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import boto3

from scanner.findings import Finding, Status

REGION = "us-east-1"


def statuses(findings: Iterable[Finding], resource_arn: str) -> list[Status]:
    """Statuses reported for one resource, ignoring moto's default resources."""
    return [f.status for f in findings if f.resource_arn == resource_arn]


def launch_instance() -> str:
    ec2 = boto3.client("ec2", region_name=REGION)
    image_id = ec2.describe_images(Owners=["amazon"])["Images"][0]["ImageId"]
    reservation = ec2.run_instances(
        ImageId=image_id, InstanceType="t3.micro", MinCount=1, MaxCount=1
    )
    instance_id: str = reservation["Instances"][0]["InstanceId"]
    return instance_id


def create_db_instance(name: str, **overrides: Any) -> str:
    settings: dict[str, Any] = {
        "DBInstanceIdentifier": name,
        "DBInstanceClass": "db.t3.micro",
        "Engine": "postgres",
        "MasterUsername": "pillarscan",
        "MasterUserPassword": "not-a-real-password",
        "AllocatedStorage": 20,
        "PubliclyAccessible": False,
        "MultiAZ": False,
        "BackupRetentionPeriod": 7,
    }
    settings.update(overrides)
    rds = boto3.client("rds", region_name=REGION)
    arn: str = rds.create_db_instance(**settings)["DBInstance"]["DBInstanceArn"]
    return arn
