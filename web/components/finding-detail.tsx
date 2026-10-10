"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

import { SeverityMark, StatusMark } from "@/components/severity-mark";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { PILLAR_LABELS, serviceOf, type Finding } from "@/lib/findings";
import { formatTimestamp } from "@/lib/format";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="inline-flex shrink-0 items-center gap-1 rounded-md border border-line px-2 py-1 text-xs font-medium hover:bg-page"
    >
      {copied ? (
        <Check className="size-3.5 text-sound" aria-hidden="true" />
      ) : (
        <Copy className="size-3.5" aria-hidden="true" />
      )}
      <span aria-live="polite">{copied ? "Copied" : "Copy ARN"}</span>
    </button>
  );
}

function Fact({ label, mono, children }: { label: string; mono?: boolean; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[6rem_1fr] gap-3 border-b border-line py-2.5 last:border-b-0">
      <dt className="text-muted-ink">{label}</dt>
      <dd className={mono ? "font-mono text-xs leading-5 break-all" : undefined}>{children}</dd>
    </div>
  );
}

export function FindingDetail({
  finding,
  regions,
  open,
  onOpenChange,
}: {
  finding: Finding | null;
  /** Every region this finding was found in; more than one for account-wide settings. */
  regions: string[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 overflow-y-auto shadow-xl sm:max-w-lg data-[side=right]:sm:max-w-lg">
        {finding && (
          <>
            <SheetHeader className="gap-3 border-b border-line p-6 pr-12">
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.8125rem]">
                <StatusMark status={finding.status} />
                <SeverityMark severity={finding.severity} />
                <span className="text-muted-ink">
                  {PILLAR_LABELS[finding.pillar]} · {serviceOf(finding)}
                </span>
              </div>
              <SheetTitle className="text-xl leading-snug font-semibold tracking-tight">
                {finding.title}
              </SheetTitle>
              <SheetDescription className="sr-only">
                Details and remediation for this finding.
              </SheetDescription>
            </SheetHeader>

            <div className="flex flex-col gap-6 p-6">
              <section>
                <h3 className="mb-1.5 text-[0.8125rem] font-semibold">What was found</h3>
                <p className="leading-relaxed text-pretty">{finding.description}</p>
                {regions.length > 1 && (
                  <p className="mt-2 text-pretty text-muted-ink">
                    The same is true in {regions.length - 1} other{" "}
                    {regions.length === 2 ? "region" : "regions"}, listed below.
                  </p>
                )}
              </section>

              <section className="rounded-lg bg-sound-tint p-4">
                <h3 className="mb-1.5 text-[0.8125rem] font-semibold text-sound">How to fix it</h3>
                <p className="leading-relaxed text-pretty">{finding.remediation}</p>
              </section>

              <section>
                <div className="mb-1 flex items-center justify-between">
                  <h3 className="text-[0.8125rem] font-semibold">Resource</h3>
                  <CopyButton text={finding.resource_arn} />
                </div>
                <dl className="text-[0.8125rem]">
                  <Fact label="ARN" mono>
                    {finding.resource_arn}
                  </Fact>
                  <Fact label="Type" mono>
                    {finding.resource_type}
                  </Fact>
                  <Fact label={regions.length > 1 ? `${regions.length} regions` : "Region"} mono>
                    {regions.length > 1 ? regions.join(", ") : finding.region}
                  </Fact>
                  <Fact label="Account" mono>
                    {finding.account_id}
                  </Fact>
                  <Fact label="Check" mono>
                    {finding.check_id}
                  </Fact>
                  <Fact label="Scanned">{formatTimestamp(finding.scanned_at)}</Fact>
                </dl>
              </section>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
