import { SEVERITY_COLOR } from "@/components/severity-mark";
import {
  PILLAR_LABELS,
  SEVERITIES,
  SEVERITY_LABELS,
  STATUS_LABELS,
  bySeverity,
  resourceName,
  type Finding,
  type Pillar,
} from "@/lib/findings";
import type { PillarSummary } from "@/lib/score";
import { cn } from "@/lib/utils";

function blockColor(finding: Finding): string {
  if (finding.status === "pass") return "var(--sound)";
  if (finding.status === "error") return "var(--line)";
  return SEVERITY_COLOR[finding.severity];
}

/**
 * The three pillars side by side in one panel, each a wall of blocks with
 * one block per finding. Sound checks are teal; failures take their
 * severity colour, so damage is what you see. Each pillar gets width in
 * proportion to how many checks it holds, so none is left mostly empty.
 */
export function PillarWall({
  pillars,
  findings,
  selected,
  onFilter,
  onOpen,
}: {
  pillars: PillarSummary[];
  findings: Finding[];
  selected: Pillar | "all";
  onFilter: (pillar: Pillar | "all") => void;
  onOpen: (finding: Finding) => void;
}) {
  return (
    <section aria-label="Pillars" className="panel p-5">
      <div className="flex flex-col gap-x-8 gap-y-6 md:flex-row">
        {pillars.map((summary) => {
          const label = PILLAR_LABELS[summary.pillar];
          const own = findings.filter((finding) => finding.pillar === summary.pillar).sort(bySeverity);
          const active = selected === summary.pillar;
          return (
            <div
              key={summary.pillar}
              className="min-w-40"
              // A pillar with more checks gets more room for its blocks.
              style={{ flex: `${Math.max(own.length, 6)} 1 0%` }}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <h3 className="text-[0.9375rem] font-semibold">{label}</h3>
                <p className="text-[0.8125rem] text-muted-ink">
                  <span className="text-[0.9375rem] font-semibold text-ink">
                    {summary.score ?? "n/a"}
                  </span>{" "}
                  / 100
                </p>
              </div>
              <p className="text-[0.8125rem] text-muted-ink">
                {summary.failed} failed, {summary.passed} passed
              </p>

              {/* The table lists the same findings for keyboard and screen reader
                  users, so the blocks stay out of the tab order. */}
              <div className="mt-3 flex flex-wrap gap-1">
                {own.map((finding, index) => (
                  <button
                    key={`${finding.check_id}:${finding.resource_arn}:${finding.region}`}
                    type="button"
                    tabIndex={-1}
                    onClick={() => onOpen(finding)}
                    title={`${finding.title} · ${resourceName(finding.resource_arn)}`}
                    aria-label={`${
                      finding.status === "fail"
                        ? SEVERITY_LABELS[finding.severity]
                        : STATUS_LABELS[finding.status]
                    }: ${finding.title}, ${resourceName(finding.resource_arn)}`}
                    className="size-4 animate-sweep rounded-sm transition-transform duration-150 ease-out hover:scale-125"
                    style={{ background: blockColor(finding), animationDelay: `${index * 5}ms` }}
                  />
                ))}
                {own.length === 0 && (
                  <p className="text-[0.8125rem] text-muted-ink">No checks ran for this pillar.</p>
                )}
              </div>

              <button
                type="button"
                onClick={() => onFilter(active ? "all" : summary.pillar)}
                aria-pressed={active}
                className={cn(
                  "mt-3 text-[0.8125rem] font-medium underline-offset-4 hover:underline",
                  active ? "text-ink" : "text-sound",
                )}
              >
                {active ? "Showing these. Show all pillars" : `Show ${label.toLowerCase()} findings`}
              </button>
            </div>
          );
        })}
      </div>

      <ul className="mt-5 flex flex-wrap gap-x-4 gap-y-1 border-t border-line pt-3 text-[0.8125rem] text-muted-ink">
        <li className="flex items-center gap-1.5">
          <span className="size-3 rounded-sm bg-sound" aria-hidden="true" />
          Passed
        </li>
        {SEVERITIES.map((severity) => (
          <li key={severity} className="flex items-center gap-1.5">
            <span
              className="size-3 rounded-sm"
              style={{ background: SEVERITY_COLOR[severity] }}
              aria-hidden="true"
            />
            {SEVERITY_LABELS[severity]}
          </li>
        ))}
        <li>One block is one check on one resource. Select a block to open it.</li>
      </ul>
    </section>
  );
}
