from __future__ import annotations

import boto3

from scanner.checks import iam_user_mfa
from scanner.findings import Status

from .conftest import ContextFactory

PASSWORD = "Not-a-real-password-1!"


def _create_console_user(name: str) -> str:
    iam = boto3.client("iam", region_name="us-east-1")
    arn: str = iam.create_user(UserName=name)["User"]["Arn"]
    iam.create_login_profile(UserName=name, Password=PASSWORD)
    return arn


def _attach_mfa(name: str) -> None:
    iam = boto3.client("iam", region_name="us-east-1")
    device = iam.create_virtual_mfa_device(VirtualMFADeviceName=f"{name}-mfa")
    iam.enable_mfa_device(
        UserName=name,
        SerialNumber=device["VirtualMFADevice"]["SerialNumber"],
        AuthenticationCode1="123456",
        AuthenticationCode2="654321",
    )


def test_fails_for_console_user_without_mfa(make_ctx: ContextFactory) -> None:
    arn = _create_console_user("alice")

    findings = list(iam_user_mfa.run(make_ctx()))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_passes_for_console_user_with_mfa(make_ctx: ContextFactory) -> None:
    arn = _create_console_user("bob")
    _attach_mfa("bob")

    findings = list(iam_user_mfa.run(make_ctx()))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]


def test_ignores_users_without_a_console_password(make_ctx: ContextFactory) -> None:
    boto3.client("iam", region_name="us-east-1").create_user(UserName="ci-bot")

    assert list(iam_user_mfa.run(make_ctx())) == []


def test_reports_every_user_across_pages(make_ctx: ContextFactory) -> None:
    # More users than one list_users page holds (the default page size is 100).
    for index in range(105):
        _create_console_user(f"user-{index:03d}")

    findings = list(iam_user_mfa.run(make_ctx()))

    assert len(findings) == 105
    assert all(finding.status is Status.FAIL for finding in findings)
