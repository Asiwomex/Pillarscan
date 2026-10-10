import Link from "next/link";
import { Check, CircleDashed } from "lucide-react";

import { SeverityMark } from "@/components/severity-mark";
import { Mark } from "@/components/site/mark";
import { PILLARS, PILLAR_LABELS, SEVERITIES, type Finding } from "@/lib/findings";
import { AUTHOR_URL, LYTAWORKS_URL, REPO_URL } from "@/lib/links";

function SectionHeading({ title, lead }: { title: string; lead: string }) {
  return (
    <div className="max-w-2xl">
      <h2 className="text-[clamp(1.75rem,3.4vw,2.5rem)] leading-tight font-semibold tracking-[-0.02em] text-balance">
        {title}
      </h2>
      <p className="mt-3 text-lg leading-relaxed text-pretty text-on-night-muted">{lead}</p>
    </div>
  );
}

const STEPS = [
  {
    title: "It assumes a read-only role",
    body: "The role carries two AWS managed policies, SecurityAudit and ViewOnlyAccess, and nothing else. The scanner can look at everything and change nothing.",
  },
  {
    title: "It runs 22 checks in every region",
    body: "Each check is one small Python file that looks for one common mistake. They run in parallel across every region enabled in the account.",
  },
  {
    title: "It ranks what it found",
    body: "Every finding names the exact resource, says why it matters and gives the fix. The worst ones come first.",
  },
];

// Real output from a scan of this project's own AWS account, with the
// account ID replaced.
const TRANSCRIPT = [
  { prompt: true, text: "python -m scanner --profile pillarscan --out findings.json" },
  { text: "Ran 22 checks against account 000000000000" },
  { text: "  40 failed, 19 passed, 0 errored" },
  { text: "  high: 3" },
  { text: "  medium: 35" },
  { text: "  low: 2" },
  { text: "Findings written to findings.json" },
];

export function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="mx-auto grid max-w-6xl scroll-mt-16 gap-x-16 gap-y-10 px-4 py-[clamp(4rem,9vw,7rem)] sm:px-6 lg:grid-cols-[5fr_6fr]"
    >
      <div>
        <SectionHeading
          title="One command, under a minute."
          lead="There is no agent to install and nothing to set up inside the account being scanned."
        />
        <ol className="mt-8">
          {STEPS.map((step) => (
            <li key={step.title} className="border-t border-night-line py-5">
              <h3 className="text-lg font-semibold">{step.title}</h3>
              <p className="mt-1.5 leading-relaxed text-pretty text-on-night-muted">{step.body}</p>
            </li>
          ))}
        </ol>
      </div>

      <figure className="self-start lg:sticky lg:top-24">
        <pre className="overflow-x-auto rounded-xl border border-night-line bg-night-raised p-5 font-mono text-[0.8125rem] leading-7 sm:p-6 sm:text-sm sm:leading-7">
          {TRANSCRIPT.map((line) => (
            <span key={line.text} className={line.prompt ? "block text-on-night" : "block text-on-night-muted"}>
              {line.prompt && <span className="text-sound-bright select-none">$ </span>}
              {line.text}
            </span>
          ))}
        </pre>
        <figcaption className="mt-3 text-[0.8125rem] text-on-night-muted">
          Real output from a scan of this project&apos;s own AWS account: 17 regions in 52
          seconds.
        </figcaption>
      </figure>
    </section>
  );
}

