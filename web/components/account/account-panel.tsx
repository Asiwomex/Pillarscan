import { ExternalLink } from "lucide-react";

import type { ConnectedAccount } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { cn } from "@/lib/utils";

const BUTTON =
  "inline-flex h-10 items-center justify-center gap-2 rounded-md px-4 font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50";
const PRIMARY = cn(BUTTON, "bg-ink text-surface hover:bg-ink/85");
const SECONDARY = cn(BUTTON, "border border-line bg-surface hover:border-muted-ink");

const STATUS_TEXT: Record<ConnectedAccount["status"], string> = {
  pending: "Waiting for its role",
  scanning: "Scanning now",
  connected: "Connected",
  error: "Needs attention",
};

/** One connected AWS account: where it stands, and what to do next. */
export function AccountPanel({
  account,
  busy,
  viewing,
  onRunScan,
  onView,
}: {
  account: ConnectedAccount;
  /** A scan was requested from this page and has not finished yet. */
  busy: boolean;
  viewing: boolean;
  onRunScan: () => void;
  onView: () => void;
}) {
  const scanning = busy || account.status === "scanning";
  const neverScanned = account.last_scan_id === null;

  return (
    <li className={cn("panel p-5", viewing && "border-ink")}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 className="font-mono text-[0.9375rem]">{account.aws_account_id}</h3>
        <p
          className={cn(
            "text-[0.8125rem] font-medium",
            account.status === "connected" ? "text-sound" : "text-muted-ink",
          )}
          aria-live="polite"
        >
          {scanning ? STATUS_TEXT.scanning : STATUS_TEXT[account.status]}
          {account.last_scanned_at && !scanning && (
            <span className="font-normal text-muted-ink">
              {" "}
              · last scanned {formatTimestamp(account.last_scanned_at)}
            </span>
          )}
        </p>
      </div>

      {account.last_error && !scanning && (
        <p className="mt-3 rounded-md border border-line bg-page p-3 text-pretty" role="alert">
          {account.last_error}
        </p>
      )}

      {neverScanned && (
        <ol className="mt-4 flex flex-col gap-3 text-pretty text-muted-ink">
          <li>
            <span className="font-medium text-ink">Create the role.</span> The button opens
            CloudFormation in your AWS account with the template filled in. Tick the
            acknowledgement at the bottom and choose Create stack. It takes about a minute.
          </li>
          <li>
            <span className="font-medium text-ink">Run a scan.</span> Once the stack says
            CREATE_COMPLETE, come back here and run the first scan.
          </li>
        </ol>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {neverScanned && (
          <a href={account.launch_url} target="_blank" rel="noreferrer" className={SECONDARY}>
            Create the role
            <ExternalLink className="size-3.5" aria-hidden="true" />
            <span className="sr-only">(opens the AWS console in a new tab)</span>
          </a>
        )}
        <button type="button" onClick={onRunScan} disabled={scanning} className={PRIMARY}>
          {scanning ? "Scanning, about a minute" : neverScanned ? "Run the first scan" : "Scan again"}
        </button>
        {!neverScanned && (
          <button type="button" onClick={onView} aria-pressed={viewing} className={SECONDARY}>
            {viewing ? "Showing results below" : "Show results"}
          </button>
        )}
      </div>
    </li>
  );
}
