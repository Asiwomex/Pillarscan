"""The findings schema shared by the scanner, API, database and frontend."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum


class Pillar(StrEnum):
    SECURITY = "security"
    RELIABILITY = "reliability"
    COST = "cost"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Status(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Finding:
    check_id: str
    title: str
    pillar: Pillar
    severity: Severity
    status: Status
    resource_arn: str
    resource_type: str
    region: str
    account_id: str
    description: str
    remediation: str
    scanned_at: str

    def to_dict(self) -> dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items()}


def format_timestamp(moment: datetime) -> str:
    """Render a datetime as UTC ISO 8601 with a Z suffix, to the second."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
