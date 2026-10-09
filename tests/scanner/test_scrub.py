from __future__ import annotations

import json
from typing import Any

from scanner.scrub import scrub

REAL_ACCOUNT = "987654321098"


def _report(*findings: dict[str, str]) -> dict[str, Any]:
    return {
        "scan": {"account_id": REAL_ACCOUNT, "regions": ["us-east-1"]},
        "findings": [{"account_id": REAL_ACCOUNT, **finding} for finding in findings],
    }


def test_replaces_the_account_id_everywhere() -> None:
    report = _report(
        {"resource_arn": f"arn:aws:iam::{REAL_ACCOUNT}:root", "description": "Root has no MFA."}
    )

    scrubbed = scrub(report)

    assert REAL_ACCOUNT not in json.dumps(scrubbed)
    assert scrubbed["scan"]["account_id"] == "000000000000"
    assert scrubbed["findings"][0]["resource_arn"] == "arn:aws:iam::000000000000:root"


def test_replaces_user_names_in_arns_and_descriptions() -> None:
    report = _report(
        {
            "resource_arn": f"arn:aws:iam::{REAL_ACCOUNT}:user/jane.doe",
            "description": "User jane.doe has an MFA device.",
        }
    )

    finding = scrub(report)["findings"][0]

    assert finding["resource_arn"] == "arn:aws:iam::000000000000:user/example-user-1"
    assert finding["description"] == "User example-user-1 has an MFA device."


def test_replaces_generated_ids_consistently() -> None:
    group_id = "sg-0123456789abcdef0"
    report = _report(
        {
            "resource_arn": f"arn:aws:ec2:us-east-1:{REAL_ACCOUNT}:security-group/{group_id}",
            "description": f"Security group {group_id} (web) allows SSH.",
        }
    )

    finding = scrub(report)["findings"][0]
    fake_id = finding["resource_arn"].rsplit("/", 1)[1]

    assert fake_id != group_id
    assert fake_id.startswith("sg-") and len(fake_id) == len(group_id)
    assert fake_id in finding["description"]


def test_replaces_access_key_tails() -> None:
    report = _report(
        {
            "resource_arn": f"arn:aws:iam::{REAL_ACCOUNT}:user/ci",
            "description": "Access key ending WXYZ of user ci is 120 days old.",
        }
    )

    finding = scrub(report)["findings"][0]

    assert finding["description"] == (
        "Access key ending 0000 of user example-user-1 is 120 days old."
    )
