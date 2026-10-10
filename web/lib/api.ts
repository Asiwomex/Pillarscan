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

// --- Routes for signed-in users --------------------------------------------

/** An AWS account the signed-in user has connected. */
export type ConnectedAccount = {
  aws_account_id: string;
  role_arn: string;
  status: "pending" | "scanning" | "connected" | "error";
  created_at: string;
  last_requested_at: string | null;
  last_scanned_at: string | null;
  last_scan_id: string | null;
  last_error: string | null;
  /** Opens CloudFormation with the role template filled in. */
  launch_url: string;
};

/** Thrown when the API refuses the token, which means the session has ended. */
export class SignedOutError extends Error {}

async function send<T>(
  token: string,
  method: "GET" | "POST" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 401) throw new SignedOutError("Your session has ended.");
  if (!response.ok) {
    // The API explains refusals in a "detail" field; show that when it is text.
    const problem = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    throw new Error(
      typeof problem?.detail === "string"
        ? problem.detail
        : "Something went wrong. Please try again.",
    );
  }
  return (await response.json()) as T;
}

export async function fetchAccounts(token: string): Promise<ConnectedAccount[]> {
  return (await send<{ accounts: ConnectedAccount[] }>(token, "GET", "/me/accounts")).accounts;
}

export function connectAccount(token: string, awsAccountId: string): Promise<ConnectedAccount> {
  return send<ConnectedAccount>(token, "POST", "/me/accounts", { aws_account_id: awsAccountId });
}

export async function requestScan(token: string, awsAccountId: string): Promise<void> {
  await send(token, "POST", `/me/accounts/${awsAccountId}/scans`);
}

export async function fetchAccountHistory(
  token: string,
  awsAccountId: string,
): Promise<ScanSummary[]> {
  const path = `/me/accounts/${awsAccountId}/scans`;
  return (await send<{ scans: ScanSummary[] }>(token, "GET", path)).scans;
}

export function fetchAccountScan(
  token: string,
  awsAccountId: string,
  scanId: string,
): Promise<ScanReport> {
  return send<ScanReport>(token, "GET", `/me/accounts/${awsAccountId}/scans/${scanId}`);
}

/**
 * Forget a connected account and delete its scans. Returns the name of the
 * CloudFormation stack that still holds its role, for the user to delete.
 */
export async function disconnectAccount(token: string, awsAccountId: string): Promise<string> {
  const result = await send<{ stack_name: string }>(
    token,
    "DELETE",
    `/me/accounts/${awsAccountId}`,
  );
  return result.stack_name;
}
