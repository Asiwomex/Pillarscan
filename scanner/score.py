"""Posture score for a scan.

The same formula lives in web/lib/score.ts, which scores the sample data in
the browser. Change both together.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

# How much one finding counts. A failed critical check should outweigh
# several failed low ones, so the scale is not linear.
SEVERITY_WEIGHT = {"critical": 10, "high": 6, "medium": 3, "low": 1}


def posture_score(findings: Iterable[Mapping[str, str]]) -> int | None:
    """Weighted share of evaluated checks that passed, from 0 to 100.

    Findings with status "error" were not evaluated, so they count neither
    for nor against. Returns None if nothing was evaluated.
    """
    passed = 0
    failed = 0
    for finding in findings:
        weight = SEVERITY_WEIGHT[finding["severity"]]
        if finding["status"] == "pass":
            passed += weight
        elif finding["status"] == "fail":
            failed += weight
    if passed + failed == 0:
        return None
    # Round half up, as JavaScript's Math.round does, so both sides agree.
    return int(100 * passed / (passed + failed) + 0.5)
