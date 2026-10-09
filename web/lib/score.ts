import { PILLARS, SEVERITIES, type Finding, type Pillar, type Severity } from "./findings";

// How much one finding counts towards the score. A failed critical check
// should outweigh several failed low ones, so the scale is not linear.
const SEVERITY_WEIGHT: Record<Severity, number> = {
  critical: 10,
  high: 6,
  medium: 3,
  low: 1,
};

/**
 * Posture score from 0 to 100: the weighted share of evaluated checks that
 * passed. Findings with status "error" were not evaluated, so they are left
 * out rather than counted for or against. Returns null if nothing was
 * evaluated.
 */
export function postureScore(findings: Finding[]): number | null {
  let passed = 0;
  let failed = 0;
  for (const finding of findings) {
    const weight = SEVERITY_WEIGHT[finding.severity];
    if (finding.status === "pass") passed += weight;
    if (finding.status === "fail") failed += weight;
  }
  if (passed + failed === 0) return null;
  return Math.round((100 * passed) / (passed + failed));
}

export type PillarSummary = {
  pillar: Pillar;
  score: number | null;
  failed: number;
  passed: number;
  failedBySeverity: Record<Severity, number>;
};

export function summarisePillars(findings: Finding[]): PillarSummary[] {
  return PILLARS.map((pillar) => {
    const own = findings.filter((finding) => finding.pillar === pillar);
    const failed = own.filter((finding) => finding.status === "fail");
    return {
      pillar,
      score: postureScore(own),
      failed: failed.length,
      passed: own.filter((finding) => finding.status === "pass").length,
      failedBySeverity: countBySeverity(failed),
    };
  });
}

export function countBySeverity(findings: Finding[]): Record<Severity, number> {
  const counts = Object.fromEntries(SEVERITIES.map((s) => [s, 0])) as Record<Severity, number>;
  for (const finding of findings) counts[finding.severity] += 1;
  return counts;
}

/** A one-word reading of a score, so the number is not left to interpretation. */
export function verdict(score: number | null): string {
  if (score === null) return "Nothing checked";
  if (score >= 90) return "Strong";
  if (score >= 70) return "Fair";
  if (score >= 50) return "Needs attention";
  return "At risk";
}
