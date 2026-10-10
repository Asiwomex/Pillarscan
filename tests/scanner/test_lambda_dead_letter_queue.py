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


def _queue_arn(name: str) -> str:
    sqs = boto3.client("sqs", region_name=REGION)
    url = sqs.create_queue(QueueName=name)["QueueUrl"]
    arn: str = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])[
        "Attributes"
    ]["QueueArn"]
    return arn


def _allow_service(function_name: str, service: str) -> None:
    boto3.client("lambda", region_name=REGION).add_permission(
        FunctionName=function_name,
        StatementId=service.split(".")[0],
        Action="lambda:InvokeFunction",
        Principal=service,
    )


def test_passes_with_an_on_failure_destination(make_ctx: ContextFactory) -> None:
    arn = _create_function("with-destination")
    boto3.client("lambda", region_name=REGION).put_function_event_invoke_config(
        FunctionName="with-destination",
        DestinationConfig={"OnFailure": {"Destination": _queue_arn("failures")}},
    )

    findings = list(lambda_dead_letter_queue.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]


def test_fails_for_a_function_invoked_by_an_asynchronous_service(
    make_ctx: ContextFactory,
) -> None:
    arn = _create_function("on-upload")
    _allow_service("on-upload", "s3.amazonaws.com")

    findings = list(lambda_dead_letter_queue.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_leaves_out_a_function_only_called_synchronously(make_ctx: ContextFactory) -> None:
    _create_function("behind-api")
    _allow_service("behind-api", "apigateway.amazonaws.com")

    assert list(lambda_dead_letter_queue.run(make_ctx(region=REGION))) == []


def test_still_checks_a_function_with_both_kinds_of_caller(make_ctx: ContextFactory) -> None:
    arn = _create_function("mixed")
    _allow_service("mixed", "apigateway.amazonaws.com")
    _allow_service("mixed", "sns.amazonaws.com")

    findings = list(lambda_dead_letter_queue.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_leaves_out_a_function_that_reads_from_a_queue(make_ctx: ContextFactory) -> None:
    _create_function("queue-worker")
    boto3.client("lambda", region_name=REGION).create_event_source_mapping(
        EventSourceArn=_queue_arn("work"), FunctionName="queue-worker"
    )

    assert list(lambda_dead_letter_queue.run(make_ctx(region=REGION))) == []
