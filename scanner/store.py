"""Scans stored in DynamoDB, in one table.

Two kinds of item share the table:

    PK = ACCOUNT#<account_id>   SK = SCAN#<scan_id>        one summary per scan
    PK = SCAN#<scan_id>         SK = FINDING#<00042>       one item per finding

Scan IDs are the scan's start time (20261009T221200Z), so they sort by
time. That makes "the latest scans for an account" a single query on the
first key, newest first, and "every finding of a scan" a single query on
the second. Nothing ever needs a table scan.
"""

from __future__ import annotations

import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from scanner.score import posture_score

RETENTION = timedelta(days=90)
SUMMARY_FIELDS = (
    "scan_id",
    "account_id",
    "started_at",
    "finished_at",
    "regions",
    "checks_run",
    "score",
    "passed",
    "failed",
    "errored",
    "failed_by_severity",
)


def scan_id_for(started_at: str) -> str:
    """2026-10-09T22:12:00Z -> 20261009T221200Z"""
    return started_at.replace("-", "").replace(":", "")


def _plain(value: Any) -> Any:
    """DynamoDB returns every number as a Decimal; turn them back into ints."""
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    return value


def summarise(report: dict[str, Any]) -> dict[str, Any]:
    scan = report["scan"]
    findings = report["findings"]
    by_status = Counter(finding["status"] for finding in findings)
    failed_by_severity = Counter(
        finding["severity"] for finding in findings if finding["status"] == "fail"
    )
    return {
        "scan_id": scan_id_for(scan["started_at"]),
        "account_id": scan["account_id"],
        "started_at": scan["started_at"],
        "finished_at": scan["finished_at"],
        "regions": scan["regions"],
        "checks_run": scan["checks_run"],
        "score": posture_score(findings),
        "passed": by_status["pass"],
        "failed": by_status["fail"],
        "errored": by_status["error"],
        "failed_by_severity": dict(failed_by_severity),
    }


class ScanStore:
    def __init__(self, table: Any) -> None:
        self._table = table

    @classmethod
    def from_env(cls) -> ScanStore:
        return cls(boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"]))

    def put_scan(self, report: dict[str, Any]) -> str:
        """Store a scan report as written by the scanner. Returns its scan ID."""
        summary = summarise(report)
        scan_id: str = summary["scan_id"]
        # DynamoDB deletes items once this time has passed, so the table
        # cannot grow without limit.
        expires_at = int((datetime.now(timezone.utc) + RETENTION).timestamp())

        # batch_writer groups writes into batches of 25 and retries any
        # that DynamoDB could not take the first time.
        with self._table.batch_writer() as batch:
            for index, finding in enumerate(report["findings"]):
                batch.put_item(
                    Item={
                        **finding,
                        "PK": f"SCAN#{scan_id}",
                        "SK": f"FINDING#{index:05d}",
                        "expires_at": expires_at,
                    }
                )
            # The summary goes last: a scan only shows up in the history
            # once all of its findings are there.
            batch.put_item(
                Item={
                    **summary,
                    "PK": f"ACCOUNT#{summary['account_id']}",
                    "SK": f"SCAN#{scan_id}",
                    "expires_at": expires_at,
                }
            )
        return scan_id

    def list_scans(self, account_id: str, limit: int = 30) -> list[dict[str, Any]]:
        """Scan summaries for an account, newest first."""
        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(f"ACCOUNT#{account_id}")
            & Key("SK").begins_with("SCAN#"),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [self._summary(item) for item in response["Items"]]

    def get_scan(self, account_id: str, scan_id: str) -> dict[str, Any] | None:
        """One scan in the shape the scanner writes, or None if it is unknown."""
        if scan_id == "latest":
            latest = self.list_scans(account_id, limit=1)
            if not latest:
                return None
            summary = latest[0]
        else:
            response = self._table.get_item(
                Key={"PK": f"ACCOUNT#{account_id}", "SK": f"SCAN#{scan_id}"}
            )
            if "Item" not in response:
                return None
            summary = self._summary(response["Item"])

        findings: list[dict[str, Any]] = []
        query: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(f"SCAN#{summary['scan_id']}")
        }
        # A query returns at most 1 MB per call; keep going until it is done.
        while True:
            page = self._table.query(**query)
            findings.extend(self._finding(item) for item in page["Items"])
            if "LastEvaluatedKey" not in page:
                break
            query["ExclusiveStartKey"] = page["LastEvaluatedKey"]

        return {"scan": summary, "findings": findings}

    @staticmethod
    def _summary(item: dict[str, Any]) -> dict[str, Any]:
        return {field: _plain(item.get(field)) for field in SUMMARY_FIELDS}

    @staticmethod
    def _finding(item: dict[str, Any]) -> dict[str, Any]:
        storage_only = {"PK", "SK", "expires_at"}
        return {key: _plain(value) for key, value in item.items() if key not in storage_only}
