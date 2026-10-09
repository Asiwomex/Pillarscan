"use client";

import { useCallback, useMemo, useState } from "react";
import { Search } from "lucide-react";

import { FindingDetail } from "@/components/finding-detail";
import { FindingsTable } from "@/components/findings-table";
import { PillarBlocks } from "@/components/pillar-blocks";
import { ServiceChart } from "@/components/service-chart";
import { Mark } from "@/components/site/mark";
import { SEVERITY_COLOR } from "@/components/severity-mark";
import {
  PILLARS,
  PILLAR_LABELS,
  SEVERITIES,
  SEVERITY_LABELS,
  type Finding,
  type Pillar,
  type Severity,
  type Status,
} from "@/lib/findings";
import { formatTimestamp } from "@/lib/format";
import type { Scan } from "@/lib/scans";
import { countBySeverity, postureScore, summarisePillars, verdict } from "@/lib/score";
import { cn } from "@/lib/utils";

type Filters = {
  status: Status | "all";
  pillar: Pillar | "all";
  severity: Severity | "all";
  query: string;
};

const DEFAULT_FILTERS: Filters = { status: "fail", pillar: "all", severity: "all", query: "" };

function matches(finding: Finding, filters: Filters): boolean {
  if (filters.status !== "all" && finding.status !== filters.status) return false;
  if (filters.pillar !== "all" && finding.pillar !== filters.pillar) return false;
  if (filters.severity !== "all" && finding.severity !== filters.severity) return false;
  const query = filters.query.trim().toLowerCase();
  if (!query) return true;
  return [finding.title, finding.resource_arn, finding.check_id, finding.region].some((text) =>
    text.toLowerCase().includes(query),
  );
}

const CONTROL =
  "h-8 rounded-md border border-line bg-surface px-2.5 text-[0.8125rem] transition-colors duration-150 hover:border-muted-ink";

