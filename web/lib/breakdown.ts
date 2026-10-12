import { SEVERITIES, type Finding, type Severity } from "./findings";

/** One line of a breakdown: how many failed findings share a value. */
export type BreakdownRow = { key: string; label: string; total: number } & Record<Severity, number>;

/**
 * Count failed findings by any property, busiest first. Each row also
 * carries the count per severity, so its bar can show the mix.
 */
export function breakdown(
  failed: Finding[],
  keyOf: (finding: Finding) => string,
  labelOf: (finding: Finding) => string = keyOf,
): BreakdownRow[] {
  const rows = new Map<string, BreakdownRow>();
  for (const finding of failed) {
    const key = keyOf(finding);
    const row = rows.get(key) ?? {
      key,
      label: labelOf(finding),
      total: 0,
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
    };
    row[finding.severity] += 1;
    row.total += 1;
    rows.set(key, row);
  }
  return [...rows.values()].sort(
    (a, b) => b.total - a.total || worst(a) - worst(b) || a.label.localeCompare(b.label),
  );
}

// Position of the most severe failure in a row; lower is worse.
function worst(row: BreakdownRow): number {
  return SEVERITIES.findIndex((severity) => row[severity] > 0);
}
