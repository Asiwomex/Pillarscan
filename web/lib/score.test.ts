import { describe, expect, it } from "vitest";

import type { Finding, Severity, Status } from "./findings";
import { postureScore, summarisePillars, verdict } from "./score";

function finding(status: Status, severity: Severity, pillar: Finding["pillar"] = "security"): Finding {
  return {
    check_id: "example",
    title: "Example",
    pillar,
    severity,
    status,
    resource_arn: "arn:aws:s3:::example",
    resource_type: "AWS::S3::Bucket",
    region: "us-east-1",
    account_id: "000000000000",
    description: "",
    remediation: "",
    scanned_at: "2026-10-09T06:00:00Z",
  };
}

// The same cases as tests/scanner/test_store.py::test_posture_score. The
// API scores scans in Python and the browser scores sample data here, so
// the two must agree.
describe("postureScore", () => {
  it.each<[string, [Status, Severity][], number | null]>([
    ["nothing checked", [], null],
    ["only errors", [["error", "critical"]], null],
    ["all passed", [["pass", "low"]], 100],
    ["all failed", [["fail", "low"]], 0],
    ["a critical pass outweighs a low failure", [["pass", "critical"], ["fail", "low"]], 91],
    ["half and half", [["pass", "low"], ["fail", "low"]], 50],
    [
      "37.5 rounds up",
      [["pass", "medium"], ["fail", "medium"], ["fail", "low"], ["fail", "low"]],
      38,
    ],
  ])("%s", (_name, statuses, expected) => {
    const findings = statuses.map(([status, severity]) => finding(status, severity));
    expect(postureScore(findings)).toBe(expected);
  });
});

describe("summarisePillars", () => {
  it("scores each pillar from its own findings", () => {
    const pillars = summarisePillars([
      finding("fail", "high", "security"),
      finding("pass", "low", "cost"),
    ]);

    expect(pillars.map((p) => [p.pillar, p.score, p.failed, p.passed])).toEqual([
      ["security", 0, 1, 0],
      ["reliability", null, 0, 0],
      ["cost", 100, 0, 1],
    ]);
  });
});

describe("verdict", () => {
  it.each<[number | null, string]>([
    [null, "Nothing checked"],
    [95, "Strong"],
    [90, "Strong"],
    [70, "Fair"],
    [50, "Needs attention"],
    [49, "At risk"],
  ])("%s reads as %s", (score, words) => {
    expect(verdict(score)).toBe(words);
  });
});
