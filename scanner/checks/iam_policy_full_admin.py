"""Customer managed policies that allow every action on every resource."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

ALL_ACTIONS = {"*", "*:*"}

META = CheckMeta(
    check_id="iam_policy_full_admin",
    title="IAM policy granting * on *",
    pillar=Pillar.SECURITY,
    severity=Severity.HIGH,
    resource_type="AWS::IAM::ManagedPolicy",
    scope=Scope.GLOBAL,
    remediation=(
        "Replace the wildcard statement with the specific actions and "
        "resources the workload uses. IAM Access Analyzer can generate a "
        "policy from CloudTrail activity. Delete the policy if nothing "
        "needs it."
    ),
)


def _as_list(value: Any) -> list[Any]:
    # Policy JSON allows a single value wherever it allows a list.
    return value if isinstance(value, list) else [value]


def grants_full_admin(document: dict[str, Any]) -> bool:
    for statement in _as_list(document.get("Statement", [])):
        if statement.get("Effect") != "Allow":
            continue
        actions = _as_list(statement.get("Action", []))
        resources = _as_list(statement.get("Resource", []))
        if ALL_ACTIONS.intersection(actions) and "*" in resources:
            return True
    return False


def run(ctx: CheckContext) -> Iterable[Finding]:
    iam = ctx.client("iam")
    # Scope=Local skips the AWS managed policies, which the account cannot edit.
    for page in iam.get_paginator("list_policies").paginate(Scope="Local"):
        for policy in page["Policies"]:
            name = policy["PolicyName"]
            version = iam.get_policy_version(
                PolicyArn=policy["Arn"], VersionId=policy["DefaultVersionId"]
            )
            if grants_full_admin(version["PolicyVersion"]["Document"]):
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    policy["Arn"],
                    f"Policy {name} allows every action on every resource and "
                    f"is attached to {policy['AttachmentCount']} identities. "
                    "Whoever holds it can do anything in the account, "
                    "including granting themselves more access.",
                )
            else:
                yield ctx.finding(
                    META,
                    Status.PASS,
                    policy["Arn"],
                    f"Policy {name} does not allow * on *.",
                )
