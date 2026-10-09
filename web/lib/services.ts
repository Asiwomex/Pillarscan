import { SEVERITIES, serviceOf, type Finding, type Severity } from "./findings";

export type ServiceRow = { service: string; total: number } & Record<Severity, number>;

const MAX_ROWS = 8;

/** Failed findings counted per AWS service, busiest first. */
export function rowsByService(failed: Finding[]): ServiceRow[] {
  const rows = new Map<string, ServiceRow>();
  for (const finding of failed) {
    const service = serviceOf(finding);
    const row = rows.get(service) ?? { service, total: 0, critical: 0, high: 0, medium: 0, low: 0 };
    row[finding.severity] += 1;
    row.total += 1;
    rows.set(service, row);
  }
  const sorted = [...rows.values()].sort((a, b) => b.total - a.total);
  if (sorted.length <= MAX_ROWS) return sorted;

  // Fold the long tail into one row so the chart stays a glanceable height.
  const other: ServiceRow = {
    service: "Other services",
    total: 0,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  };
  for (const row of sorted.slice(MAX_ROWS - 1)) {
    for (const severity of SEVERITIES) other[severity] += row[severity];
    other.total += row.total;
  }
  return [...sorted.slice(0, MAX_ROWS - 1), other];
}
