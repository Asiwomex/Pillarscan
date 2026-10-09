"""No CloudTrail trail that records every region."""

from __future__ import annotations

from collections.abc import Iterable

from scanner.check import CheckContext, CheckMeta, Scope
from scanner.findings import Finding, Pillar, Severity, Status

META = CheckMeta(
    check_id="cloudtrail_multi_region",
    title="CloudTrail not enabled in all regions",
    pillar=Pillar.SECURITY,
    severity=Severity.HIGH,
    resource_type="AWS::CloudTrail::Trail",
    # One multi-region trail covers the account, so this runs once.
    scope=Scope.GLOBAL,
    remediation=(
        "Create a multi-region trail that delivers to an S3 bucket, with log "
        "file validation on, and make sure logging is started. The first "
        "copy of management events is free; you pay only for the S3 storage."
    ),
)


def run(ctx: CheckContext) -> Iterable[Finding]:
    # includeShadowTrails returns multi-region trails whatever their home
    # region. describe_trails is not a paginated API.
    trails = ctx.client("cloudtrail").describe_trails(includeShadowTrails=True)["trailList"]
    for trail in trails:
        if not trail.get("IsMultiRegionTrail"):
            continue
        # Trail status can only be read in the trail's home region.
        home_region = trail["HomeRegion"]
        status = ctx.client("cloudtrail", region=home_region).get_trail_status(
            Name=trail["TrailARN"]
        )
        if status["IsLogging"]:
            yield ctx.finding(
                META,
                Status.PASS,
                trail["TrailARN"],
                f"Trail {trail['Name']} is logging in all regions.",
                region=home_region,
            )
            return

    yield ctx.finding(
        META,
        Status.FAIL,
        ctx.account_arn,
        "No multi-region trail is logging. API activity in regions you do "
        "not use goes unrecorded, which is where an attacker with stolen "
        "credentials tends to work, and there is no audit trail to "
        "investigate an incident with.",
    )
