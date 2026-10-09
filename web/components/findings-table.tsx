"use client";

import { useMemo, useState } from "react";
import {
  createColumnHelper,
  createSortedRowModel,
  rowSortingFeature,
  tableFeatures,
  useTable,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";

import { SeverityMark, StatusMark } from "@/components/severity-mark";
import {
  SEVERITIES,
  STATUSES,
  resourceName,
  serviceOf,
  type Finding,
} from "@/lib/findings";
import { cn } from "@/lib/utils";

const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
});

const helper = createColumnHelper<typeof features, Finding>();

function compare(a: string | number, b: string | number): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

// Columns that drop out on narrow screens; the detail panel still has them.
const COLUMN_CLASS: Record<string, string> = {
  severity: "w-[5.5rem] sm:w-28",
  service: "hidden w-36 md:table-cell",
  region: "hidden w-32 lg:table-cell",
  status: "w-20 sm:w-32",
};

function buildColumns(onSelect: (finding: Finding) => void) {
  return helper.columns([
    // Severity and status sort by rank, not alphabetically.
    helper.accessor((finding) => SEVERITIES.indexOf(finding.severity), {
      id: "severity",
      header: "Severity",
      sortFn: (a, b, id) => compare(a.getValue<number>(id), b.getValue<number>(id)),
      cell: ({ row }) => <SeverityMark severity={row.original.severity} />,
    }),
    helper.accessor("title", {
      header: "Finding",
      sortFn: (a, b, id) => compare(a.getValue<string>(id), b.getValue<string>(id)),
      cell: ({ row }) => (
        <>
          <button
            type="button"
            onClick={() => onSelect(row.original)}
            className="text-left font-medium underline-offset-4 group-hover:underline"
          >
            {row.original.title}
          </button>
          <span className="mt-0.5 block font-mono text-xs break-all text-muted-ink">
            {resourceName(row.original.resource_arn)}
          </span>
        </>
      ),
    }),
    helper.accessor((finding) => serviceOf(finding), {
      id: "service",
      header: "Service",
      sortFn: (a, b, id) => compare(a.getValue<string>(id), b.getValue<string>(id)),
    }),
    helper.accessor("region", {
      header: "Region",
      sortFn: (a, b, id) => compare(a.getValue<string>(id), b.getValue<string>(id)),
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.region}</span>,
    }),
    helper.accessor((finding) => STATUSES.indexOf(finding.status), {
      id: "status",
      header: "Status",
      sortFn: (a, b, id) => compare(a.getValue<number>(id), b.getValue<number>(id)),
      cell: ({ row }) => <StatusMark status={row.original.status} />,
    }),
  ]);
}

export function FindingsTable({
  findings,
  onSelect,
}: {
  findings: Finding[];
  onSelect: (finding: Finding) => void;
}) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "severity", desc: false }]);
  const columns = useMemo(() => buildColumns(onSelect), [onSelect]);
  const table = useTable({
    features,
    columns,
    data: findings,
    state: { sorting },
    onSortingChange: setSorting,
  });

  return (
    <table className="w-full border-collapse text-[0.8125rem]">
      <thead>
        {table.getHeaderGroups().map((group) => (
          <tr key={group.id} className="border-y border-line bg-page">
            {group.headers.map((header) => {
              const sorted = header.column.getIsSorted();
              const SortIcon =
                sorted === "asc" ? ArrowUp : sorted === "desc" ? ArrowDown : ChevronsUpDown;
              return (
                <th
                  key={header.id}
                  scope="col"
                  aria-sort={
                    sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : "none"
                  }
                  className={cn("px-3 py-2 text-left font-medium sm:px-5", COLUMN_CLASS[header.column.id])}
                >
                  <button
                    type="button"
                    onClick={header.column.getToggleSortingHandler()}
                    className={cn(
                      "inline-flex items-center gap-1 text-muted-ink hover:text-ink",
                      sorted && "text-ink",
                    )}
                  >
                    <table.FlexRender header={header} />
                    <SortIcon className={cn("size-3.5", !sorted && "opacity-50")} aria-hidden="true" />
                  </button>
                </th>
              );
            })}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr
            key={row.id}
            onClick={() => onSelect(row.original)}
            className="group cursor-pointer border-b border-line align-top transition-colors duration-150 last:border-b-0 hover:bg-page"
          >
            {row.getAllCells().map((cell) => (
              <td key={cell.id} className={cn("px-3 py-3 sm:px-5", COLUMN_CLASS[cell.column.id])}>
                <table.FlexRender cell={cell} />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
