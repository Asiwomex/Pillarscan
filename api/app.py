"""HTTP API over stored scans.

Two groups of routes:

    /scans...   public. Serves the scrubbed scans of the platform's own
                account, for the dashboard anyone can open.
    /me/...     for signed-in users. API Gateway checks the Cognito token
                before the request reaches this code; these routes read the
                user's ID from the verified token and never from the
                request itself.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Any
from urllib.parse import quote, urlencode

import boto3
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from scanner.accounts import (
    AccountStore,
    ScanRequestedTooSoon,
    TooManyAccounts,
    tenant_key,
)
from scanner.store import ScanStore

# The interactive docs are switched off to keep the public surface small.
app = FastAPI(title="Pillarscan API", docs_url=None, redoc_url=None, openapi_url=None)

AWS_ACCOUNT_ID = r"^\d{12}$"


@lru_cache
def get_store() -> ScanStore:
    return ScanStore.from_env()


@lru_cache
def get_accounts() -> AccountStore:
    return AccountStore.from_env()


@lru_cache
def get_scan_queue() -> Callable[[dict[str, str]], None]:
    queue = boto3.resource("sqs").Queue(os.environ["SCAN_QUEUE_URL"])
    return lambda request: queue.send_message(MessageBody=json.dumps(request))


def public_account_id() -> str:
    return os.environ.get("PILLARSCAN_ACCOUNT_ID", "000000000000")


def current_user(request: Request) -> str:
    """The signed-in user's ID, from the token API Gateway has verified."""
    event = request.scope.get("aws.event", {})
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    user_id = claims.get("sub")
    if not user_id:
        # API Gateway already refuses unsigned requests to these routes.
        # This is a second lock in case a route is ever exposed by mistake.
        raise HTTPException(status_code=401, detail="Sign in first.")
    return str(user_id)


Store = Annotated[ScanStore, Depends(get_store)]
Accounts = Annotated[AccountStore, Depends(get_accounts)]
ScanQueue = Annotated[Callable[[dict[str, str]], None], Depends(get_scan_queue)]
PublicAccount = Annotated[str, Depends(public_account_id)]
User = Annotated[str, Depends(current_user)]
AccountId = Annotated[str, Path(pattern=AWS_ACCOUNT_ID)]
Limit = Annotated[int, Query(ge=1, le=90)]


# --- Public routes ---------------------------------------------------------


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/scans")
def list_scans(store: Store, account: PublicAccount, limit: Limit = 30) -> dict[str, Any]:
    """Scan summaries, newest first."""
    return {"scans": store.list_scans(account, limit=limit)}


@app.get("/scans/{scan_id}")
def get_scan(scan_id: str, store: Store, account: PublicAccount) -> dict[str, Any]:
    """One scan with its findings. Use the ID "latest" for the newest scan."""
    scan = store.get_scan(account, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="No such scan.")
    return scan


# --- Routes for signed-in users --------------------------------------------


class ConnectAccount(BaseModel):
    aws_account_id: str = Field(pattern=AWS_ACCOUNT_ID)


def launch_url(account: dict[str, Any]) -> str:
    """A link that opens CloudFormation with the role template filled in."""
    region = os.environ.get("AWS_REGION", "us-east-1")
    parameters = urlencode(
        {
            "templateURL": os.environ["ROLE_TEMPLATE_URL"],
            "stackName": f"pillarscan-audit-role{account['role_name_suffix']}",
            "param_ScannerPrincipalArn": os.environ["SCANNER_ROLE_ARN"],
            "param_ExternalId": account["external_id"],
            "param_RoleNameSuffix": account["role_name_suffix"],
        },
        quote_via=quote,
    )
    return (
        f"https://{region}.console.aws.amazon.com/cloudformation/home"
        f"?region={region}#/stacks/quickcreate?{parameters}"
    )


def describe(account: dict[str, Any]) -> dict[str, Any]:
    """What the site is told about a connected account."""
    return {
        "aws_account_id": account["aws_account_id"],
        "role_arn": account["role_arn"],
        "status": account["status"],
        "created_at": account["created_at"],
        "last_requested_at": account.get("last_requested_at"),
        "last_scanned_at": account.get("last_scanned_at"),
        "last_scan_id": account.get("last_scan_id"),
        "last_error": account.get("last_error"),
        "launch_url": launch_url(account),
    }


def owned_account(user: str, aws_account_id: str, accounts: AccountStore) -> dict[str, Any]:
    account = accounts.get(user, aws_account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="You have not connected this account.")
    return account


@app.get("/me/accounts")
def list_accounts(user: User, accounts: Accounts) -> dict[str, Any]:
    return {"accounts": [describe(account) for account in accounts.list(user)]}


@app.post("/me/accounts", status_code=201)
def connect_account(body: ConnectAccount, user: User, accounts: Accounts) -> dict[str, Any]:
    """Start connecting an AWS account. Returns the link that creates its role."""
    try:
        return describe(accounts.connect(user, body.aws_account_id))
    except TooManyAccounts:
        raise HTTPException(
            status_code=409, detail="You have reached the limit of connected accounts."
        ) from None


@app.post("/me/accounts/{aws_account_id}/scans", status_code=202)
def request_scan(
    aws_account_id: AccountId, user: User, accounts: Accounts, queue: ScanQueue
) -> dict[str, str]:
    """Ask for a scan. It runs in the background and takes about a minute."""
    owned_account(user, aws_account_id, accounts)
    try:
        accounts.mark_scan_requested(user, aws_account_id)
    except ScanRequestedTooSoon:
        raise HTTPException(
            status_code=429,
            detail="A scan of this account was requested moments ago. Try again in two minutes.",
        ) from None
    queue({"user_id": user, "aws_account_id": aws_account_id})
    return {"status": "requested"}


@app.get("/me/accounts/{aws_account_id}/scans")
def list_account_scans(
    aws_account_id: AccountId, user: User, accounts: Accounts, store: Store, limit: Limit = 30
) -> dict[str, Any]:
    owned_account(user, aws_account_id, accounts)
    return {"scans": store.list_scans(tenant_key(user, aws_account_id), limit=limit)}


@app.get("/me/accounts/{aws_account_id}/scans/{scan_id}")
def get_account_scan(
    aws_account_id: AccountId, scan_id: str, user: User, accounts: Accounts, store: Store
) -> dict[str, Any]:
    owned_account(user, aws_account_id, accounts)
    scan = store.get_scan(tenant_key(user, aws_account_id), scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="No such scan.")
    return scan
