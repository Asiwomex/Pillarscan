"use client";

import { useCallback, useMemo, useState } from "react";
import { Search, X } from "lucide-react";

import { BreakdownPanel } from "@/components/breakdown-panel";
import { FindingDetail } from "@/components/finding-detail";
import { FindingsTable } from "@/components/findings-table";
import { Overview } from "@/components/overview";
import { PillarWall } from "@/components/pillar-wall";
import { Mark } from "@/components/site/mark";
import { fetchHistory, fetchScan } from "@/lib/api";
import { API_ONLINE } from "@/lib/backend";
import { breakdown } from "@/lib/breakdown";
import {
  PILLARS,
  PILLAR_LABELS,
  SEVERITIES,
  SEVERITY_LABELS,
  groupAcrossRegions,
  serviceOf,
  type Finding,
  type FindingGroup,
  type Pillar,
  type ScanReport,
  type ScanSummary,
  type Severity,
  type Status,
} from "@/lib/findings";
import { formatDay } from "@/lib/format";
import type { Scan } from "@/lib/scans";
import { postureScore, summarisePillars } from "@/lib/score";
import { cn } from "@/lib/utils";

type Filters = {
  status: Status | "all";
  pillar: Pillar | "all";
  severity: Severity | "all";
  service: string | "all";
  check: string | "all";
  region: string | "all";
  query: string;
};

const DEFAULT_FILTERS: Filters = {
  status: "fail",
  pillar: "all",
  severity: "all",
  service: "all",
  check: "all",
  region: "all",
  query: "",
};

