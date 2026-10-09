"""Build the demo dataset by running the real scanner against a mocked account.

    python sample-data/generate_demo.py

moto stands in for AWS, so this needs no credentials and costs nothing. The
script creates a small fictional company's resources, some configured well
and some badly, scans them, and writes sample-data/demo-findings.json.

The real account behind this project only has a handful of resources (see
findings.json next to this file). The demo account exists so the dashboard
can show every check, including the ones that would cost money to trigger
for real, such as RDS instances and load balancers.
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Must be set before moto is imported. moto otherwise seeds hundreds of
# public AMIs and their snapshots into the mocked account.
os.environ["MOTO_EC2_LOAD_DEFAULT_AMIS"] = "false"
os.environ.update(
    AWS_ACCESS_KEY_ID="testing",
    AWS_SECRET_ACCESS_KEY="testing",
    AWS_SESSION_TOKEN="testing",
    AWS_DEFAULT_REGION="us-east-1",
)
os.environ.pop("AWS_PROFILE", None)

import boto3  # noqa: E402
from moto import mock_aws  # noqa: E402
from moto.ec2 import ec2_backends  # noqa: E402
from moto.iam import iam_backends  # noqa: E402

from scanner.engine import run_scan  # noqa: E402

MOTO_ACCOUNT_ID = "123456789012"
DEMO_ACCOUNT_ID = "000000000000"
REGIONS = ["eu-west-1", "us-east-1", "us-west-2"]
PRIMARY = "us-east-1"
IMAGE_ID = "ami-0abcdef1234567890"
OUTPUT = Path(__file__).parent / "demo-findings.json"

ALL_BLOCKED = {
    "BlockPublicAcls": True,
    "IgnorePublicAcls": True,
    "BlockPublicPolicy": True,
    "RestrictPublicBuckets": True,
}


def days_ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def client(service: str, region: str = PRIMARY) -> Any:
    return boto3.client(service, region_name=region)


def launch_instance(region: str = PRIMARY) -> str:
    reservation = client("ec2", region).run_instances(
        ImageId=IMAGE_ID, InstanceType="t3.micro", MinCount=1, MaxCount=1
    )
    instance_id: str = reservation["Instances"][0]["InstanceId"]
    return instance_id


def build_iam() -> None:
    iam = client("iam")

    def console_user(name: str, mfa: bool) -> None:
        iam.create_user(UserName=name)
        iam.create_login_profile(UserName=name, Password="Not-a-real-password-1!")
        if mfa:
            device = iam.create_virtual_mfa_device(VirtualMFADeviceName=f"{name}-mfa")
            iam.enable_mfa_device(
                UserName=name,
                SerialNumber=device["VirtualMFADevice"]["SerialNumber"],
                AuthenticationCode1="123456",
                AuthenticationCode2="654321",
            )

    def key_user(name: str, key_age_days: int) -> None:
        iam.create_user(UserName=name)
        iam.create_access_key(UserName=name)
        # moto stamps keys with the current time; reach into its store to
        # backdate one, which the public API has no way to do.
        user = iam_backends[MOTO_ACCOUNT_ID]["global"].users[name]
        user.access_keys[0].create_date = days_ago(key_age_days)

    console_user("amara.okafor", mfa=True)
    console_user("daniel.reyes", mfa=True)
    console_user("contractor-temp", mfa=False)
    key_user("deploy-bot", key_age_days=412)
    key_user("metrics-exporter", key_age_days=131)
    key_user("ci-runner", key_age_days=18)

    def policy(name: str, statement: dict[str, Any]) -> None:
        document = {"Version": "2012-10-17", "Statement": [statement]}
        iam.create_policy(PolicyName=name, PolicyDocument=json.dumps(document))

    policy("legacy-admin", {"Effect": "Allow", "Action": "*", "Resource": "*"})
    policy(
        "read-build-artifacts",
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": ["arn:aws:s3:::northwind-artifacts", "arn:aws:s3:::northwind-artifacts/*"],
        },
    )
    policy(
        "billing-read-only",
        {"Effect": "Allow", "Action": ["ce:Get*", "budgets:View*"], "Resource": "*"},
    )


def build_s3() -> None:
    def bucket(name: str, region: str, blocked: bool, versioned: bool) -> None:
        s3 = client("s3", region)
        if region == "us-east-1":
            s3.create_bucket(Bucket=name)
        else:
            s3.create_bucket(
                Bucket=name, CreateBucketConfiguration={"LocationConstraint": region}
            )
        if blocked:
            s3.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration=ALL_BLOCKED)
        if versioned:
            s3.put_bucket_versioning(
                Bucket=name, VersioningConfiguration={"Status": "Enabled"}
            )

    bucket("northwind-marketing-site", "us-east-1", blocked=False, versioned=False)
    bucket("northwind-customer-exports", "us-east-1", blocked=False, versioned=True)
    bucket("northwind-artifacts", "us-east-1", blocked=True, versioned=False)
    bucket("northwind-data-lake", "us-west-2", blocked=True, versioned=True)
    bucket("northwind-backups-eu", "eu-west-1", blocked=True, versioned=True)
    bucket("northwind-audit-logs", "us-east-1", blocked=True, versioned=True)


def build_network_and_compute() -> None:
    def security_group(region: str, name: str, port: int, cidr: str) -> None:
        ec2 = client("ec2", region)
        group_id = ec2.create_security_group(GroupName=name, Description=name)["GroupId"]
        ec2.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": port,
                    "ToPort": port,
                    "IpRanges": [{"CidrIp": cidr}],
                }
            ],
        )

    security_group("us-east-1", "bastion-legacy", 22, "0.0.0.0/0")
    security_group("us-east-1", "web-public", 443, "0.0.0.0/0")
    security_group("us-east-1", "db-internal", 5432, "10.0.0.0/16")
    security_group("eu-west-1", "windows-jump-host", 3389, "0.0.0.0/0")
    security_group("us-west-2", "office-ssh", 22, "203.0.113.0/24")

    client("ec2", "us-east-1").enable_ebs_encryption_by_default()
    client("guardduty", "us-east-1").create_detector(Enable=True)

    # A trail that only covers one region, so the multi-region check fails.
    client("cloudtrail").create_trail(
        Name="northwind-us-east-1-only", S3BucketName="northwind-audit-logs"
    )
    client("cloudtrail").start_logging(Name="northwind-us-east-1-only")

    ec2 = client("ec2")
    web_instance = launch_instance()

    def volume(size: int, volume_type: str, attach_to: str | None = None) -> str:
        volume_id: str = ec2.create_volume(
            Size=size, AvailabilityZone="us-east-1a", VolumeType=volume_type
        )["VolumeId"]
        if attach_to:
            ec2.attach_volume(VolumeId=volume_id, InstanceId=attach_to, Device="/dev/sdf")
        return volume_id

    data_volume = volume(200, "gp3", attach_to=web_instance)
    volume(500, "gp2")
    volume(100, "gp2")
    volume(50, "gp3")

    def snapshot(volume_id: str, age_days: int) -> None:
        snapshot_id = ec2.create_snapshot(VolumeId=volume_id)["SnapshotId"]
        stored = ec2_backends[MOTO_ACCOUNT_ID][PRIMARY].snapshots[snapshot_id]
        stored.start_time = days_ago(age_days)

    snapshot(data_volume, age_days=3)
    snapshot(data_volume, age_days=198)
    snapshot(data_volume, age_days=540)

    in_use = ec2.allocate_address(Domain="vpc")["AllocationId"]
    ec2.associate_address(AllocationId=in_use, InstanceId=web_instance)
    ec2.allocate_address(Domain="vpc")
    client("ec2", "us-west-2").allocate_address(Domain="vpc")

    autoscaling = client("autoscaling")
    autoscaling.create_launch_configuration(
        LaunchConfigurationName="web", ImageId=IMAGE_ID, InstanceType="t3.micro"
    )
    for name, zones in (
        ("web-asg", ["us-east-1a", "us-east-1b", "us-east-1c"]),
        ("worker-asg", ["us-east-1a"]),
    ):
        autoscaling.create_auto_scaling_group(
            AutoScalingGroupName=name,
            LaunchConfigurationName="web",
            MinSize=0,
            MaxSize=0,
            AvailabilityZones=zones,
        )

    build_load_balancers(web_instance)


def build_load_balancers(instance_id: str) -> None:
    ec2 = client("ec2")
    elb = client("elbv2")
    vpc_id = ec2.describe_vpcs()["Vpcs"][0]["VpcId"]
    by_zone = {s["AvailabilityZone"]: s["SubnetId"] for s in ec2.describe_subnets()["Subnets"]}
    subnets = list(by_zone.values())[:2]

    def load_balancer(name: str, register_target: bool) -> None:
        arn = elb.create_load_balancer(Name=name, Subnets=subnets, Type="application")[
            "LoadBalancers"
        ][0]["LoadBalancerArn"]
        group_arn = elb.create_target_group(
            Name=f"{name}-targets", Protocol="HTTP", Port=80, VpcId=vpc_id, TargetType="instance"
        )["TargetGroups"][0]["TargetGroupArn"]
        elb.create_listener(
            LoadBalancerArn=arn,
            Protocol="HTTP",
            Port=80,
            DefaultActions=[{"Type": "forward", "TargetGroupArn": group_arn}],
        )
        if register_target:
            elb.register_targets(TargetGroupArn=group_arn, Targets=[{"Id": instance_id}])

    load_balancer("web-prod", register_target=True)
    load_balancer("api-v1-retired", register_target=False)


def build_data_stores() -> None:
    def database(region: str, name: str, public: bool, multi_az: bool, backup_days: int) -> None:
        client("rds", region).create_db_instance(
            DBInstanceIdentifier=name,
            DBInstanceClass="db.t3.medium",
            Engine="postgres",
            MasterUsername="northwind",
            MasterUserPassword="not-a-real-password",
            AllocatedStorage=50,
            PubliclyAccessible=public,
            MultiAZ=multi_az,
            BackupRetentionPeriod=backup_days,
        )

    database("us-east-1", "orders-prod", public=False, multi_az=True, backup_days=14)
    database("us-east-1", "analytics-dev", public=True, multi_az=False, backup_days=0)
    database("eu-west-1", "reporting-eu", public=False, multi_az=False, backup_days=7)

    dynamodb = client("dynamodb")
    for name, recovery in (("orders", True), ("sessions", False), ("feature-flags", False)):
        dynamodb.create_table(
            TableName=name,
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        if recovery:
            dynamodb.update_continuous_backups(
                TableName=name,
                PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
            )


def build_serverless() -> None:
    trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    role_arn = client("iam").create_role(
        RoleName="lambda-basic", AssumeRolePolicyDocument=json.dumps(trust)
    )["Role"]["Arn"]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("handler.py", "def handler(event, context):\n    return None\n")

    # moto does not model dead-letter config, so every demo function fails
    # that check. The pass case is covered by the unit tests.
    for name in ("image-thumbnailer", "nightly-export"):
        client("lambda").create_function(
            FunctionName=name,
            Runtime="python3.12",
            Role=role_arn,
            Handler="handler.handler",
            Code={"ZipFile": buffer.getvalue()},
        )

    logs = client("logs")
    for name, retention in (
        ("/aws/lambda/image-thumbnailer", None),
        ("/aws/lambda/nightly-export", 30),
        ("/northwind/api/access", None),
        ("/northwind/api/application", 90),
    ):
        logs.create_log_group(logGroupName=name)
        if retention:
            logs.put_retention_policy(logGroupName=name, retentionInDays=retention)


def main() -> None:
    with mock_aws():
        build_iam()
        build_s3()
        build_network_and_compute()
        build_data_stores()
        build_serverless()
        result = run_scan(boto3.Session(region_name=PRIMARY), regions=REGIONS)

    text = json.dumps(result.to_dict(), indent=2).replace(MOTO_ACCOUNT_ID, DEMO_ACCOUNT_ID)
    OUTPUT.write_text(text + "\n", encoding="utf-8")
    failed = sum(finding.status == "fail" for finding in result.findings)
    print(f"Wrote {len(result.findings)} findings ({failed} failing) to {OUTPUT}")


if __name__ == "__main__":
    main()
