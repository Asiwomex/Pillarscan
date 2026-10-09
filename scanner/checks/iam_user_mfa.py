"""IAM users with a console password but no MFA device."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="iam_user_mfa",
    title="IAM user without MFA",
    pillar=Pillar.SECURITY,
    severity=Severity.HIGH,
    resource_type="AWS::IAM::User",
    scope=Scope.GLOBAL,
    remediation=(
        "Have the user assign an MFA device under IAM > Users > Security "
        "credentials, or remove the console password if they do not need to "
        "sign in. Better still, move people to IAM Identity Center, which "
        "issues short-lived credentials."
    ),
)


def _has_console_password(iam: Any, user_name: str) -> bool:
    try:
        iam.get_login_profile(UserName=user_name)
    except iam.exceptions.NoSuchEntityException:
        return False
    return True


def _has_mfa_device(iam: Any, user_name: str) -> bool:
    pages = iam.get_paginator("list_mfa_devices").paginate(UserName=user_name)
    return any(page["MFADevices"] for page in pages)


def run(ctx: CheckContext) -> Iterable[Finding]:
    iam = ctx.client("iam")
    for page in iam.get_paginator("list_users").paginate():
        for user in page["Users"]:
            name = user["UserName"]
            # MFA protects console sign-in. A user with only access keys has
            # no password to protect, so they are out of scope (as in CIS).
            if not _has_console_password(iam, name):
                continue
            if _has_mfa_device(iam, name):
                yield ctx.finding(
                    META, Status.PASS, user["Arn"], f"User {name} has an MFA device."
                )
            else:
                yield ctx.finding(
                    META,
                    Status.FAIL,
                    user["Arn"],
                    f"User {name} can sign in to the console with a password "
                    "alone. A phished or reused password is then enough to act "
                    "with all of this user's permissions.",
                )
