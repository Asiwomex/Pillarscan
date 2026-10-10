"""AWS accounts that signed-in users have connected, in the scans table.

    PK = USER#<user id>   SK = ACCOUNT#<aws account id>

Each connection has its own external ID and its own role name, both made
up here and never chosen by the user. The external ID is what stops one
user pointing the scanner at a role in somebody else's account: that role
would only accept the ID that Pillarscan generated for its real owner.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from scanner.findings import format_timestamp

AUDIT_ROLE_NAME = "PillarscanAuditRole"
MAX_ACCOUNTS_PER_USER = 5
MIN_TIME_BETWEEN_SCANS = timedelta(minutes=2)


class TooManyAccounts(Exception):
    """The user has reached the limit of connected accounts."""


class ScanRequestedTooSoon(Exception):
    """A scan of this account was requested moments ago."""


def tenant_key(user_id: str, aws_account_id: str) -> str:
    """Key under which one user's scans of one account are stored.

    Scans are filed per user and account, never by account alone, so two
    users who connect the same account cannot see each other's results.
    """
    return f"{user_id}:{aws_account_id}"


def _now() -> str:
    return format_timestamp(datetime.now(timezone.utc))


class AccountStore:
    def __init__(self, table: Any) -> None:
        self._table = table

    @classmethod
    def from_env(cls) -> AccountStore:
        return cls(boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"]))

    @staticmethod
    def _key(user_id: str, aws_account_id: str) -> dict[str, str]:
        return {"PK": f"USER#{user_id}", "SK": f"ACCOUNT#{aws_account_id}"}

    def list(self, user_id: str) -> list[dict[str, Any]]:
        accounts: list[dict[str, Any]] = []
        query: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(f"USER#{user_id}")
            & Key("SK").begins_with("ACCOUNT#")
        }
        while True:
            page = self._table.query(**query)
            accounts.extend(page["Items"])
            if "LastEvaluatedKey" not in page:
                return accounts
            query["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    def get(self, user_id: str, aws_account_id: str) -> dict[str, Any] | None:
        response = self._table.get_item(Key=self._key(user_id, aws_account_id))
        item: dict[str, Any] | None = response.get("Item")
        return item

    def connect(self, user_id: str, aws_account_id: str) -> dict[str, Any]:
        """Start connecting an account. Safe to call again for the same one."""
        existing = self.get(user_id, aws_account_id)
        if existing:
            return existing
        if len(self.list(user_id)) >= MAX_ACCOUNTS_PER_USER:
            raise TooManyAccounts

        # The suffix keeps this role apart from any other Pillarscan role
        # already in the account, including one made by another user.
        suffix = secrets.token_hex(4)
        account = {
            **self._key(user_id, aws_account_id),
            "aws_account_id": aws_account_id,
            "role_name_suffix": f"-{suffix}",
            "role_arn": f"arn:aws:iam::{aws_account_id}:role/{AUDIT_ROLE_NAME}-{suffix}",
            "external_id": secrets.token_urlsafe(32),
            "status": "pending",
            "created_at": _now(),
        }
        try:
            # The condition makes two simultaneous requests agree on one
            # external ID instead of the second overwriting the first.
            self._table.put_item(
                Item=account, ConditionExpression=Attr("PK").not_exists()
            )
        except ClientError as error:
            if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            existing = self.get(user_id, aws_account_id)
            assert existing is not None
            return existing
        return account

    def mark_scan_requested(self, user_id: str, aws_account_id: str) -> None:
        """Record a scan request, refusing one that follows too closely."""
        now = datetime.now(timezone.utc)
        earliest_previous = format_timestamp(now - MIN_TIME_BETWEEN_SCANS)
        try:
            self._table.update_item(
                Key=self._key(user_id, aws_account_id),
                UpdateExpression="SET last_requested_at = :now",
                # Timestamps in this format compare correctly as text.
                ConditionExpression=Attr("PK").exists()
                & (
                    Attr("last_requested_at").not_exists()
                    | Attr("last_requested_at").lt(earliest_previous)
                ),
                ExpressionAttributeValues={":now": format_timestamp(now)},
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ScanRequestedTooSoon from error
            raise

    def record_scan(self, user_id: str, aws_account_id: str, scan_id: str) -> None:
        self._table.update_item(
            Key=self._key(user_id, aws_account_id),
            UpdateExpression=(
                "SET #status = :connected, last_scan_id = :scan_id, last_scanned_at = :now "
                "REMOVE last_error"
            ),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":connected": "connected",
                ":scan_id": scan_id,
                ":now": _now(),
            },
        )

    def record_failure(self, user_id: str, aws_account_id: str, message: str) -> None:
        self._table.update_item(
            Key=self._key(user_id, aws_account_id),
            UpdateExpression="SET #status = :error, last_error = :message",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":error": "error", ":message": message},
        )
