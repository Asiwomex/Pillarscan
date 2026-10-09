"""Active access keys older than 90 days."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

MAX_KEY_AGE = timedelta(days=90)

META = CheckMeta(
    check_id="iam_access_key_age",
    title="Access key older than 90 days",
    pillar=Pillar.SECURITY,
    severity=Severity.MEDIUM,
    resource_type="AWS::IAM::AccessKey",
    scope=Scope.GLOBAL,
    remediation=(
        "Create a new key, switch the workload to it, deactivate the old key, "
        "and delete it once nothing breaks. Where possible replace the key "
        "with short-lived credentials: an IAM role for workloads, or "
        "`aws login` / IAM Identity Center for people."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    iam = ctx.client("iam")
    for user_page in iam.get_paginator("list_users").paginate():
        for user in user_page["Users"]:
            name = user["UserName"]
            key_pages = iam.get_paginator("list_access_keys").paginate(UserName=name)
            for key_page in key_pages:
                for key in key_page["AccessKeyMetadata"]:
                    # An inactive key cannot sign requests, so its age is not a risk.
                    if key["Status"] != "Active":
                        continue
                    # Access keys have no ARN of their own, so the finding
                    # points at the owning user and names the key by its tail.
                    label = f"Access key ending {key['AccessKeyId'][-4:]} of user {name}"
                    age = ctx.now - key["CreateDate"]
                    if age > MAX_KEY_AGE:
                        yield ctx.finding(
                            META,
                            Status.FAIL,
                            user["Arn"],
                            f"{label} is {age.days} days old. Long-lived keys "
                            "end up in shell history, CI logs and old laptops; "
                            "the longer one lives, the more places it can leak from.",
                        )
                    else:
                        yield ctx.finding(
                            META,
                            Status.PASS,
                            user["Arn"],
                            f"{label} is {age.days} days old.",
                        )