/** Every check the scanner runs, read from the scan data so it cannot drift. */
export function Checks({ findings }: { findings: Finding[] }) {
  const checks = [...new Map(findings.map((finding) => [finding.check_id, finding])).values()].sort(
    (a, b) => SEVERITIES.indexOf(a.severity) - SEVERITIES.indexOf(b.severity),
  );

  return (
    <section id="checks" className="scroll-mt-16 border-y border-night-line bg-night-raised">
      <div className="mx-auto max-w-6xl px-4 py-[clamp(4rem,9vw,7rem)] sm:px-6">
      <SectionHeading
        title={`${checks.length} checks across three pillars.`}
        lead="The pillars come from the AWS Well-Architected Framework. Each check looks for one specific, common mistake."
      />
      <div className="mt-10 grid gap-x-10 gap-y-10 md:grid-cols-3">
        {PILLARS.map((pillar) => {
          const own = checks.filter((check) => check.pillar === pillar);
          return (
            <div key={pillar}>
              <h3 className="flex items-baseline justify-between border-b border-night-line pb-3 text-lg font-semibold">
                {PILLAR_LABELS[pillar]}
                <span className="text-sm font-normal text-on-night-muted">{own.length} checks</span>
              </h3>
              <ul>
                {own.map((check) => (
                  <li
                    key={check.check_id}
                    className="flex items-start justify-between gap-4 border-b border-night-line py-2.5"
                  >
                    <span className="text-pretty">{check.title}</span>
                    <SeverityMark
                      severity={check.severity}
                      className="pt-0.5 text-[0.8125rem] text-on-night-muted"
                    />
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
      </div>
    </section>
  );
}

const PROGRESS = [
  {
    done: true,
    title: "Scanner",
    body: "A command-line tool with 22 checks, each tested against mocked AWS.",
  },
  {
    done: true,
    title: "Dashboard",
    body: "This page: a posture score, the pillars and a findings table with fixes.",
  },
  {
    done: true,
    title: "Scan history",
    body: "A daily scan on Lambda, stored in DynamoDB and served by an API.",
  },
  {
    done: true,
    title: "Connect your own account",
    body: "Sign in by invitation, create the read-only role in one click, and scan from the browser.",
  },
];

export function Progress() {
  return (
    <section id="status" className="mx-auto max-w-6xl scroll-mt-16 px-4 py-[clamp(4rem,9vw,7rem)] sm:px-6">
      <div className="grid gap-10 lg:grid-cols-[5fr_7fr]">
        <div>
          <h2 className="text-[clamp(1.75rem,3.4vw,2.5rem)] leading-tight font-semibold tracking-[-0.02em] text-balance">
            A portfolio project, built in the open.
          </h2>
          <p className="mt-3 text-lg leading-relaxed text-pretty text-on-night-muted">
            Pillarscan is not a company or a product. It is one engineer&apos;s working
            answer to &ldquo;show me you understand AWS&rdquo;.
          </p>
          <p className="mt-4 leading-relaxed text-pretty text-on-night-muted">
            The scanner is Python with boto3, tested with pytest and moto. The infrastructure
            is Terraform. This site is Next.js and TypeScript.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <a
              href="#demo"
              className="inline-flex h-12 items-center justify-center rounded-md bg-sound-bright px-5 font-semibold text-night transition-transform duration-150 ease-out active:scale-[0.97]"
            >
              Open the live demo
            </a>
            <a
              href={REPO_URL}
              className="inline-flex h-12 items-center justify-center rounded-md border border-night-line px-5 font-semibold transition-colors duration-150 hover:border-on-night-muted"
            >
              Read the source
            </a>
          </div>
        </div>
        <ul className="grid content-start gap-x-8 sm:grid-cols-2">
          {PROGRESS.map((item) => (
            <li key={item.title} className="flex gap-3 border-t border-night-line py-4">
              {item.done ? (
                <Check className="mt-0.5 size-5 shrink-0 text-sound-bright" aria-hidden="true" />
              ) : (
                <CircleDashed className="mt-0.5 size-5 shrink-0 text-on-night-muted" aria-hidden="true" />
              )}
              <div>
                <h3 className="font-semibold">
                  {item.title}{" "}
                  <span className="font-normal text-on-night-muted">
                    · {item.done ? "built" : "planned"}
                  </span>
                </h3>
                <p className="mt-1 text-pretty text-on-night-muted">{item.body}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

const FOOTER_LINK = "text-on-night underline decoration-night-line underline-offset-4 transition-colors duration-150 hover:decoration-on-night";

export function Footer() {
  return (
    <footer className="border-t border-night-line">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <Mark className="size-5" sound="var(--sound-bright)" />
            <span className="font-semibold tracking-tight">Pillarscan</span>
          </Link>
          <p className="flex flex-col gap-1 text-on-night-muted sm:flex-row sm:gap-6">
            <span>
              Built by{" "}
              <a href={AUTHOR_URL} className={FOOTER_LINK}>
                Asiwome Boateng
              </a>
            </span>
            <span>
              Powered by{" "}
              <a href={LYTAWORKS_URL} className={FOOTER_LINK}>
                LytaWorks
              </a>
            </span>
          </p>
        </div>
        <p className="mt-8 max-w-3xl text-[0.8125rem] leading-relaxed text-pretty text-on-night-muted">
          The scanner is read-only and never calls a write API. Pillarscan is an independent
          project and is not affiliated with, endorsed by or sponsored by Amazon. AWS and its
          service names are trademarks of Amazon.com, Inc. or its affiliates.
        </p>
      </div>
    </footer>
  );
}
