"""Lambda functions that can lose failed asynchronous events."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

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
        "or an on-failure destination, and alarm on messages arriving there."
    ),
)

# Services that call a function and wait for its answer. A failure goes
# straight back to the caller, so there is no event to lose.
SYNCHRONOUS_CALLERS = {
    "apigateway.amazonaws.com",
    "elasticloadbalancing.amazonaws.com",
    "cognito-idp.amazonaws.com",
    "lex.amazonaws.com",
    "alexa-appkit.amazon.com",
}


def _has_failure_target(lambda_client: Any, function: dict[str, Any]) -> bool:
    if function.get("DeadLetterConfig", {}).get("TargetArn"):
        return True
    # An on-failure destination is the newer way to do the same job.
    pages = lambda_client.get_paginator("list_function_event_invoke_configs").paginate(
        FunctionName=function["FunctionName"]
    )
    return any(
        config.get("DestinationConfig", {}).get("OnFailure", {}).get("Destination")
        for page in pages
        for config in page["FunctionEventInvokeConfigs"]
    )


def _reads_from_a_source(lambda_client: Any, function_name: str) -> bool:
    """True if Lambda polls a queue or stream for this function.

    Failures are then handled by the source, for example an SQS redrive
    policy, and the function's own dead-letter queue is never used.
    """
    pages = lambda_client.get_paginator("list_event_source_mappings").paginate(
        FunctionName=function_name
    )
    return any(page["EventSourceMappings"] for page in pages)


def _service_callers(lambda_client: Any, function_name: str) -> set[str]:
    """AWS services the function's resource policy allows to invoke it."""
    try:
        policy = json.loads(lambda_client.get_policy(FunctionName=function_name)["Policy"])
    except lambda_client.exceptions.ResourceNotFoundException:
        return set()  # no resource policy at all
    callers: set[str] = set()
    for statement in policy.get("Statement", []):
        principal = statement.get("Principal", {})
        services = principal.get("Service", []) if isinstance(principal, dict) else []
        callers.update([services] if isinstance(services, str) else services)
    return callers


def run(ctx: CheckContext) -> Iterable[Finding]:
    lambda_client = ctx.client("lambda")
    for page in lambda_client.get_paginator("list_functions").paginate():
        for function in page["Functions"]:
            name = function["FunctionName"]
            arn = function["FunctionArn"]

            if _has_failure_target(lambda_client, function):
                yield ctx.finding(
                    META,
                    Status.PASS,
                    arn,
                    f"Function {name} sends failed asynchronous events somewhere they can be seen.",
                )
                continue

            # A dead-letter queue only matters for asynchronous invocations.
            # Leave out functions that are clearly not invoked that way.
            callers = _service_callers(lambda_client, name)
            only_synchronous = bool(callers) and callers <= SYNCHRONOUS_CALLERS
            if only_synchronous or (
                not callers and _reads_from_a_source(lambda_client, name)
            ):
                continue

            yield ctx.finding(
                META,
                Status.FAIL,
                arn,
                f"Function {name} has no dead-letter queue or on-failure "
                "destination. An asynchronous event that still fails after "
                "Lambda's two retries is dropped without a trace.",
            )
