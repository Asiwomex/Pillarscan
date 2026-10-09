import { Check, CircleAlert, X } from "lucide-react";

import { SEVERITY_LABELS, STATUS_LABELS, type Severity, type Status } from "@/lib/findings";
import { cn } from "@/lib/utils";

export const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "var(--critical)",
  high: "var(--high)",
  medium: "var(--medium)",
  low: "var(--low)",
};

/** Severity as a colour dot plus its name, so colour is never the only cue. */
export function SeverityMark({ severity, className }: { severity: Severity; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 whitespace-nowrap", className)}>
      <span
        className="size-2 shrink-0 rounded-full"
        style={{ background: SEVERITY_COLOR[severity] }}
        aria-hidden="true"
      />
      <span className={cn(severity === "critical" && "font-semibold")}>
        {SEVERITY_LABELS[severity]}
      </span>
    </span>
  );
}

const STATUS_ICON = { fail: X, pass: Check, error: CircleAlert } as const;

const STATUS_STYLE: Record<Status, string> = {
  fail: "text-ink",
  pass: "text-sound",
  error: "text-muted-ink",
};

export function StatusMark({ status }: { status: Status }) {
  const Icon = STATUS_ICON[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-[0.8125rem] font-medium whitespace-nowrap",
        STATUS_STYLE[status],
      )}
    >
      <Icon className="size-3.5" strokeWidth={2.5} aria-hidden="true" />
      {STATUS_LABELS[status]}
    </span>
  );
}
