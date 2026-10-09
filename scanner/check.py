"""What a check is made of: its metadata and the context it runs in."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

import boto3
from botocore.config import Config

from scanner.findings import Finding, Pillar, Severity, Status, format_timestamp

# Region value reported on findings for services that are not regional (IAM).
GLOBAL_REGION = "global"

# Global services still need a region to sign requests against.
GLOBAL_ENDPOINT_REGION = "us-east-1"

# IAM and describe APIs throttle easily when a scan walks every resource.
# "standard" mode retries throttling errors with exponential backoff.
CLIENT_CONFIG = Config(retries={"mode": "standard", "max_attempts": 10})

ERROR_REMEDIATION = (
    "Confirm the scanning role has the SecurityAudit and ViewOnlyAccess "
    "managed policies attached, then run the scan again."
)

# boto3 clients are safe to share between threads, but creating them from a
# shared session is not, so client creation is serialised.
_client_lock = threading.Lock()


class Scope(StrEnum):
    GLOBAL = "global"  # run once per account
    REGIONAL = "regional"  # run once per region


@dataclass(frozen=True, slots=True)
class CheckMeta:
    check_id: str
    title: str
    pillar: Pillar
    severity: Severity
    resource_type: str
    scope: Scope
    remediation: str


@dataclass(frozen=True, slots=True)
class CheckContext:
    """Everything a check needs to run once, in one region of one account."""

    session: boto3.Session
    account_id: str
    region: str
    now: datetime

    @property
    def account_arn(self) -> str:
        return f"arn:aws:iam::{self.account_id}:root"

    def arn(self, service: str, resource: str) -> str:
        """ARN of a resource in this context's region and account."""
        return f"arn:aws:{service}:{self.region}:{self.account_id}:{resource}"

    def client(self, service: str, region: str | None = None) -> Any:
        if region is None:
            region = GLOBAL_ENDPOINT_REGION if self.region == GLOBAL_REGION else self.region
        with _client_lock:
            return self.session.client(service, region_name=region, config=CLIENT_CONFIG)

    def finding(
        self,
        meta: CheckMeta,
        status: Status,
        resource_arn: str,
        description: str,
        remediation: str | None = None,
        region: str | None = None,
    ) -> Finding:
        return Finding(
            check_id=meta.check_id,
            title=meta.title,
            pillar=meta.pillar,
            severity=meta.severity,
            status=status,
            resource_arn=resource_arn,
            resource_type=meta.resource_type,
            region=self.region if region is None else region,
            account_id=self.account_id,
            description=description,
            remediation=meta.remediation if remediation is None else remediation,
            scanned_at=format_timestamp(self.now),
        )

    def error(self, meta: CheckMeta, resource_arn: str, exc: Exception) -> Finding:
        """The finding to report when a resource or a whole check cannot be read."""
        return self.finding(
            meta,
            Status.ERROR,
            resource_arn,
            f"The check could not run: {type(exc).__name__}: {exc}",
            remediation=ERROR_REMEDIATION,
        )
