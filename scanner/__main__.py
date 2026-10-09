"""CLI entry point: python -m scanner --profile <name> --out findings.json"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from scanner.engine import ScanResult, run_scan
from scanner.findings import Severity, Status


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scanner",
        description="Scan an AWS account with read-only access and write findings as JSON.",
    )
    parser.add_argument("--profile", help="AWS CLI profile to use (default: the default credential chain)")
    parser.add_argument("--out", type=Path, default=Path("findings.json"), help="output file (default: findings.json)")
    parser.add_argument(
        "--regions",
        help="comma-separated regions for regional checks (default: every region enabled in the account)",
    )
    return parser.parse_args(argv)


def print_summary(result: ScanResult, out: Path) -> None:
    by_status = Counter(finding.status for finding in result.findings)
    failed_by_severity = Counter(
        finding.severity for finding in result.findings if finding.status is Status.FAIL
    )
    print(f"Ran {len(result.checks_run)} checks against account {result.account_id}")
    print(
        f"  {by_status[Status.FAIL]} failed, {by_status[Status.PASS]} passed, "
        f"{by_status[Status.ERROR]} errored"
    )
    for severity in Severity:
        if failed_by_severity[severity]:
            print(f"  {severity}: {failed_by_severity[severity]}")
    print(f"Findings written to {out}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    regions = [r.strip() for r in args.regions.split(",") if r.strip()] if args.regions else None

    try:
        session = boto3.Session(profile_name=args.profile)
        result = run_scan(session, regions=regions)
    except (BotoCoreError, ClientError) as exc:
        # Raised before any check runs: missing profile, no or expired credentials.
        print(f"Could not start the scan: {exc}", file=sys.stderr)
        return 2

    args.out.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    print_summary(result, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
