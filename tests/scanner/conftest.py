from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import datetime, timezone

import boto3
import pytest
from moto import mock_aws

from scanner.check import GLOBAL_REGION, CheckContext

# The account ID moto reports for every mocked call.
MOTO_ACCOUNT_ID = "123456789012"

ContextFactory = Callable[..., CheckContext]


@pytest.fixture(autouse=True)
def aws(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Mock AWS for every test and make sure real credentials are never used."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    with mock_aws():
        yield


@pytest.fixture
def session() -> boto3.Session:
    return boto3.Session(region_name="us-east-1")


@pytest.fixture
def make_ctx(session: boto3.Session) -> ContextFactory:
    def factory(region: str = GLOBAL_REGION, now: datetime | None = None) -> CheckContext:
        return CheckContext(
            session=session,
            account_id=MOTO_ACCOUNT_ID,
            region=region,
            now=now or datetime.now(timezone.utc),
        )

    return factory
