"use client";

import { useState } from "react";

import { SEVERITY_COLOR } from "@/components/severity-mark";
import type { BreakdownRow } from "@/lib/breakdown";
import { SEVERITIES, SEVERITY_LABELS } from "@/lib/findings";
import { cn } from "@/lib/utils";

const ROWS_SHOWN = 7;

export type BreakdownTab = {
  id: string;
  label: string;
  rows: BreakdownRow[];
  /** The value the findings are currently filtered to, if any. */
  selected: string | null;
  onSelect: (key: string | null) => void;
};

/**
 * Failed checks counted one way or another, as a list of bars. Choosing a
 * row filters the findings table to it; choosing it again clears that.
 */
export function BreakdownPanel({ title, tabs }: { title: string; tabs: BreakdownTab[] }) {
  const [tabId, setTabId] = useState(tabs[0].id);
  const [expanded, setExpanded] = useState(false);
  const tab = tabs.find((candidate) => candidate.id === tabId) ?? tabs[0];
  const largest = Math.max(1, ...tab.rows.map((row) => row.total));
  const rows = expanded ? tab.rows : tab.rows.slice(0, ROWS_SHOWN);
  const hidden = tab.rows.length - rows.length;

  return (
    <section aria-label={title} className="panel flex flex-col p-5">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <h3 className="text-[0.8125rem] font-medium text-muted-ink">{title}</h3>
        {tabs.length > 1 && (
          <div role="tablist" aria-label={title} className="flex gap-4">
            {tabs.map((candidate) => (
              <button
                key={candidate.id}
                type="button"
                role="tab"
                aria-selected={candidate.id === tab.id}
                onClick={() => {
                  setTabId(candidate.id);
                  setExpanded(false);
                }}
                className={cn(
                  "border-b-2 pb-1 text-[0.8125rem] font-medium transition-colors duration-150",
                  candidate.id === tab.id
                    ? "border-ink text-ink"
                    : "border-transparent text-muted-ink hover:text-ink",
                )}
              >
                {candidate.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {tab.rows.length === 0 ? (
        <p className="mt-4 text-muted-ink">No failed checks.</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-1">
          {rows.map((row) => {
            const selected = tab.selected === row.key;
            return (
              <li key={row.key}>
                <button
                  type="button"
                  aria-pressed={selected}
                  onClick={() => tab.onSelect(selected ? null : row.key)}
                  className={cn(
                    "group relative flex w-full items-center justify-between gap-3 rounded-md px-2.5 py-1.5 text-left transition-colors duration-150",
                    selected ? "bg-ink text-surface" : "hover:bg-page",
                  )}
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate">{row.label}</span>
                    {/* The bar's length is the count; its colours are the severities. */}
                    <span
                      className="mt-1 flex h-1.5 gap-px overflow-hidden rounded-full"
                      style={{ width: `${Math.max(4, (100 * row.total) / largest)}%` }}
                      aria-hidden="true"
                    >
                      {SEVERITIES.filter((severity) => row[severity] > 0).map((severity) => (
                        <span
                          key={severity}
                          style={{ background: SEVERITY_COLOR[severity], flexGrow: row[severity] }}
                        />
                      ))}
                    </span>
                  </span>
                  <span className="font-semibold">{row.total}</span>
                  <span className="sr-only">
                    failed:{" "}
                    {SEVERITIES.filter((severity) => row[severity] > 0)
                      .map((severity) => `${row[severity]} ${SEVERITY_LABELS[severity].toLowerCase()}`)
                      .join(", ")}
                    . {selected ? "Showing only these. Select to clear." : "Select to show only these."}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {(hidden > 0 || expanded) && (
        <button
          type="button"
          onClick={() => setExpanded((current) => !current)}
          className="mt-2 self-start px-2.5 text-[0.8125rem] font-medium text-sound underline-offset-4 hover:underline"
        >
          {expanded ? "Show fewer" : `Show ${hidden} more`}
        </button>
      )}
    </section>
  );
}
