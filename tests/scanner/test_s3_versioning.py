from __future__ import annotations

import boto3

from scanner.checks import s3_versioning
from scanner.findings import Status

from .conftest import ContextFactory
from .helpers import REGION


def _create_bucket(name: str, versioning: str | None = None) -> None:
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=name)
    if versioning:
        s3.put_bucket_versioning(Bucket=name, VersioningConfiguration={"Status": versioning})


def test_fails_when_versioning_was_never_enabled(make_ctx: ContextFactory) -> None:
    _create_bucket("plain-bucket")

    findings = list(s3_versioning.run(make_ctx()))

    assert [(f.status, f.resource_arn) for f in findings] == [
        (Status.FAIL, "arn:aws:s3:::plain-bucket")
    ]


def test_fails_when_versioning_is_suspended(make_ctx: ContextFactory) -> None:
    _create_bucket("paused-bucket", versioning="Suspended")

    findings = list(s3_versioning.run(make_ctx()))

    assert [f.status for f in findings] == [Status.FAIL]
    assert "suspended" in findings[0].description


def test_passes_when_versioning_is_enabled(make_ctx: ContextFactory) -> None:
    _create_bucket("versioned-bucket", versioning="Enabled")

    findings = list(s3_versioning.run(make_ctx()))

    assert [f.status for f in findings] == [Status.PASS]
