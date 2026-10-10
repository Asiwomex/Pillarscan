import type { ScanReport, Severity } from "./findings";

// The read-only API from infra/platform. The address is public and holds
// no secret, so it can live in the source; the variable is there to point
// a build at a different deployment.
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://kzowp5bd5l.execute-api.us-east-1.amazonaws.com";

/** One row of scan history, as GET /scans returns it. */
export type ScanSummary = {
  scan_id: string;
  started_at: string;
  score: number | null;
  failed: number;
  passed: number;
  errored: number;
  failed_by_severity: Partial<Record<Severity, number>>;
};

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) throw new Error(`The API answered ${response.status} for ${path}`);
  return (await response.json()) as T;
}

/** Scan summaries, newest first. */
export async function fetchHistory(): Promise<ScanSummary[]> {
  return (await get<{ scans: ScanSummary[] }>("/scans")).scans;
}

/** One scan with its findings. The ID "latest" returns the newest. */
export function fetchScan(scanId: string): Promise<ScanReport> {
  return get<ScanReport>(`/scans/${scanId}`);
}
