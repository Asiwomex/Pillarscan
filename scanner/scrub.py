"""Turn a real scan into sample data that is safe to publish.

    python -m scanner.scrub findings.json sample-data/findings.json

Replaces the account ID, AWS-generated resource IDs, IAM user names and
access key tails. Names you chose yourself (buckets, tables, functions) are
kept, so read the output before committing it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

FAKE_ACCOUNT_ID = "000000000000"

# IDs AWS generates, such as sg-0123456789abcdef0 or vol-0123456789abcdef0.
RESOURCE_ID = re.compile(r"\b((?:sg|vol|snap|i|vpc|subnet|eipalloc|ami)-)([0-9a-f]{8,17})\b")
DETECTOR_ID = re.compile(r"\b(detector/)([0-9a-f]{32})\b")
KEY_TAIL = re.compile(r"(Access key ending )\w{4}")
USER_ARN = re.compile(r":user/(?:[^\"]*/)?([^/\"]+)$")


def _fake_id(match: re.Match[str]) -> str:
    # Hashing keeps the mapping stable, so one resource that appears in
    # several findings still has one ID after scrubbing.
    digest = hashlib.sha256(match.group(2).encode()).hexdigest()
    return match.group(1) + digest[: len(match.group(2))]


def _user_names(report: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for finding in report["findings"]:
        match = USER_ARN.search(finding["resource_arn"])
        if match:
            names.add(match.group(1))
    return sorted(names)


def scrub(report: dict[str, Any]) -> dict[str, Any]:
    account_id: str = report["scan"]["account_id"]
    text = json.dumps(report)

    text = text.replace(account_id, FAKE_ACCOUNT_ID)
    for index, name in enumerate(_user_names(report), start=1):
        text = re.sub(rf"(?<![\w-]){re.escape(name)}(?![\w-])", f"example-user-{index}", text)
    text = RESOURCE_ID.sub(_fake_id, text)
    text = DETECTOR_ID.sub(_fake_id, text)
    text = KEY_TAIL.sub(r"\g<1>0000", text)

    if account_id != FAKE_ACCOUNT_ID and account_id in text:
        raise ValueError("the account ID survived scrubbing")
    scrubbed: dict[str, Any] = json.loads(text)
    return scrubbed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scanner.scrub", description=__doc__)
    parser.add_argument("source", type=Path, help="findings file written by the scanner")
    parser.add_argument("destination", type=Path, help="where to write the scrubbed copy")
    args = parser.parse_args(argv)

    report = json.loads(args.source.read_text(encoding="utf-8"))
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(json.dumps(scrub(report), indent=2) + "\n", encoding="utf-8")
    print(f"Scrubbed {len(report['findings'])} findings into {args.destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
