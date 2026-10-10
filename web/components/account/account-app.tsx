"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

import { AccountPanel } from "@/components/account/account-panel";
import { Dashboard } from "@/components/dashboard";
import {
  SignedOutError,
  connectAccount,
  fetchAccountHistory,
  fetchAccountScan,
  fetchAccounts,
  requestScan,
  type ConnectedAccount,
  type ScanSummary,
} from "@/lib/api";
import {
  completeSignIn,
  currentSession,
  forgetSession,
  signIn,
  signOut,
  type Session,
} from "@/lib/auth";
import type { ScanReport } from "@/lib/findings";
import { formatDay } from "@/lib/format";
import { cn } from "@/lib/utils";

const POLL_EVERY_MS = 5000;
const POLL_ATTEMPTS = 36; // three minutes

type Viewing = { accountId: string; history: ScanSummary[]; report: ScanReport };

const DARK_BUTTON =
  "inline-flex h-12 items-center justify-center rounded-md px-5 font-semibold transition-colors duration-150";

function SignedOut({ notice, onSignIn }: { notice: string | null; onSignIn: () => void }) {
  return (
    <div className="max-w-2xl">
      <h1 className="text-[clamp(2rem,5vw,3.25rem)] leading-[1.05] font-semibold tracking-[-0.03em] text-balance">
        Scan your own AWS account.
      </h1>
      <p className="mt-5 text-lg leading-relaxed text-pretty text-on-night-muted">
        Sign-in is by invitation. If you have been given an account, sign in to connect an
        AWS account and scan it. Everyone else can explore the demo, which needs no
        sign-in.
      </p>
      {notice && (
        <p className="mt-5 rounded-md border border-night-line bg-night-raised p-4" role="alert">
          {notice}
        </p>
      )}
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={onSignIn}
          className={cn(DARK_BUTTON, "bg-sound-bright text-night active:scale-[0.97]")}
        >
          Sign in
        </button>
        <Link
          href="/#demo"
          className={cn(DARK_BUTTON, "border border-night-line hover:border-on-night-muted")}
        >
          Open the demo
        </Link>
      </div>
    </div>
  );
}

function ConnectForm({ onConnect }: { onConnect: (accountId: string) => Promise<void> }) {
  const [value, setValue] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const accountId = value.replace(/[\s-]/g, "");
    if (!/^\d{12}$/.test(accountId)) {
      setProblem("An AWS account ID is 12 digits. You can find it in the menu at the top right of the AWS console.");
      return;
    }
    setProblem(null);
    setSending(true);
    try {
      await onConnect(accountId);
      setValue("");
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "Something went wrong. Please try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={submit} className="panel p-5" noValidate>
      <h2 className="text-[0.9375rem] font-semibold">Connect an AWS account</h2>
      <p className="mt-1 text-pretty text-muted-ink">
        Pillarscan only ever gets read-only access, through a role you create and can
        delete at any time.
      </p>
      <label htmlFor="aws-account-id" className="mt-4 block text-[0.8125rem] font-medium">
        AWS account ID
      </label>
      <div className="mt-1.5 flex flex-col gap-2 sm:flex-row">
        <input
          id="aws-account-id"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          inputMode="numeric"
          autoComplete="off"
          placeholder="12 digits"
          aria-invalid={problem !== null}
          aria-describedby={problem ? "aws-account-id-problem" : undefined}
          className="h-10 w-full rounded-md border border-line bg-surface px-3 font-mono sm:w-56"
        />
        <button
          type="submit"
          disabled={sending}
          className="inline-flex h-10 items-center justify-center rounded-md bg-ink px-4 font-medium text-surface hover:bg-ink/85 disabled:opacity-50"
        >
          {sending ? "Connecting" : "Connect account"}
        </button>
      </div>
      {problem && (
        <p id="aws-account-id-problem" className="mt-2 text-pretty text-critical" role="alert">
          {problem}
        </p>
      )}
    </form>
  );
}

