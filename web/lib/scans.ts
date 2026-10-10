import { readFileSync } from "node:fs";
import path from "node:path";

import type { ScanReport } from "./findings";

export type Scan = {
  id: string;
  label: string;
  note: string;
  report: ScanReport;
};

// Demo mode reads the committed files in sample-data/ at the repo root.
// They are read at build time, so the deployed page is fully static.
const SAMPLE_DATA = path.join(process.cwd(), "..", "sample-data");

function read(file: string): ScanReport {
  return JSON.parse(readFileSync(path.join(SAMPLE_DATA, file), "utf-8")) as ScanReport;
}

export function loadScans(): Scan[] {
  return [
    {
      id: "demo",
      label: "Demo account",
      note:
        "A fictional company's account. The findings come from running the real scanner against mocked AWS, so every check has something to show.",
      report: read("demo-findings.json"),
    },
    {
      id: "real",
      label: "Live account",
      // Shown only if JavaScript is off; the dashboard swaps this scan for
      // the latest one from the API as soon as it is opened.
      note:
        "A saved scan of this project's own AWS account, with the account ID and resource IDs replaced.",
      report: read("findings.json"),
    },
  ];
}
