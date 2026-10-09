"""GuardDuty not enabled in a region."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="guardduty_enabled",
    title="GuardDuty not enabled",
    pillar=Pillar.SECURITY,
    severity=Severity.MEDIUM,
    resource_type="AWS::GuardDuty::Detector",
    scope=Scope.REGIONAL,
    remediation=(
        "Enable GuardDuty in every region, including unused ones, since "
        "that is where unexpected activity stands out. It has a 30-day free "
        "trial and is billed by the volume of logs analysed afterwards, so "
        "check the usage page before the trial ends."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    guardduty = ctx.client("guardduty")
    for page in guardduty.get_paginator("list_detectors").paginate():
        for detector_id in page["DetectorIds"]:
            # A detector can exist but be suspended.
            if guardduty.get_detector(DetectorId=detector_id)["Status"] == "ENABLED":
                yield ctx.finding(
                    META,
                    Status.PASS,
                    ctx.arn("guardduty", f"detector/{detector_id}"),
                    f"GuardDuty is enabled in {ctx.region}.",
                )
                return

    yield ctx.finding(
        META,
        Status.FAIL,
        ctx.account_arn,
        f"GuardDuty is not enabled in {ctx.region}. Nothing is watching "
        "CloudTrail, VPC flow and DNS logs there for signs of compromise "
        "such as crypto-mining or credentials used from an unusual place.",
    )
