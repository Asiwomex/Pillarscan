"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";

import type { Finding } from "@/lib/findings";
import { rowsByService } from "@/lib/services";

// The charting library is the heaviest script on the page. Loading it only
// when the chart is about to be seen keeps the first paint and first tap fast.
const ServiceChart = dynamic(() => import("@/components/service-chart"), { ssr: false });

/** Failed checks per AWS service, stacked by severity: where the problems are. */
export function ServiceChartFrame({ failed }: { failed: Finding[] }) {
  const rows = rowsByService(failed);
  const frame = useRef<HTMLDivElement>(null);
  const [near, setNear] = useState(false);

  useEffect(() => {
    const element = frame.current;
    if (!element) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setNear(true);
          observer.disconnect();
        }
      },
      { rootMargin: "300px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  if (rows.length === 0) {
    return <p className="text-muted-ink">No failed checks.</p>;
  }

  return (
    <figure>
      <figcaption className="sr-only">
        Failed checks by service.{" "}
        {rows.map((row) => `${row.service}: ${row.total}.`).join(" ")}
      </figcaption>
      {/* The height is fixed up front, so nothing moves when the chart arrives. */}
      <div ref={frame} style={{ height: rows.length * 26 + 8 }} aria-hidden="true">
        {near && <ServiceChart rows={rows} />}
      </div>
    </figure>
  );
}
