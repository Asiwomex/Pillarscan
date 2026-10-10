"""Scanner Lambda: run the scans requested on the queue and store them.

There are two kinds of request:

    {}                                        scan the platform's own account
                                              and store it scrubbed, for the
                                              public dashboard
    {"user_id": ..., "aws_account_id": ...}   scan an account a signed-in
                                              user connected, and store it
                                              for that user only

Either way the function's own role can do almost nothing in AWS. It assumes
a read-only audit role in the account to scan and uses that.

Environment:
    TABLE_NAME             DynamoDB table for scans and connected accounts
    AUDIT_ROLE_ARN         audit role in the platform's own account
    EXTERNAL_ID_PARAMETER  SSM parameter holding that role's external ID
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from scanner.accounts import AccountStore, tenant_key
from scanner.engine import run_scan
from scanner.scrub import scrub
from scanner.session import assume_role_session
from scanner.store import ScanStore

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COULD_NOT_ASSUME = (
    "Pillarscan could not assume the role in this account. Check that the "
    "CloudFormation stack finished creating and was made from the link on "
    "this page."
)
WRONG_ACCOUNT = "The role belongs to a different AWS account from the one entered."


def _own_external_id() -> str:
    # Read at run time rather than kept in an environment variable, where
    # anyone who can view the function's configuration could read it.
    parameter = boto3.client("ssm").get_parameter(
        Name=os.environ["EXTERNAL_ID_PARAMETER"], WithDecryption=True
    )
    value: str = parameter["Parameter"]["Value"]
    return value


def scan_own_account() -> dict[str, Any]:
    session = assume_role_session(
        boto3.Session(), os.environ["AUDIT_ROLE_ARN"], _own_external_id()
    )
    # The API serves these scans without sign-in, so the account ID, user
    # names and resource IDs are replaced before anything is stored.
    report = scrub(run_scan(session).to_dict())
    scan_id = ScanStore.from_env().put_scan(report)
    logger.info("stored public scan %s with %d findings", scan_id, len(report["findings"]))
    return {"scan_id": scan_id, "findings": len(report["findings"])}


def scan_connected_account(user_id: str, aws_account_id: str) -> dict[str, Any]:
    accounts = AccountStore.from_env()
    account = accounts.get(user_id, aws_account_id)
    if account is None:
        # The account was removed after the scan was requested.
        logger.warning("no connected account %s for this user", aws_account_id)
        return {"skipped": aws_account_id}

    try:
        session = assume_role_session(
            boto3.Session(), account["role_arn"], account["external_id"]
        )
    except ClientError as error:
        # Retrying will not help: the role is missing or does not trust us.
        # Record why, so the user sees it, and let the message go.
        logger.info("cannot assume role: %s", error.response["Error"]["Code"])
        accounts.record_failure(user_id, aws_account_id, COULD_NOT_ASSUME)
        return {"failed": aws_account_id}

    report = run_scan(session).to_dict()
    if report["scan"]["account_id"] != aws_account_id:
        accounts.record_failure(user_id, aws_account_id, WRONG_ACCOUNT)
        return {"failed": aws_account_id}

    scan_id = ScanStore.from_env().put_scan(report, owner=tenant_key(user_id, aws_account_id))
    accounts.record_scan(user_id, aws_account_id, scan_id)
    logger.info("stored private scan %s with %d findings", scan_id, len(report["findings"]))
    return {"scan_id": scan_id, "findings": len(report["findings"])}


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    requests = [json.loads(record["body"] or "{}") for record in event.get("Records", [])]
    results: list[dict[str, Any]] = []
    scanned_own_account = False
    # An event with no records (a manual test invoke) means one public scan.
    for request in requests or [{}]:
        if "user_id" in request:
            results.append(
                scan_connected_account(request["user_id"], request["aws_account_id"])
            )
        elif not scanned_own_account:
            # Two public requests close together should not produce two
            # identical scans.
            scanned_own_account = True
            results.append(scan_own_account())
    # If anything above raises, the message goes back on the queue and, after
    # a second failure, to the dead-letter queue.
    return {"scans": results}
