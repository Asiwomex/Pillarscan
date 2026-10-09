"""Builds the boto3 session a scan runs with."""

from __future__ import annotations

import boto3

from scanner.check import CLIENT_CONFIG, GLOBAL_ENDPOINT_REGION

ROLE_SESSION_NAME = "pillarscan-scan"


def assume_role_session(
    base: boto3.Session, role_arn: str, external_id: str
) -> boto3.Session:
    """Swap the caller's credentials for the read-only audit role's.

    The external ID guards against the "confused deputy" problem: a role
    that trusts the scanner's account would otherwise let anyone who can
    use the scanner point it at somebody else's role ARN. The role's trust
    policy only accepts the call when the ID matches, so it is required
    here, never optional.
    """
    sts = base.client(
        "sts",
        region_name=base.region_name or GLOBAL_ENDPOINT_REGION,
        config=CLIENT_CONFIG,
    )
    credentials = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=ROLE_SESSION_NAME,
        ExternalId=external_id,
    )["Credentials"]
    # These credentials last an hour and are not refreshed. A scan takes
    # about a minute, so that is plenty.
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=base.region_name,
    )
