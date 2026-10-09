import { SEVERITY_COLOR } from "@/components/severity-mark";
import {
  PILLAR_LABELS,
  SEVERITY_LABELS,
  STATUS_LABELS,
  bySeverity,
  resourceName,
  type Finding,
} from "@/lib/findings";
import type { PillarSummary } from "@/lib/score";
import { cn } from "@/lib/utils";

function blockColor(finding: Finding): string {
  if (finding.status === "pass") return "var(--sound)";
  if (finding.status === "error") return "var(--line)";
  return SEVERITY_COLOR[finding.severity];
}

/**
 * One pillar drawn as a wall of blocks, one block per finding. Sound checks
 * are teal; failures take their severity colour, so damage is what you see.
 */
export function PillarBlocks({
  summary,
  findings,
  selected,
  onFilter,
  onOpen,
}: {
  summary: PillarSummary;
  findings: Finding[];
  selected: boolean;
  onFilter: () => void;
  onOpen: (finding: Finding) => void;
}) {
  const label = PILLAR_LABELS[summary.pillar];
  const ordered = [...findings].sort(bySeverity);

  return (
    <section aria-label={label} className={cn("panel p-5", selected && "border-ink")}>
      <div className="flex items-baseline justify-between gap-3">
        <h4 className="text-[0.9375rem] font-semibold">{label}</h4>
        <p className="text-muted-ink">
          <span className="text-2xl font-semibold tracking-tight text-ink">
            {summary.score ?? "n/a"}
          </span>{" "}
          / 100
        </p>
      </div>
      <p className="mt-0.5 text-[0.8125rem] text-muted-ink">
        {summary.failed} failed, {summary.passed} passed
      </p>

      {/* The table lists the same findings for keyboard and screen reader
          users, so the blocks stay out of the tab order. */}
      <div className="mt-4 flex flex-wrap gap-1">
        {ordered.map((finding, index) => (
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
            className="size-5 animate-sweep rounded-sm transition-transform duration-150 ease-out hover:scale-125"
            style={{ background: blockColor(finding), animationDelay: `${index * 6}ms` }}
          />
        ))}
        {ordered.length === 0 && (
          <p className="text-[0.8125rem] text-muted-ink">No checks ran for this pillar.</p>
        )}
      </div>

      <button
        type="button"
        onClick={onFilter}
        aria-pressed={selected}
        className="mt-4 text-[0.8125rem] font-medium text-sound underline-offset-4 hover:underline"
      >
        {selected ? "Show all pillars" : `Show ${label.toLowerCase()} findings`}
      </button>
    </section>
  );
}
