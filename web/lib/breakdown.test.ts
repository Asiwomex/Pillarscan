import { describe, expect, it } from "vitest";

import { breakdown } from "./breakdown";
import { groupAcrossRegions, resourceName, serviceOf, type Finding, type Severity } from "./findings";

function failed(check_id: string, severity: Severity, resource: string, region = "us-east-1"): Finding {
  return {
    check_id,
    title: `Title of ${check_id}`,
    pillar: "security",
    severity,
    status: "fail",
    resource_arn: resource,
    resource_type: "AWS::Example::Thing",
    region,
    account_id: "000000000000",
    description: "",
    remediation: "",
    scanned_at: "2026-10-09T06:00:00Z",
  };
}

const ACCOUNT = "arn:aws:iam::000000000000:root";

describe("breakdown", () => {
  const findings = [
    failed("s3_versioning", "low", "arn:aws:s3:::a"),
    failed("s3_public_access_block", "high", "arn:aws:s3:::a"),
    failed("iam_root_mfa", "critical", ACCOUNT, "global"),
  ];

  it("counts by any property, busiest first", () => {
    const rows = breakdown(findings, serviceOf);

    expect(rows.map((row) => [row.label, row.total])).toEqual([
      ["S3", 2],
      ["IAM", 1],
    ]);
    expect(rows[0]).toMatchObject({ high: 1, low: 1, critical: 0 });
  });

  it("puts the more severe row first when counts are equal", () => {
    const rows = breakdown(findings, (finding) => finding.check_id);

    expect(rows.map((row) => row.key)).toEqual([
      "iam_root_mfa",
      "s3_public_access_block",
      "s3_versioning",
    ]);
  });

  it("uses a separate label when one is given", () => {
    const [row] = breakdown([findings[0]], (f) => f.check_id, (f) => f.title);

    expect(row).toMatchObject({ key: "s3_versioning", label: "Title of s3_versioning" });
  });
});

describe("groupAcrossRegions", () => {
  it("merges an account-wide setting found in several regions", () => {
    const groups = groupAcrossRegions([
      failed("guardduty_enabled", "medium", ACCOUNT, "us-east-1"),
      failed("guardduty_enabled", "medium", ACCOUNT, "eu-west-1"),
      failed("ebs_default_encryption", "medium", ACCOUNT, "us-east-1"),
    ]);

    expect(groups.map((group) => [group.finding.check_id, group.regions])).toEqual([
      ["guardduty_enabled", ["us-east-1", "eu-west-1"]],
      ["ebs_default_encryption", ["us-east-1"]],
    ]);
  });

  it("keeps different resources apart", () => {
    const groups = groupAcrossRegions([
      failed("s3_versioning", "low", "arn:aws:s3:::a"),
      failed("s3_versioning", "low", "arn:aws:s3:::b"),
    ]);

    expect(groups).toHaveLength(2);
  });
});

describe("resourceName", () => {
  it.each([
    ["arn:aws:iam::000000000000:root", "Account"],
    ["arn:aws:s3:::northwind-artifacts", "northwind-artifacts"],
    ["arn:aws:rds:us-east-1:000000000000:db:orders-prod", "orders-prod"],
    ["arn:aws:ec2:us-east-1:000000000000:volume/vol-0123", "vol-0123"],
    [
      "arn:aws:autoscaling:us-east-1:000000000000:autoScalingGroup:78d3:autoScalingGroupName/worker-asg",
      "worker-asg",
    ],
    [
      "arn:aws:elasticloadbalancing:us-east-1:000000000000:loadbalancer/app/api-v1-retired/5ffa",
      "api-v1-retired",
    ],
    ["arn:aws:logs:us-east-1:000000000000:log-group:/aws/lambda/thumbnailer", "/aws/lambda/thumbnailer"],
  ])("%s is shown as %s", (arn, name) => {
    expect(resourceName(arn)).toBe(name);
  });
});
