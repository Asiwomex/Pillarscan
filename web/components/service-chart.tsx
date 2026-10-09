"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { SEVERITY_COLOR } from "@/components/severity-mark";
import {
  SEVERITIES,
  SEVERITY_LABELS,
  serviceOf,
  type Finding,
  type Severity,
} from "@/lib/findings";

const MAX_ROWS = 8;
const AXIS_WIDTH = 150;

type Row = { service: string; total: number } & Record<Severity, number>;

function rowsByService(failed: Finding[]): Row[] {
  const rows = new Map<string, Row>();
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
  const other: Row = { service: "Other services", total: 0, critical: 0, high: 0, medium: 0, low: 0 };
  for (const row of sorted.slice(MAX_ROWS - 1)) {
    for (const severity of SEVERITIES) other[severity] += row[severity];
    other.total += row.total;
  }
  return [...sorted.slice(0, MAX_ROWS - 1), other];
}

/** Axis label: the service name with its total beside it. */
function ServiceTick({
  y,
  payload,
  totals,
}: {
  y?: number | string;
  payload?: { value: string };
  totals: Map<string, number>;
}) {
  if (!payload) return null;
  return (
    <text x={0} y={y} dy="0.35em" fontSize={13}>
      <tspan fill="var(--ink)">{payload.value}</tspan>
      <tspan fill="var(--muted-ink)" dx={8}>
        {totals.get(payload.value)}
      </tspan>
    </text>
  );
}

/** Failed checks per AWS service, stacked by severity: where the problems are. */
export function ServiceChart({ failed }: { failed: Finding[] }) {
  const rows = rowsByService(failed);
  const totals = new Map(rows.map((row) => [row.service, row.total]));

  if (rows.length === 0) {
    return <p className="text-muted-ink">No failed checks.</p>;
  }

  return (
    <figure>
      <figcaption className="sr-only">
        Failed checks by service.{" "}
        {rows.map((row) => `${row.service}: ${row.total}.`).join(" ")}
      </figcaption>
      <div style={{ height: rows.length * 26 + 8 }} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            barSize={12}
            margin={{ top: 0, bottom: 0, left: 0, right: 0 }}
          >
            <XAxis type="number" hide allowDecimals={false} />
            <YAxis
              type="category"
              dataKey="service"
              width={AXIS_WIDTH}
              interval={0}
              axisLine={false}
              tickLine={false}
              tick={<ServiceTick totals={totals} />}
            />
            <Tooltip
              cursor={{ fill: "var(--page)" }}
              contentStyle={{
                background: "var(--surface)",
                border: "1px solid var(--line)",
                borderRadius: 6,
                fontSize: 13,
                boxShadow: "none",
              }}
              formatter={(value, name) => [value, SEVERITY_LABELS[name as Severity]]}
            />
            {SEVERITIES.map((severity) => (
              <Bar
                key={severity}
                dataKey={severity}
                stackId="failed"
                fill={SEVERITY_COLOR[severity]}
                // Surface-coloured gaps keep neighbouring segments apart.
                stroke="var(--surface)"
                strokeWidth={1.5}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
