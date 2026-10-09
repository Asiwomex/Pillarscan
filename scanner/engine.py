"""Discovers the checks in scanner/checks and runs them against an account."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from types import ModuleType
from typing import Any

import boto3

from scanner import checks as checks_package
from scanner.check import (
    CLIENT_CONFIG,
    GLOBAL_ENDPOINT_REGION,
    GLOBAL_REGION,
    CheckContext,
    CheckMeta,
    Scope,
)
from scanner.findings import Finding, format_timestamp

logger = logging.getLogger(__name__)

# A scan is almost entirely waiting on AWS, so threads speed it up a lot.
# Kept low to stay well under API rate limits.
MAX_WORKERS = 8


class CheckDefinitionError(Exception):
    """A module in scanner/checks does not follow the check contract."""


@dataclass(frozen=True, slots=True)
class Check:
    meta: CheckMeta
    run: Callable[[CheckContext], Iterable[Finding]]


@dataclass(frozen=True, slots=True)
class ScanResult:
    account_id: str
    started_at: datetime
    finished_at: datetime
    regions: list[str]
    checks_run: list[str]
    findings: list[Finding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scan": {
                "account_id": self.account_id,
                "started_at": format_timestamp(self.started_at),
                "finished_at": format_timestamp(self.finished_at),
                "regions": self.regions,
                "checks_run": self.checks_run,
            },
            "findings": [finding.to_dict() for finding in self.findings],
        }


def discover_checks(package: ModuleType = checks_package) -> list[Check]:
    """Import every module in the package and return its check, sorted by id."""
    found: list[Check] = []
    for info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package.__name__}.{info.name}")
        meta = getattr(module, "META", None)
        run = getattr(module, "run", None)
        if not isinstance(meta, CheckMeta) or not callable(run):
            raise CheckDefinitionError(
                f"{module.__name__} must define META (a CheckMeta) and run(ctx)"
            )
        if meta.check_id != info.name:
            raise CheckDefinitionError(
                f"{module.__name__} has check_id {meta.check_id!r}; "
                "the file must be named after its check_id"
            )
        found.append(Check(meta=meta, run=run))
    return sorted(found, key=lambda check: check.meta.check_id)


def enabled_regions(session: boto3.Session) -> list[str]:
    """Regions the account can use. Opt-in regions that are off are excluded."""
    ec2 = session.client(
        "ec2",
        region_name=session.region_name or GLOBAL_ENDPOINT_REGION,
        config=CLIENT_CONFIG,
    )
    # describe_regions is not a paginated API.
    response = ec2.describe_regions(AllRegions=False)
    return sorted(region["RegionName"] for region in response["Regions"])


def run_check(check: Check, ctx: CheckContext) -> list[Finding]:
    """Run one check. A failure becomes an error finding, never an exception."""
    try:
        return list(check.run(ctx))
    except Exception as exc:  # noqa: BLE001 - one broken check must not stop the scan
        logger.warning("%s failed in %s: %s", check.meta.check_id, ctx.region, exc)
        return [ctx.error(check.meta, ctx.account_arn, exc)]


def run_scan(
    session: boto3.Session,
    checks: Sequence[Check] | None = None,
    regions: Sequence[str] | None = None,
    now: datetime | None = None,
) -> ScanResult:
    """Run every check against the account the session's credentials belong to."""
    started_at = now or datetime.now(timezone.utc)
    checks = discover_checks() if checks is None else checks

    sts = session.client(
        "sts",
        region_name=session.region_name or GLOBAL_ENDPOINT_REGION,
        config=CLIENT_CONFIG,
    )
    account_id: str = sts.get_caller_identity()["Account"]

    # Only look up regions when a check needs them, so an IAM-only scan does
    # not depend on ec2:DescribeRegions.
    has_regional_checks = any(check.meta.scope is Scope.REGIONAL for check in checks)
    if not has_regional_checks:
        scan_regions: list[str] = []
    elif regions is None:
        scan_regions = enabled_regions(session)
    else:
        scan_regions = list(regions)

    runs: list[tuple[Check, CheckContext]] = []
    for check in checks:
        targets = [GLOBAL_REGION] if check.meta.scope is Scope.GLOBAL else scan_regions
        for region in targets:
            ctx = CheckContext(
                session=session, account_id=account_id, region=region, now=started_at
            )
            runs.append((check, ctx))

    # map() returns results in submission order, so output stays deterministic.
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = pool.map(lambda run: run_check(*run), runs)
        findings = [finding for result in results for finding in result]

    return ScanResult(
        account_id=account_id,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc) if now is None else now,
        regions=scan_regions,
        checks_run=[check.meta.check_id for check in checks],
        findings=findings,
    )
