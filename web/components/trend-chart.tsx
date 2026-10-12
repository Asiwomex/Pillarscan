"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type TrendPoint = { label: string; value: number; current: boolean };

/**
 * One measure across scans, oldest to newest. This is the only file that
 * imports the charting library, so it can load on its own once the chart
 * is about to be seen.
 */
export default function TrendChart({
  points,
  name,
  ceiling,
}: {
  points: TrendPoint[];
  name: string;
  /** The most the measure can be, if it has a limit: 100 for the score. */
  ceiling?: number;
}) {
  const current = points.find((point) => point.current);
  // The axis is fitted to the data, with some room either side, so small
  // changes between scans can be seen. It never runs past what is possible.
  const values = points.map((point) => point.value);
  const room = Math.max(2, Math.ceil((Math.max(...values) - Math.min(...values)) / 2));
  const lowest = Math.max(0, Math.min(...values) - room);
  const highest = Math.min(ceiling ?? Infinity, Math.max(...values) + room);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart
        data={points}
        margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
        // The summary beside the chart describes it for screen readers.
        accessibilityLayer={false}
      >
        <CartesianGrid vertical={false} stroke="var(--line)" />
        <XAxis
          dataKey="label"
          axisLine={false}
          tickLine={false}
          tickMargin={8}
          minTickGap={24}
          tick={{ fill: "var(--muted-ink)", fontSize: 12 }}
        />
        <YAxis
          width={36}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
          domain={[lowest, highest]}
          tick={{ fill: "var(--muted-ink)", fontSize: 12 }}
        />
        <Tooltip
          cursor={{ stroke: "var(--muted-ink)", strokeDasharray: "3 3" }}
          contentStyle={{
            background: "var(--surface)",
            border: "1px solid var(--line)",
            borderRadius: 6,
            fontSize: 13,
            boxShadow: "none",
          }}
          formatter={(value) => [value, name]}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="var(--sound)"
          strokeWidth={2}
          // A line, not a filled area: the axis does not start at zero, and a
          // filled shape would make small changes look larger than they are.
          fillOpacity={0}
          dot={{ r: 3, fill: "var(--surface)", stroke: "var(--sound)", strokeWidth: 2 }}
          activeDot={{ r: 5 }}
          isAnimationActive={false}
        />
        {/* The scan on screen, marked so it can be found on the line. */}
        {current && (
          <ReferenceDot x={current.label} y={current.value} r={5} fill="var(--sound)" stroke="var(--surface)" strokeWidth={2} />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}
