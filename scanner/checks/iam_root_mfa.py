"""Root account without MFA."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="iam_root_mfa",
    title="Root account without MFA",
    pillar=Pillar.SECURITY,
    severity=Severity.CRITICAL,
    resource_type="AWS::::Account",
    scope=Scope.GLOBAL,
    remediation=(
        "Sign in as the root user, open Security credentials and assign an MFA "
        "device (a passkey or hardware key is best). Then stop using root for "
        "daily work and keep it for the few tasks that require it."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    # The account summary is the only read API that reports root MFA without
    # generating a credential report.
    summary = ctx.client("iam").get_account_summary()["SummaryMap"]
    if summary.get("AccountMFAEnabled") == 1:
        yield ctx.finding(
            META, Status.PASS, ctx.account_arn, "The root user has MFA enabled."
        )
    else:
        yield ctx.finding(
            META,
            Status.FAIL,
            ctx.account_arn,
            "The root user has no MFA device. Root cannot be restricted by IAM "
            "policies, so a stolen root password gives full control of the "
            "account, including billing and closing it.",
        )
