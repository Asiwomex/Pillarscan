import { Dashboard } from "@/components/dashboard";
import { Hero } from "@/components/site/hero";
import { SiteHeader } from "@/components/site/site-header";
import { Checks, Footer, HowItWorks, Progress } from "@/components/site/sections";
import { loadScans } from "@/lib/scans";

export default function Home() {
  const scans = loadScans();
  // The demo scan covers every check, so the hero and the check list use it.
  const demo = scans[0].report.findings;

  return (
    <div id="top">
      <SiteHeader />
      <main>
        <Hero findings={demo} />
        <section id="demo" aria-label="Live demo" className="mx-auto max-w-6xl scroll-mt-20 px-2 sm:px-6">
          <h2 className="sr-only">Live demo</h2>
          <Dashboard scans={scans} />
        </section>
        <HowItWorks />
        <Checks findings={demo} />
        <Progress />
      </main>
      <Footer />
    </div>
  );
}
