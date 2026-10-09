from __future__ import annotations

import io
import json
import zipfile
from typing import Any

import boto3
import pytest
from botocore.stub import Stubber

from scanner.check import CheckContext
from scanner.checks import lambda_dead_letter_queue
from scanner.findings import Status

from .conftest import MOTO_ACCOUNT_ID, ContextFactory
from .helpers import REGION

TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}


def _zipped_handler() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("handler.py", "def handler(event, context):\n    return None\n")
    return buffer.getvalue()


def _create_function(name: str, dead_letter_arn: str | None = None) -> str:
    role_arn = boto3.client("iam", region_name=REGION).create_role(
        RoleName=f"{name}-role", AssumeRolePolicyDocument=json.dumps(TRUST_POLICY)
    )["Role"]["Arn"]
    settings: dict[str, Any] = {
        "FunctionName": name,
        "Runtime": "python3.12",
        "Role": role_arn,
        "Handler": "handler.handler",
        "Code": {"ZipFile": _zipped_handler()},
    }
    if dead_letter_arn:
        settings["DeadLetterConfig"] = {"TargetArn": dead_letter_arn}
    arn: str = boto3.client("lambda", region_name=REGION).create_function(**settings)[
        "FunctionArn"
    ]
    return arn


def test_fails_without_a_dead_letter_queue(make_ctx: ContextFactory) -> None:
    arn = _create_function("no-dlq")

    findings = list(lambda_dead_letter_queue.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_passes_with_a_dead_letter_queue(
    make_ctx: ContextFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    # moto does not model DeadLetterConfig, so stub the listing instead.
    arn = f"arn:aws:lambda:{REGION}:{MOTO_ACCOUNT_ID}:function:with-dlq"
    queue_arn = f"arn:aws:sqs:{REGION}:{MOTO_ACCOUNT_ID}:failures"
    lambda_client = boto3.client("lambda", region_name=REGION)
    monkeypatch.setattr(CheckContext, "client", lambda self, service: lambda_client)
    with Stubber(lambda_client) as stubber:
        stubber.add_response(
            "list_functions",
            {
                "Functions": [
                    {
                        "FunctionName": "with-dlq",
                        "FunctionArn": arn,
                        "DeadLetterConfig": {"TargetArn": queue_arn},
                    }
                ]
            },
        )
        findings = list(lambda_dead_letter_queue.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]
