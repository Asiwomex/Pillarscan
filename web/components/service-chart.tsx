"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { SEVERITY_COLOR } from "@/components/severity-mark";
import { SEVERITIES, SEVERITY_LABELS, type Severity } from "@/lib/findings";
import type { ServiceRow } from "@/lib/services";

const AXIS_WIDTH = 150;

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

/**
 * The bars themselves. This is the only file that imports the charting
 * library, so it can be loaded on its own once the chart scrolls into view.
 */
export default function ServiceChart({ rows }: { rows: ServiceRow[] }) {
  const totals = new Map(rows.map((row) => [row.service, row.total]));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={rows}
        layout="vertical"
        barSize={12}
        margin={{ top: 0, bottom: 0, left: 0, right: 0 }}
        // The figure's caption describes the chart for screen readers, so the
        // chart itself stays out of the tab order.
        accessibilityLayer={false}
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
  );
}
