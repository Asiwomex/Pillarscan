"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";

import type { TrendPoint } from "@/components/trend-chart";
import type { ScanSummary } from "@/lib/findings";
import { formatDate, formatDay } from "@/lib/format";
import { verdict } from "@/lib/score";
import { cn } from "@/lib/utils";

// The charting library is the heaviest script on the page. Loading it only
// when the chart is about to be seen keeps the first paint and first tap fast.
const TrendChart = dynamic(() => import("@/components/trend-chart"), { ssr: false });

const CHART_HEIGHT = 200;

type Metric = "score" | "failed";

const METRIC_NAME: Record<Metric, string> = { score: "Posture score", failed: "Failed checks" };

type Change = { text: string; tone: "good" | "plain" };

/**
 * "3 higher than the previous scan", or null when there is nothing to
 * compare with. `upIsGood` says which direction counts as an improvement.
 */
function change(
  now: number | null,
  before: number | null | undefined,
  words: { up: string; down: string },
  upIsGood: boolean,
): Change | null {
  if (now === null || before === null || before === undefined) return null;
  if (now === before) return { text: "Same as the previous scan", tone: "plain" };
  const up = now > before;
  return {
    text: `${Math.abs(now - before)} ${up ? words.up : words.down} than the previous scan`,
    tone: up === upIsGood ? "good" : "plain",
  };
}

function Stat({
  label,
  value,
  note,
  noteTone,
  selected,
  onSelect,
}: {
  label: string;
  value: string | number;
  note?: string;
  noteTone?: "good" | "plain";
  /** Present on the stats that the chart can plot. */
  selected?: boolean;
  onSelect?: () => void;
}) {
  const body = (
    <>
      <span className="block text-[0.8125rem] font-medium text-muted-ink">{label}</span>
      <span className="mt-1 block text-2xl leading-tight font-semibold tracking-tight">{value}</span>
      <span
        className={cn(
          "mt-0.5 block min-h-5 text-[0.8125rem] text-pretty",
          noteTone === "good" ? "text-sound" : "text-muted-ink",
        )}
      >
        {note}
      </span>
    </>
  );
  const frame = "block h-full w-full rounded-md px-3 py-2.5 text-left";

  return onSelect ? (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        frame,
        "transition-colors duration-150",
        selected ? "bg-page shadow-[inset_0_0_0_1px_var(--line)]" : "hover:bg-page",
      )}
    >
      {body}
      <span className="sr-only">Show this on the chart.</span>
    </button>
  ) : (
    <div className={frame}>{body}</div>
  );
}

/** The answer first: where the account stands now, and which way it is moving. */
export function Overview({
  score,
  failed,
  passed,
  resources,
  regions,
  startedAt,
  history,
}: {
  score: number | null;
  failed: number;
  passed: number;
  resources: number;
  regions: number;
  startedAt: string;
  /** Summaries of this account's scans, newest first. May be empty. */
  history: ScanSummary[];
}) {
  const [metric, setMetric] = useState<Metric>("score");
  const frame = useRef<HTMLDivElement>(null);
  const [near, setNear] = useState(false);

  useEffect(() => {
    const element = frame.current;
    if (!element) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setNear(true);
          observer.disconnect();
        }
      },
      { rootMargin: "300px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const index = history.findIndex((entry) => entry.started_at === startedAt);
  const previous = index >= 0 ? history[index + 1] : undefined;
  const scoreChange = change(score, previous?.score, { up: "higher", down: "lower" }, true);
  const failedChange = change(failed, previous?.failed, { up: "more", down: "fewer" }, false);

  // One scan a day needs only the date on the axis. Two on the same day
  // need the time as well, or their labels would be the same.
  const days = history.map((entry) => entry.started_at.slice(0, 10));
  const sameDayTwice = new Set(days).size < days.length;

  // Oldest first, the direction a chart is read in.
  const points: TrendPoint[] = [...history].reverse().map((entry) => ({
    label: sameDayTwice ? formatDay(entry.started_at) : formatDate(entry.started_at),
    value: (metric === "score" ? entry.score : entry.failed) ?? 0,
    current: entry.started_at === startedAt,
  }));

  return (
    <section aria-label="Overview" className="panel p-2">
      <div className="grid grid-cols-2 gap-1 md:grid-cols-5">
        <Stat
          label="Posture score"
          value={score === null ? "n/a" : `${score} / 100`}
          note={scoreChange?.text ?? verdict(score)}
          noteTone={scoreChange?.tone}
          selected={metric === "score"}
          onSelect={() => setMetric("score")}
        />
        <Stat
          label="Failed checks"
          value={failed}
          note={failedChange?.text}
          noteTone={failedChange?.tone}
          selected={metric === "failed"}
          onSelect={() => setMetric("failed")}
        />
        <Stat label="Passed checks" value={passed} />
        <Stat label="Resources checked" value={resources} />
        <Stat label="Regions scanned" value={regions === 0 ? "Global only" : regions} />
      </div>

      <figure className="px-3 pt-3 pb-2">
        <figcaption className="sr-only">
          {METRIC_NAME[metric]} over the last {points.length} scans:{" "}
          {points.map((point) => `${point.label}, ${point.value}`).join("; ")}.
        </figcaption>
        {/* The height is fixed up front, so nothing moves when the chart arrives. */}
        <div ref={frame} style={{ height: CHART_HEIGHT }} aria-hidden="true">
          {points.length < 2 ? (
            <p className="flex h-full items-center justify-center rounded-md bg-page px-4 text-center text-pretty text-muted-ink">
              The trend appears here once this account has been scanned twice.
            </p>
          ) : (
            near && (
              <TrendChart
                points={points}
                name={METRIC_NAME[metric]}
                ceiling={metric === "score" ? 100 : undefined}
              />
            )
          )}
        </div>
      </figure>
    </section>
  );
}
