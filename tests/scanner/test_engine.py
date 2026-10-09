from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import boto3

from scanner.__main__ import main
from scanner.check import CheckContext, CheckMeta, Scope
from scanner.engine import Check, discover_checks, enabled_regions, run_scan
from scanner.findings import Finding, Pillar, Severity, Status

from .conftest import MOTO_ACCOUNT_ID

SCHEMA_KEYS = {
    "check_id",
    "title",
    "pillar",
    "severity",
    "status",
    "resource_arn",
    "resource_type",
    "region",
    "account_id",
    "description",
    "remediation",
    "scanned_at",
}


def _fake_check(check_id: str, scope: Scope, fail_with: Exception | None = None) -> Check:
    meta = CheckMeta(
        check_id=check_id,
        title="Fake check",
        pillar=Pillar.SECURITY,
        severity=Severity.LOW,
        resource_type="AWS::Fake::Thing",
        scope=scope,
        remediation="Nothing to do.",
    )

    def run(ctx: CheckContext) -> Iterable[Finding]:
        if fail_with is not None:
            raise fail_with
        yield ctx.finding(meta, Status.PASS, f"arn:aws:fake:{ctx.region}::thing", "Fine.")

    return Check(meta=meta, run=run)


def test_discovers_checks_named_after_their_files() -> None:
    check_ids = [check.meta.check_id for check in discover_checks()]

    assert check_ids == sorted(check_ids)
    assert {"iam_root_mfa", "iam_user_mfa", "iam_access_key_age"} <= set(check_ids)


def test_global_checks_run_once_and_regional_checks_once_per_region(
    session: boto3.Session,
) -> None:
    checks = [_fake_check("global_one", Scope.GLOBAL), _fake_check("regional_one", Scope.REGIONAL)]

    result = run_scan(session, checks=checks, regions=["us-east-1", "eu-west-1"])

    assert result.account_id == MOTO_ACCOUNT_ID
    assert [(f.check_id, f.region) for f in result.findings] == [
        ("global_one", "global"),
        ("regional_one", "us-east-1"),
        ("regional_one", "eu-west-1"),
    ]


def test_crashing_check_becomes_an_error_finding_and_the_scan_continues(
    session: boto3.Session,
) -> None:
    checks = [
        _fake_check("broken", Scope.GLOBAL, fail_with=RuntimeError("boom")),
        _fake_check("healthy", Scope.GLOBAL),
    ]

    result = run_scan(session, checks=checks)

    assert [(f.check_id, f.status) for f in result.findings] == [
        ("broken", Status.ERROR),
        ("healthy", Status.PASS),
    ]
    assert "boom" in result.findings[0].description


def test_enabled_regions_come_from_the_account(session: boto3.Session) -> None:
    regions = enabled_regions(session)

    assert "us-east-1" in regions
    assert regions == sorted(regions)


def test_cli_writes_findings_in_the_schema(tmp_path: Path) -> None:
    out = tmp_path / "findings.json"

    exit_code = main(["--out", str(out)])

    assert exit_code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["scan"]["account_id"] == MOTO_ACCOUNT_ID
    assert report["findings"], "a fresh account should at least fail the root MFA check"
    for finding in report["findings"]:
        assert set(finding) == SCHEMA_KEYS
    assert report["findings"][0]["scanned_at"].endswith("Z")
