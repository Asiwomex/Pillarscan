from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

import boto3
import pytest

from scanner.check import GLOBAL_REGION, CheckContext

# The account ID moto reports for every mocked call.
MOTO_ACCOUNT_ID = "123456789012"

ContextFactory = Callable[..., CheckContext]


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