export function AccountApp() {
  // "checking" until the browser has looked for a session; the server
  // cannot know, so it renders nothing that depends on it.
  const [session, setSession] = useState<Session | null | "checking">("checking");
  const [notice, setNotice] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<ConnectedAccount[] | null>(null);
  const [busyAccount, setBusyAccount] = useState<string | null>(null);
  const [viewing, setViewing] = useState<Viewing | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const results = useRef<HTMLDivElement>(null);

  /** Turn any failed API call into the right message, or a sign-out. */
  const handle = useCallback((error: unknown) => {
    if (error instanceof SignedOutError) {
      forgetSession();
      setSession(null);
      setAccounts(null);
      setViewing(null);
      setNotice("Your session has ended. Sign in again to carry on.");
      return;
    }
    setProblem(error instanceof Error ? error.message : "Something went wrong. Please try again.");
  }, []);

  useEffect(() => {
    let cancelled = false;
    completeSignIn()
      .then((fresh) => fresh ?? currentSession())
      .then(async (found) => {
        if (cancelled) return;
        setSession(found);
        if (found) setAccounts(await fetchAccounts(found.accessToken));
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof SignedOutError) return handle(error);
        setSession(currentSession());
        setNotice(error instanceof Error ? error.message : "The sign-in could not be completed.");
      });
    return () => {
      cancelled = true;
    };
  }, [handle]);

  if (session === "checking") {
    return <p className="text-on-night-muted">Checking whether you are signed in.</p>;
  }
  if (session === null) {
    return <SignedOut notice={notice} onSignIn={() => void signIn()} />;
  }
  const token = session.accessToken;

  async function connect(accountId: string) {
    try {
      const account = await connectAccount(token, accountId);
      setAccounts((current) => [
        ...(current ?? []).filter((other) => other.aws_account_id !== accountId),
        account,
      ]);
    } catch (error) {
      if (error instanceof SignedOutError) return handle(error);
      throw error; // the form shows it beside the field
    }
  }

  async function view(accountId: string, scanId = "latest") {
    setProblem(null);
    try {
      const [history, report] = await Promise.all([
        fetchAccountHistory(token, accountId),
        fetchAccountScan(token, accountId, scanId),
      ]);
      setViewing({ accountId, history, report });
      // Wait for the results to be on the page before scrolling to them.
      requestAnimationFrame(() => results.current?.scrollIntoView({ block: "start" }));
    } catch (error) {
      handle(error);
    }
  }

  async function runScan(accountId: string) {
    setProblem(null);
    setBusyAccount(accountId);
    try {
      await requestScan(token, accountId);
      // The scan runs in the background. Ask how it is going every few
      // seconds until it has finished one way or the other.
      for (let attempt = 0; attempt < POLL_ATTEMPTS; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, POLL_EVERY_MS));
        const latest = await fetchAccounts(token);
        setAccounts(latest);
        const account = latest.find((other) => other.aws_account_id === accountId);
        if (account && account.status !== "scanning") {
          if (account.status === "connected") await view(accountId);
          return;
        }
      }
      setProblem("The scan is taking longer than usual. Reload this page in a minute to see it.");
    } catch (error) {
      handle(error);
    } finally {
      setBusyAccount(null);
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-[clamp(1.75rem,3.4vw,2.5rem)] leading-tight font-semibold tracking-[-0.02em]">
          Your AWS accounts
        </h1>
        <p className="text-on-night-muted">
          {session.email && <span className="mr-3">{session.email}</span>}
          <button
            type="button"
            onClick={signOut}
            className="font-medium text-on-night underline decoration-night-line underline-offset-4 hover:decoration-on-night"
          >
            Sign out
          </button>
        </p>
      </div>

      <div className="demo-frame mt-6 flex flex-col gap-4 rounded-xl border border-night-line bg-page p-4 text-ink sm:p-6">
        {problem && (
          <p className="rounded-md border border-line bg-surface p-3 text-pretty" role="alert">
            {problem}
          </p>
        )}

        {accounts === null ? (
          <p className="text-muted-ink">Loading your accounts.</p>
        ) : (
          <>
            {accounts.length > 0 && (
              <ul className="flex flex-col gap-4">
                {accounts.map((account) => (
                  <AccountPanel
                    key={account.aws_account_id}
                    account={account}
                    busy={busyAccount === account.aws_account_id}
                    viewing={viewing?.accountId === account.aws_account_id}
                    onRunScan={() => void runScan(account.aws_account_id)}
                    onView={() => void view(account.aws_account_id)}
                  />
                ))}
              </ul>
            )}
            <ConnectForm onConnect={connect} />
          </>
        )}
      </div>

      {viewing && (
        <div ref={results} className="mt-10 scroll-mt-20">
          {viewing.history.length > 1 && (
            <div className="mb-4 flex items-center gap-3">
              <h2 className="shrink-0 text-sm font-medium text-on-night-muted">Earlier scans</h2>
              <ul className="flex gap-1.5 overflow-x-auto pb-1">
                {viewing.history.map((entry) => {
                  const current = viewing.report.scan.started_at === entry.started_at;
                  return (
                    <li key={entry.scan_id} className="shrink-0">
                      <button
                        type="button"
                        aria-pressed={current}
                        onClick={() => void view(viewing.accountId, entry.scan_id)}
                        className={cn(
                          "flex h-9 items-center gap-2 rounded-md border px-3 text-sm transition-colors duration-150",
                          current
                            ? "border-on-night"
                            : "border-night-line text-on-night-muted hover:border-on-night-muted",
                        )}
                      >
                        {formatDay(entry.started_at)}
                        <span className="font-semibold">{entry.score ?? "n/a"}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
          <Dashboard
            key={viewing.report.scan.started_at}
            caption="Your scan"
            scans={[
              {
                id: "private",
                label: `Account ${viewing.accountId}`,
                note: "Only you can see this scan. Nothing in it has been replaced or hidden.",
                report: viewing.report,
              },
            ]}
          />
        </div>
      )}
    </>
  );
}
