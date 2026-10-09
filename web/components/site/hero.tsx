import { SEVERITY_COLOR } from "@/components/severity-mark";
import { PILLAR_LABELS, bySeverity, type Finding } from "@/lib/findings";
import { REPO_URL } from "@/lib/links";
import { summarisePillars } from "@/lib/score";

function blockColor(finding: Finding): string {
  if (finding.status === "pass") return "var(--sound-bright)";
  if (finding.status === "error") return "var(--night-line)";
  return SEVERITY_COLOR[finding.severity];
}

/**
 * The signature at full size: each pillar is a stack of blocks, one per
 * check, built from the ground up. Sound checks form the base and the
 * failures sit on top, where the cracks show.
 */
function HeroPillars({ findings }: { findings: Finding[] }) {
  const pillars = summarisePillars(findings);
  return (
    <div
      role="img"
      aria-label={`Three pillars built from blocks. ${pillars
        .map(
          (p) =>
            `${PILLAR_LABELS[p.pillar]}: score ${p.score} of 100, ${p.failed} checks failed.`,
        )
        .join(" ")}`}
      className="flex items-end justify-center gap-6 sm:gap-9"
    >
      {pillars.map((pillar, pillarIndex) => {
        // Reverse of worst-first, because the stack fills from the bottom.
        const stack = findings
          .filter((finding) => finding.pillar === pillar.pillar)
          .sort(bySeverity)
          .reverse();
        return (
          <div key={pillar.pillar} className="flex flex-col items-center gap-3">
            <div className="flex w-[5.25rem] flex-wrap-reverse gap-1 sm:w-[6.25rem]">
              {stack.map((finding, index) => (
                <span
                  key={`${finding.check_id}:${finding.resource_arn}:${finding.region}`}
                  className="size-[1.125rem] animate-sweep rounded-sm sm:size-[1.375rem]"
                  style={{
                    background: blockColor(finding),
                    animationDelay: `${300 + pillarIndex * 120 + index * 14}ms`,
                  }}
                />
              ))}
            </div>
            <div className="h-1.5 w-[calc(100%+1rem)] rounded-sm bg-night-line" />
            <p className="text-center text-sm">
              <span className="block font-semibold text-on-night">
                {PILLAR_LABELS[pillar.pillar]}
              </span>
              <span className="block whitespace-nowrap text-on-night-muted">
                {pillar.score} / 100
              </span>
            </p>
          </div>
        );
      })}
    </div>
  );
}

export function Hero({ findings }: { findings: Finding[] }) {
  return (
    <>
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-8 pb-14 sm:px-6 sm:pt-14 lg:grid-cols-[7fr_5fr] lg:pb-20">
        <div>
          <h1 className="text-[clamp(2.5rem,6.2vw,4.5rem)] leading-[1.02] font-semibold tracking-[-0.03em] text-balance">
            Find the cracks in your AWS account.
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-pretty text-on-night-muted">
            Pillarscan scans an account and ranks every weak spot across security, reliability
            and cost, with the fix for each one.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
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
          <p className="mt-5 text-[0.8125rem] text-on-night-muted">
            No sign-in. The demo below runs on sample data.
          </p>
        </div>

        <HeroPillars findings={findings} />
      </section>
    </>
  );
}
