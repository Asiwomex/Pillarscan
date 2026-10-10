// The findings schema written by the scanner. Keep in step with
// scanner/findings.py; the API and database will use the same shape.

export const PILLARS = ["security", "reliability", "cost"] as const;
export const SEVERITIES = ["critical", "high", "medium", "low"] as const;
export const STATUSES = ["fail", "error", "pass"] as const;

export type Pillar = (typeof PILLARS)[number];
export type Severity = (typeof SEVERITIES)[number];
export type Status = (typeof STATUSES)[number];

export type Finding = {
  check_id: string;
  title: string;
  pillar: Pillar;
  severity: Severity;
  status: Status;
  resource_arn: string;
  resource_type: string;
  region: string;
  account_id: string;
  description: string;
  remediation: string;
  scanned_at: string;
};

export type ScanReport = {
  scan: {
    account_id: string;
    started_at: string;
    finished_at: string;
    regions: string[];
    checks_run: string[];
  };
  findings: Finding[];
};

export const PILLAR_LABELS: Record<Pillar, string> = {
  security: "Security",
  reliability: "Reliability",
  cost: "Cost",
};

export const SEVERITY_LABELS: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

export const STATUS_LABELS: Record<Status, string> = {
  fail: "Failed",
  pass: "Passed",
  error: "Could not check",
};

/** The name part of an ARN, without its type prefix: a bucket name, a volume ID. */
export function resourceName(arn: string): string {
  const resource = arn.split(":").slice(5).join(":");
  if (resource === "root") return "Account";
  // "db:orders-prod" and "volume/vol-123" both carry a type before the name.
  return resource.replace(/^[a-z-]+[:/]/, "") || arn;
}

// The AWS service a check belongs to, read from the first part of its ID.
const SERVICE_LABELS: Record<string, string> = {
  iam: "IAM",
  s3: "S3",
  ec2: "EC2",
  ebs: "EBS",
  rds: "RDS",
  cloudtrail: "CloudTrail",
  guardduty: "GuardDuty",
  dynamodb: "DynamoDB",
  lambda: "Lambda",
  autoscaling: "Auto Scaling",
  elb: "Load Balancing",
  logs: "CloudWatch Logs",
};

export function serviceOf(finding: Finding): string {
  const prefix = finding.check_id.split("_")[0];
  return SERVICE_LABELS[prefix] ?? prefix;
}

/** Worst first: failures by severity, then checks that errored, then passes. */
export function bySeverity(a: Finding, b: Finding): number {
  return (
    STATUSES.indexOf(a.status) - STATUSES.indexOf(b.status) ||
    SEVERITIES.indexOf(a.severity) - SEVERITIES.indexOf(b.severity)
  );
}

/** One row of the findings table: a finding and every region it was found in. */
export type FindingGroup = { finding: Finding; regions: string[] };

/**
 * Merge findings that are the same check with the same result on the same
 * resource. That only happens for account-wide settings checked region by
 * region, such as GuardDuty, where 17 identical rows would bury the rest.
 */
export function groupAcrossRegions(findings: Finding[]): FindingGroup[] {
  const groups = new Map<string, FindingGroup>();
  for (const finding of findings) {
    const key = `${finding.check_id}|${finding.status}|${finding.resource_arn}`;
    const group = groups.get(key);
    if (group) group.regions.push(finding.region);
    else groups.set(key, { finding, regions: [finding.region] });
  }
  return [...groups.values()];
}
