from __future__ import annotations

import boto3

from scanner.checks import dynamodb_pitr
from scanner.findings import Status

from .conftest import MOTO_ACCOUNT_ID, ContextFactory
from .helpers import REGION


def _create_table(name: str, recovery: bool) -> str:
    dynamodb = boto3.client("dynamodb", region_name=REGION)
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
    return f"arn:aws:dynamodb:{REGION}:{MOTO_ACCOUNT_ID}:table/{name}"


def test_fails_without_point_in_time_recovery(make_ctx: ContextFactory) -> None:
    arn = _create_table("orders", recovery=False)

    findings = list(dynamodb_pitr.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_passes_with_point_in_time_recovery(make_ctx: ContextFactory) -> None:
    arn = _create_table("payments", recovery=True)

    findings = list(dynamodb_pitr.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]
