"""Read-only HTTP API over stored scans.

It only ever serves the account named in PILLARSCAN_ACCOUNT_ID. Until
sign-in exists (stage 4) the API is public, so the scans it serves are
stored already scrubbed: that account ID is the placeholder 000000000000.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query

from scanner.store import ScanStore

# The interactive docs are switched off to keep the public surface small.
app = FastAPI(title="Pillarscan API", docs_url=None, redoc_url=None, openapi_url=None)


@lru_cache
def get_store() -> ScanStore:
    return ScanStore.from_env()


def account_id() -> str:
    return os.environ.get("PILLARSCAN_ACCOUNT_ID", "000000000000")


Store = Annotated[ScanStore, Depends(get_store)]
AccountId = Annotated[str, Depends(account_id)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/scans")
def list_scans(
    store: Store,
    account: AccountId,
    limit: Annotated[int, Query(ge=1, le=90)] = 30,
) -> dict[str, Any]:
    """Scan summaries, newest first."""
    return {"scans": store.list_scans(account, limit=limit)}


@app.get("/scans/{scan_id}")
def get_scan(scan_id: str, store: Store, account: AccountId) -> dict[str, Any]:
    """One scan with its findings. Use the ID "latest" for the newest scan."""
    scan = store.get_scan(account, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="No such scan.")
    return scan
