from __future__ import annotations

import json
from typing import Any

import boto3
import pytest

from scanner.checks import iam_policy_full_admin
from scanner.checks.iam_policy_full_admin import grants_full_admin
from scanner.findings import Status

from .conftest import ContextFactory
from .helpers import REGION


def _create_policy(name: str, statement: dict[str, Any] | list[dict[str, Any]]) -> str:
    document = {"Version": "2012-10-17", "Statement": statement}
    iam = boto3.client("iam", region_name=REGION)
    arn: str = iam.create_policy(PolicyName=name, PolicyDocument=json.dumps(document))[
        "Policy"
    ]["Arn"]
    return arn


def test_fails_for_policy_allowing_everything(make_ctx: ContextFactory) -> None:
    arn = _create_policy("god-mode", {"Effect": "Allow", "Action": "*", "Resource": "*"})

    findings = list(iam_policy_full_admin.run(make_ctx()))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_passes_for_scoped_policy(make_ctx: ContextFactory) -> None:
    arn = _create_policy(
        "read-one-bucket",
        {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::example/*"},
    )

    findings = list(iam_policy_full_admin.run(make_ctx()))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        ({"Effect": "Allow", "Action": ["s3:Get*", "*"], "Resource": ["*"]}, True),
        ({"Effect": "Allow", "Action": "*:*", "Resource": "*"}, True),
        ({"Effect": "Deny", "Action": "*", "Resource": "*"}, False),
        ({"Effect": "Allow", "Action": "*", "Resource": "arn:aws:s3:::example/*"}, False),
        ({"Effect": "Allow", "Action": "s3:*", "Resource": "*"}, False),
        ({"Effect": "Allow", "NotAction": "iam:*", "Resource": "*"}, False),
    ],
)
def test_statement_shapes(statement: dict[str, Any], expected: bool) -> None:
    assert grants_full_admin({"Statement": statement}) is expected
    assert grants_full_admin({"Statement": [statement]}) is expected
