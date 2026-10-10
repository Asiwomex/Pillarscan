from __future__ import annotations

from typing import Any

import pytest

from scanner.score import posture_score
from scanner.store import ScanStore, scan_id_for

from ..conftest import make_report

ACCOUNT = "000000000000"


def test_scan_ids_sort_by_time() -> None:
    assert scan_id_for("2026-10-09T22:12:00Z") == "20261009T221200Z"
    assert scan_id_for("2026-10-09T22:12:00Z") < scan_id_for("2026-10-10T01:00:00Z")


def test_stores_and_returns_a_scan_unchanged(table: Any) -> None:
    store = ScanStore(table)
    report = make_report("2026-10-09T22:12:00Z", [("fail", "high"), ("pass", "low")])

    scan_id = store.put_scan(report)
    stored = store.get_scan(ACCOUNT, scan_id)

    assert stored is not None
    assert stored["findings"] == report["findings"]
    assert stored["scan"]["regions"] == ["us-east-1"]
    assert stored["scan"]["checks_run"] == report["scan"]["checks_run"]


def test_summary_counts_and_scores_the_scan(table: Any) -> None:
    store = ScanStore(table)
    store.put_scan(
        make_report(
            "2026-10-09T22:12:00Z",
            [("fail", "critical"), ("fail", "low"), ("pass", "high"), ("error", "medium")],
        )
    )

    (summary,) = store.list_scans(ACCOUNT)

    assert (summary["failed"], summary["passed"], summary["errored"]) == (2, 1, 1)
    assert summary["failed_by_severity"] == {"critical": 1, "low": 1}
    # 6 passed out of 10 + 1 + 6 evaluated; the errored check is left out.
    assert summary["score"] == 35
    assert isinstance(summary["score"], int)


def test_lists_scans_newest_first(table: Any) -> None:
    store = ScanStore(table)
    for day in ("07", "09", "08"):
        store.put_scan(make_report(f"2026-10-{day}T06:00:00Z", [("pass", "low")]))

    scans = store.list_scans(ACCOUNT)

    assert [scan["started_at"][:10] for scan in scans] == [
        "2026-10-09",
        "2026-10-08",
        "2026-10-07",
    ]
    assert len(store.list_scans(ACCOUNT, limit=2)) == 2


def test_latest_is_the_newest_scan(table: Any) -> None:
    store = ScanStore(table)
    store.put_scan(make_report("2026-10-07T06:00:00Z", [("pass", "low")]))
    store.put_scan(make_report("2026-10-09T06:00:00Z", [("fail", "low")]))

    latest = store.get_scan(ACCOUNT, "latest")

    assert latest is not None
    assert latest["scan"]["started_at"] == "2026-10-09T06:00:00Z"
    assert latest["findings"][0]["status"] == "fail"


def test_unknown_scans_return_none(table: Any) -> None:
    store = ScanStore(table)

    assert store.get_scan(ACCOUNT, "20200101T000000Z") is None
    assert store.get_scan(ACCOUNT, "latest") is None
    assert store.list_scans(ACCOUNT) == []


def test_scans_of_other_accounts_are_not_visible(table: Any) -> None:
    store = ScanStore(table)
    scan_id = store.put_scan(make_report("2026-10-09T06:00:00Z", [("pass", "low")]))

    assert store.list_scans("111111111111") == []
    assert store.get_scan("111111111111", scan_id) is None


def test_items_carry_an_expiry_time(table: Any) -> None:
    ScanStore(table).put_scan(make_report("2026-10-09T06:00:00Z", [("pass", "low")]))

    items = table.scan()["Items"]

    assert len(items) == 2
    assert all(item["expires_at"] > 0 for item in items)


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([], None),
        ([("error", "critical")], None),
        ([("pass", "low")], 100),
        ([("fail", "low")], 0),
        ([("pass", "critical"), ("fail", "low")], 91),
        # 1 of 2 low checks passed: 50 exactly.
        ([("pass", "low"), ("fail", "low")], 50),
        # 3 of 8 by weight is 37.5, which rounds up as it does in the browser.
        ([("pass", "medium"), ("fail", "medium"), ("fail", "low"), ("fail", "low")], 38),
    ],
)
def test_posture_score(statuses: list[tuple[str, str]], expected: int | None) -> None:
    findings = [{"status": status, "severity": severity} for status, severity in statuses]

    assert posture_score(findings) == expected
