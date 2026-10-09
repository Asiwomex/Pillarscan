"""The three RDS checks read the same describe call, so they share a test file."""

from __future__ import annotations

from scanner.checks import rds_backup_retention, rds_multi_az, rds_public_access
from scanner.findings import Status

from .conftest import ContextFactory
from .helpers import REGION, create_db_instance


def test_public_access_fails_for_public_instance(make_ctx: ContextFactory) -> None:
    arn = create_db_instance("public-db", PubliclyAccessible=True)

    findings = list(rds_public_access.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_public_access_passes_for_private_instance(make_ctx: ContextFactory) -> None:
    arn = create_db_instance("private-db", PubliclyAccessible=False)

    findings = list(rds_public_access.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]


def test_multi_az_fails_for_single_az_instance(make_ctx: ContextFactory) -> None:
    arn = create_db_instance("single-az-db", MultiAZ=False)

    findings = list(rds_multi_az.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_multi_az_passes_for_multi_az_instance(make_ctx: ContextFactory) -> None:
    arn = create_db_instance("multi-az-db", MultiAZ=True)

    findings = list(rds_multi_az.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]


def test_backup_retention_fails_when_backups_are_off(make_ctx: ContextFactory) -> None:
    arn = create_db_instance("no-backup-db", BackupRetentionPeriod=0)

    findings = list(rds_backup_retention.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.FAIL, arn)]


def test_backup_retention_passes_when_backups_are_kept(make_ctx: ContextFactory) -> None:
    arn = create_db_instance("backed-up-db", BackupRetentionPeriod=7)

    findings = list(rds_backup_retention.run(make_ctx(region=REGION)))

    assert [(f.status, f.resource_arn) for f in findings] == [(Status.PASS, arn)]
    assert "7 days" in findings[0].description