/** A row of mutually exclusive options, used for the scan and status pickers. */
function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string; count?: number }[];
  onChange: (value: T) => void;
}) {
  return (
    <div role="group" aria-label={label} className="inline-flex rounded-md border border-line bg-page p-0.5">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={option.value === value}
          onClick={() => onChange(option.value)}
          className={cn(
            "rounded-[0.25rem] px-2.5 py-1 text-[0.8125rem] font-medium text-muted-ink transition-colors duration-150 hover:text-ink",
            option.value === value && "bg-surface text-ink shadow-[0_0_0_1px_var(--line)]",
          )}
        >
          {option.label}
          {option.count !== undefined && (
            <span className="ml-1.5 font-normal text-muted-ink">{option.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}

function Select<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-[0.8125rem] text-muted-ink">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
        className={cn(CONTROL, "pr-1 text-ink")}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function Dashboard({ scans }: { scans: Scan[] }) {
  const [scanId, setScanId] = useState(scans[0].id);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [selected, setSelected] = useState<Finding | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const scan = scans.find((candidate) => candidate.id === scanId) ?? scans[0];
  const { findings } = scan.report;
  const { regions, checks_run: checksRun, started_at: startedAt } = scan.report.scan;

  const summary = useMemo(() => {
    const failed = findings.filter((finding) => finding.status === "fail");
    return {
      score: postureScore(findings),
      failed,
      passed: findings.filter((finding) => finding.status === "pass").length,
      failedBySeverity: countBySeverity(failed),
      pillars: summarisePillars(findings),
    };
  }, [findings]);

  const visible = useMemo(
    () => findings.filter((finding) => matches(finding, filters)),
    [findings, filters],
  );

  const openDetail = useCallback((finding: Finding) => {
    setSelected(finding);
    setDetailOpen(true);
  }, []);

  function update(patch: Partial<Filters>) {
    setFilters((current) => ({ ...current, ...patch }));
  }

  const filtered =
    filters.pillar !== "all" || filters.severity !== "all" || filters.query !== "";

  return (
    <div className="demo-frame overflow-hidden rounded-xl border border-night-line bg-page text-ink shadow-2xl shadow-black/40">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface px-4 py-3 sm:px-6">
        <div className="flex items-center gap-2.5">
          <Mark className="size-5" />
          <span className="text-[0.9375rem] font-semibold tracking-tight">Pillarscan</span>
          <span className="text-muted-ink">Live demo</span>
        </div>
        <Segmented
          label="Scan"
          value={scan.id}
          onChange={setScanId}
          options={scans.map((option) => ({ value: option.id, label: option.label }))}
        />
      </div>

      <div className="px-4 pt-5 pb-6 sm:px-6">
        <p className="mb-4 max-w-3xl text-[0.8125rem] text-pretty text-muted-ink">
          <span className="font-medium text-ink">{scan.label}.</span> {scan.note}
        </p>

        <div className="grid gap-4 lg:grid-cols-12">
          <section aria-labelledby="score-heading" className="panel p-5 lg:col-span-5">
            <h3 id="score-heading" className="text-[0.8125rem] font-medium text-muted-ink">
              Posture score
            </h3>
            <p className="mt-2 flex items-baseline gap-3">
              <span className="text-5xl leading-none font-semibold tracking-[-0.03em]">
                {summary.score ?? "n/a"}
              </span>
              <span className="text-muted-ink">/ 100</span>
              <span className="ml-auto text-[0.9375rem] font-semibold">{verdict(summary.score)}</span>
            </p>
            <p className="mt-3 text-pretty">
              {summary.failed.length} of {findings.length} checks failed.{" "}
              <span className="text-muted-ink">
                {checksRun.length} rules
                {regions.length > 0 &&
                  `, ${regions.length} ${regions.length === 1 ? "region" : "regions"}`}
                , scanned {formatTimestamp(startedAt)}.
              </span>
            </p>

            {summary.failed.length > 0 && (
              <div
                className="mt-5 flex h-2 gap-0.5 overflow-hidden rounded-full"
                aria-hidden="true"
              >
                {SEVERITIES.filter((severity) => summary.failedBySeverity[severity] > 0).map(
                  (severity) => (
                    <span
                      key={severity}
                      style={{
                        background: SEVERITY_COLOR[severity],
                        flexGrow: summary.failedBySeverity[severity],
                      }}
                    />
                  ),
                )}
              </div>
            )}
            <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1">
              {SEVERITIES.map((severity) => (
                <li key={severity}>
                  <button
                    type="button"
                    onClick={() => update({ status: "fail", severity })}
                    className="group flex items-center gap-2 rounded-md py-1 text-left"
                    aria-label={`${summary.failedBySeverity[severity]} ${SEVERITY_LABELS[severity].toLowerCase()} failures. Show them in the table.`}
                  >
                    <span
                      className="size-2 shrink-0 rounded-full"
                      style={{ background: SEVERITY_COLOR[severity] }}
                      aria-hidden="true"
                    />
                    <span className="font-semibold">{summary.failedBySeverity[severity]}</span>
                    <span className="text-muted-ink underline-offset-4 group-hover:underline">
                      {SEVERITY_LABELS[severity]}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="service-heading" className="panel p-5 lg:col-span-7">
            <h3 id="service-heading" className="mb-3 text-[0.8125rem] font-medium text-muted-ink">
              Failed checks by service
            </h3>
            <ServiceChart failed={summary.failed} />
          </section>
        </div>

        {/* Keyed by scan so the sweep replays when the scan is switched. */}
        <div key={scan.id} className="mt-4 grid gap-4 md:grid-cols-3">
          {summary.pillars.map((pillar) => (
            <PillarBlocks
              key={pillar.pillar}
              summary={pillar}
              findings={findings.filter((finding) => finding.pillar === pillar.pillar)}
              selected={filters.pillar === pillar.pillar}
              onFilter={() =>
                update({ pillar: filters.pillar === pillar.pillar ? "all" : pillar.pillar })
              }
              onOpen={openDetail}
            />
          ))}
        </div>
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[0.8125rem] text-muted-ink">
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

        <section aria-labelledby="findings-heading" className="panel mt-6 overflow-hidden">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-3 p-5">
            <h3 id="findings-heading" className="mr-auto text-[0.9375rem] font-semibold">
              Findings
            </h3>
            <Segmented
              label="Status"
              value={filters.status}
              onChange={(status) => update({ status })}
              options={[
                { value: "fail", label: "Failed", count: summary.failed.length },
                { value: "pass", label: "Passed", count: summary.passed },
                { value: "all", label: "All", count: findings.length },
              ]}
            />
            <Select
              label="Pillar"
              value={filters.pillar}
              onChange={(pillar) => update({ pillar })}
              options={[
                { value: "all", label: "All" },
                ...PILLARS.map((pillar) => ({ value: pillar, label: PILLAR_LABELS[pillar] })),
              ]}
            />
            <Select
              label="Severity"
              value={filters.severity}
              onChange={(severity) => update({ severity })}
              options={[
                { value: "all", label: "All" },
                ...SEVERITIES.map((severity) => ({
                  value: severity,
                  label: SEVERITY_LABELS[severity],
                })),
              ]}
            />
            <label className={cn(CONTROL, "flex w-full items-center gap-2 sm:w-64")}>
              <Search className="size-3.5 shrink-0 text-muted-ink" aria-hidden="true" />
              <span className="sr-only">Search findings</span>
              <input
                type="search"
                value={filters.query}
                onChange={(event) => update({ query: event.target.value })}
                placeholder="Search name, resource or region"
                className="w-full bg-transparent outline-none placeholder:text-muted-ink"
              />
            </label>
          </div>

          {visible.length > 0 ? (
            <FindingsTable findings={visible} onSelect={openDetail} />
          ) : (
            <div className="border-t border-line px-5 py-12 text-center">
              <p className="font-medium">No findings match these filters.</p>
              <button
                type="button"
                onClick={() => setFilters(DEFAULT_FILTERS)}
                className={cn(CONTROL, "mt-3 font-medium")}
              >
                Reset filters
              </button>
            </div>
          )}

          <div
            className="flex items-center justify-between border-t border-line px-5 py-2.5 text-[0.8125rem] text-muted-ink"
            aria-live="polite"
          >
            <span>
              Showing {visible.length} of {findings.length}
            </span>
            {filtered && (
              <button
                type="button"
                onClick={() => setFilters({ ...DEFAULT_FILTERS, status: filters.status })}
                className="font-medium text-sound underline-offset-4 hover:underline"
              >
                Clear filters
              </button>
            )}
          </div>
        </section>
      </div>

      <FindingDetail finding={selected} open={detailOpen} onOpenChange={setDetailOpen} />
    </div>
  );
}
