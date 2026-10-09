"""Lambda functions without a dead-letter queue."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="lambda_dead_letter_queue",
    title="Lambda function without a dead-letter queue",
    pillar=Pillar.RELIABILITY,
    severity=Severity.LOW,
    resource_type="AWS::Lambda::Function",
    scope=Scope.REGIONAL,
    remediation=(
        "Add an SQS queue or SNS topic as the function's dead-letter queue, "
        "or an on-failure destination, and alarm on messages arriving "
        "there. This matters for functions invoked asynchronously (S3, SNS, "
        "EventBridge); functions behind API Gateway or reading from SQS "
        "handle failures differently and can ignore this finding."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    lambda_client = ctx.client("lambda")
    for page in lambda_client.get_paginator("list_functions").paginate():
        for function in page["Functions"]:
            name = function["FunctionName"]
            if function.get("DeadLetterConfig", {}).get("TargetArn"):
                yield ctx.finding(
                    META,
                    Status.PASS,
                    function["FunctionArn"],
                    f"Function {name} has a dead-letter queue.",
                )
            else:
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    function["FunctionArn"],
                    f"Function {name} has no dead-letter queue. An "
                    "asynchronous event that still fails after Lambda's two "
                    "retries is dropped without a trace.",
                )