function matches(finding: Finding, filters: Filters): boolean {
  if (filters.status !== "all" && finding.status !== filters.status) return false;
  if (filters.pillar !== "all" && finding.pillar !== filters.pillar) return false;
  if (filters.severity !== "all" && finding.severity !== filters.severity) return false;
  if (filters.service !== "all" && serviceOf(finding) !== filters.service) return false;
  if (filters.check !== "all" && finding.check_id !== filters.check) return false;
  if (filters.region !== "all" && finding.region !== filters.region) return false;
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

// The scan that is read from the API instead of from a file.
const LIVE_SCAN_ID = "real";

// What the dashboard knows about the API. Until a live scan arrives, the
// saved copy of the same account's scan is shown in its place.
type Live =
  | { status: "idle" | "loading" | "failed"; history: ScanSummary[]; report: null }
  | { status: "ready"; history: ScanSummary[]; report: ScanReport };

const LIVE_NOTE: Record<Live["status"], string> = {
  idle: "",
  loading: "Fetching the latest scan from the API. Until it arrives this is a saved copy.",
  failed: "The API could not be reached, so this is a saved copy of an earlier scan.",
  ready:
    "This project's own AWS account, scanned every day by a Lambda function. Account and resource IDs are replaced before a scan is stored.",
};

// While the backend is switched off there is nothing to fetch, so the
// saved copy is all there is, and the note says so.
const OFFLINE_NOTE =
  "A saved scan of this project's own AWS account, with the account ID and resource IDs replaced. The daily scan is paused while the backend is switched off.";

export function Dashboard({
  scans,
  caption = "Live demo",
  onSelectHistory,
}: {
  scans: Scan[];
  /** Shown beside the name in the top bar. */
  caption?: string;
  /** Given when the page around the dashboard can load an earlier scan. */
  onSelectHistory?: (scanId: string) => void;
}) {
  const [scanId, setScanId] = useState(scans[0].id);
  const [live, setLive] = useState<Live>({ status: "idle", history: [], report: null });
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [selected, setSelected] = useState<FindingGroup | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const scan = scans.find((candidate) => candidate.id === scanId) ?? scans[0];
  const isLive = scan.id === LIVE_SCAN_ID;
  const report = isLive && live.report ? live.report : scan.report;
  const { findings } = report;
  const { regions, started_at: startedAt } = report.scan;

  // Earlier scans of the same account, newest first.
  const history = isLive && live.report ? live.history : (scan.history ?? []);
  const pickHistory = isLive && live.report ? (id: string) => void loadLive(id) : onSelectHistory;

  async function loadLive(historyScanId?: string) {
    setLive((current) => ({ status: "loading", history: current.history, report: null }));
    try {
      const [liveHistory, liveReport] = await Promise.all([
        fetchHistory(),
        fetchScan(historyScanId ?? "latest"),
      ]);
      setLive({ status: "ready", history: liveHistory, report: liveReport });
    } catch {
      setLive((current) => ({ status: "failed", history: current.history, report: null }));
    }
  }

  function chooseScan(id: string) {
    setScanId(id);
    setFilters(DEFAULT_FILTERS);
    // Fetched the first time the live scan is opened, not on page load, so
    // visitors who only look at the demo never call the API.
    if (id === LIVE_SCAN_ID && API_ONLINE && live.status === "idle") void loadLive();
  }

  const summary = useMemo(() => {
    const failed = findings.filter((finding) => finding.status === "fail");
    const resources = new Set(
      findings
        .map((finding) => finding.resource_arn)
        // Account-wide settings are not resources in their own right.
        .filter((arn) => !arn.endsWith(":root")),
    );
    return {
      score: postureScore(findings),
      failed,
      passed: findings.filter((finding) => finding.status === "pass").length,
      resources: resources.size,
      pillars: summarisePillars(findings),
      byService: breakdown(failed, serviceOf),
      byCheck: breakdown(
        failed,
        (finding) => finding.check_id,
        (finding) => finding.title,
      ),
      // Severities read best in their own order, not by count.
      bySeverity: breakdown(
        failed,
        (finding) => finding.severity,
        (finding) => SEVERITY_LABELS[finding.severity],
      ).sort(
        (a, b) =>
          SEVERITIES.indexOf(a.key as Severity) - SEVERITIES.indexOf(b.key as Severity),
      ),
      byRegion: breakdown(failed, (finding) => finding.region),
    };
  }, [findings]);

  const visible = useMemo(
    () => findings.filter((finding) => matches(finding, filters)),
    [findings, filters],
  );
  const visibleGroups = useMemo(() => groupAcrossRegions(visible), [visible]);

  const openGroup = useCallback((group: FindingGroup) => {
    setSelected(group);
    setDetailOpen(true);
  }, []);

  // A block in a pillar is always one finding in one region.
  const openDetail = useCallback((finding: Finding) => {
    setSelected({ finding, regions: [finding.region] });
    setDetailOpen(true);
  }, []);

  function update(patch: Partial<Filters>) {
    setFilters((current) => ({ ...current, ...patch }));
  }

  /** Narrow the table from a breakdown row. Breakdowns only count failures. */
  function narrow(patch: Partial<Filters>) {
    update({ ...patch, status: "fail" });
  }

  // Everything narrowing the table beyond its status tab, each removable.
  const checkTitle = summary.byCheck.find((row) => row.key === filters.check)?.label;
  const chips = [
    filters.pillar !== "all" && {
      label: `Pillar: ${PILLAR_LABELS[filters.pillar]}`,
      clear: () => update({ pillar: "all" }),
    },
    filters.severity !== "all" && {
      label: `Severity: ${SEVERITY_LABELS[filters.severity]}`,
      clear: () => update({ severity: "all" }),
    },
    filters.service !== "all" && {
      label: `Service: ${filters.service}`,
      clear: () => update({ service: "all" }),
    },
    filters.check !== "all" && {
      label: `Check: ${checkTitle ?? filters.check}`,
      clear: () => update({ check: "all" }),
    },
    filters.region !== "all" && {
      label: `Region: ${filters.region}`,
      clear: () => update({ region: "all" }),
    },
    filters.query.trim() !== "" && {
      label: `Search: ${filters.query.trim()}`,
      clear: () => update({ query: "" }),
    },
  ].filter((chip) => chip !== false);

  return (
    <div className="demo-frame overflow-hidden rounded-xl border border-night-line bg-page text-ink shadow-2xl shadow-black/40">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface px-4 py-3 sm:px-6">
        <div className="flex items-center gap-2.5">
          <Mark className="size-5" />
          <span className="text-[0.9375rem] font-semibold tracking-tight">Pillarscan</span>
          <span className="text-muted-ink">{caption}</span>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {pickHistory && history.length > 1 && (
            <Select
              label="Scan"
              value={history.find((entry) => entry.started_at === startedAt)?.scan_id ?? ""}
              onChange={(id) => pickHistory(id)}
              options={history.map((entry) => ({
                value: entry.scan_id,
                label: `${formatDay(entry.started_at)} UTC`,
              }))}
            />
          )}
          {scans.length > 1 && (
            <Segmented
              label="Account"
              value={scan.id}
              onChange={chooseScan}
              options={scans.map((option) => ({ value: option.id, label: option.label }))}
            />
          )}
        </div>
      </div>

      <div className="flex flex-col gap-4 px-4 pt-5 pb-6 sm:px-6">
        <p className="max-w-3xl text-[0.8125rem] text-pretty text-muted-ink">
          <span className="font-medium text-ink">{scan.label}.</span>{" "}
          <span aria-live="polite">
            {isLive ? (API_ONLINE ? LIVE_NOTE[live.status] : OFFLINE_NOTE) : scan.note}
          </span>
          {isLive && live.status === "failed" && (
            <button
              type="button"
              onClick={() => void loadLive()}
              className="ml-2 font-medium text-sound underline-offset-4 hover:underline"
            >
              Try again
            </button>
          )}
        </p>

        <Overview
          score={summary.score}
          failed={summary.failed.length}
          passed={summary.passed}
          resources={summary.resources}
          regions={regions.length}
          startedAt={startedAt}
          history={history}
        />

        {/* Keyed by scan so the sweep replays when the scan changes. */}
        <PillarWall
          key={`${scan.id}:${startedAt}`}
          pillars={summary.pillars}
          findings={findings}
          selected={filters.pillar}
          onFilter={(pillar) => update({ pillar })}
          onOpen={openDetail}
        />

        <div className="grid gap-4 lg:grid-cols-2">
          <BreakdownPanel
            title="Failed checks by"
            tabs={[
              {
                id: "service",
                label: "Service",
                rows: summary.byService,
                selected: filters.service === "all" ? null : filters.service,
                onSelect: (key) => narrow({ service: key ?? "all" }),
              },
              {
                id: "check",
                label: "Check",
                rows: summary.byCheck,
                selected: filters.check === "all" ? null : filters.check,
                onSelect: (key) => narrow({ check: key ?? "all" }),
              },
            ]}
          />
          <BreakdownPanel
            title="Failed checks by"
            tabs={[
              {
                id: "severity",
                label: "Severity",
                rows: summary.bySeverity,
                selected: filters.severity === "all" ? null : filters.severity,
                onSelect: (key) => narrow({ severity: (key as Severity | null) ?? "all" }),
              },
              {
                id: "region",
                label: "Region",
                rows: summary.byRegion,
                selected: filters.region === "all" ? null : filters.region,
                onSelect: (key) => narrow({ region: key ?? "all" }),
              },
            ]}
          />
        </div>

        <section aria-labelledby="findings-heading" className="panel overflow-hidden">
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

          {chips.length > 0 && (
            <ul aria-label="Filters in use" className="flex flex-wrap items-center gap-2 px-5 pb-4">
              {chips.map((chip) => (
                <li key={chip.label}>
                  <button
                    type="button"
                    onClick={chip.clear}
                    className="inline-flex h-7 max-w-full items-center gap-1.5 rounded-md bg-ink pr-1.5 pl-2.5 text-[0.8125rem] text-surface"
                  >
                    <span className="truncate">{chip.label}</span>
                    <X className="size-3.5 shrink-0" aria-hidden="true" />
                    <span className="sr-only">Remove this filter</span>
                  </button>
                </li>
              ))}
              {chips.length > 1 && (
                <li>
                  <button
                    type="button"
                    onClick={() => setFilters({ ...DEFAULT_FILTERS, status: filters.status })}
                    className="text-[0.8125rem] font-medium text-sound underline-offset-4 hover:underline"
                  >
                    Clear all
                  </button>
                </li>
              )}
            </ul>
          )}

          {visible.length > 0 ? (
            <FindingsTable groups={visibleGroups} onSelect={openGroup} />
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

          <p
            className="border-t border-line px-5 py-2.5 text-[0.8125rem] text-pretty text-muted-ink"
            aria-live="polite"
          >
            Showing {visible.length} of {findings.length} findings
            {visibleGroups.length < visible.length &&
              `, with repeats across regions shown as one row (${visibleGroups.length} rows)`}
          </p>
        </section>
      </div>

      <FindingDetail
        finding={selected?.finding ?? null}
        regions={selected?.regions ?? []}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
    </div>
  );
}
