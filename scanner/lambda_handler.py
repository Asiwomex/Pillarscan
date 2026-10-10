"""Scanner Lambda: run one scan and store it.

Triggered by a message on the scan queue. The function's own role can do
almost nothing in AWS. It assumes the read-only audit role, the same way it
would to scan somebody else's account, and scans with that.

Environment:
    TABLE_NAME             DynamoDB table to store the scan in
    AUDIT_ROLE_ARN         read-only role to assume in the account to scan
    EXTERNAL_ID_PARAMETER  SSM parameter holding the role's external ID
    SCRUB_OUTPUT           "true" to replace account and resource IDs before
                           storing, for scans that are shown publicly
"""

from __future__ import annotations

import logging
import os
from typing import Any

import boto3

from scanner.engine import run_scan
from scanner.scrub import scrub
from scanner.session import assume_role_session
from scanner.store import ScanStore

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _external_id() -> str:
    # Read at run time rather than kept in an environment variable, where
    # anyone who can view the function's configuration could read it.
    parameter = boto3.client("ssm").get_parameter(
        Name=os.environ["EXTERNAL_ID_PARAMETER"], WithDecryption=True
    )
    value: str = parameter["Parameter"]["Value"]
    return value


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    # One scan per invocation, however many messages arrived: two requests
    # close together should not produce two identical scans.
    session = assume_role_session(
        boto3.Session(), os.environ["AUDIT_ROLE_ARN"], _external_id()
    )
    report = run_scan(session).to_dict()
    if os.environ.get("SCRUB_OUTPUT", "").lower() == "true":
        report = scrub(report)

    scan_id = ScanStore.from_env().put_scan(report)
    logger.info("stored scan %s with %d findings", scan_id, len(report["findings"]))
    # If anything above raises, the message goes back on the queue and, after
    # a second failure, to the dead-letter queue.
    return {"scan_id": scan_id, "findings": len(report["findings"])}
