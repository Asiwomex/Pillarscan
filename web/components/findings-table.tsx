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
  type FindingGroup,
} from "@/lib/findings";
import { cn } from "@/lib/utils";

const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
});

const helper = createColumnHelper<typeof features, FindingGroup>();

function compare(a: string | number, b: string | number): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

// Columns that drop out on narrow screens; the detail panel still has them.
const COLUMN_CLASS: Record<string, string> = {
  severity: "w-[5.5rem] sm:w-28",
  service: "hidden w-36 md:table-cell",
  region: "hidden w-40 lg:table-cell",
  status: "w-20 sm:w-32",
};

function regionLabel(group: FindingGroup): string {
  return group.regions.length > 1 ? `${group.regions.length} regions` : group.regions[0];
}

function buildColumns(onSelect: (group: FindingGroup) => void) {
  return helper.columns([
    // Severity and status sort by rank, not alphabetically.
    helper.accessor((group) => SEVERITIES.indexOf(group.finding.severity), {
      id: "severity",
      header: "Severity",
      sortFn: (a, b, id) => compare(a.getValue<number>(id), b.getValue<number>(id)),
      cell: ({ row }) => <SeverityMark severity={row.original.finding.severity} />,
    }),
    helper.accessor((group) => group.finding.title, {
      id: "title",
      header: "Finding",
      sortFn: (a, b, id) => compare(a.getValue<string>(id), b.getValue<string>(id)),
      cell: ({ row }) => (
        <>
          <button
            type="button"
            onClick={() => onSelect(row.original)}
            className="text-left font-medium underline-offset-4 group-hover:underline"
          >
            {row.original.finding.title}
          </button>
          <span className="mt-0.5 block font-mono text-xs break-all text-muted-ink">
            {resourceName(row.original.finding.resource_arn)}
          </span>
        </>
      ),
    }),
    helper.accessor((group) => serviceOf(group.finding), {
      id: "service",
      header: "Service",
      sortFn: (a, b, id) => compare(a.getValue<string>(id), b.getValue<string>(id)),
    }),
    helper.accessor((group) => regionLabel(group), {
      id: "region",
      header: "Region",
      sortFn: (a, b, id) => compare(a.getValue<string>(id), b.getValue<string>(id)),
      cell: ({ row }) =>
        row.original.regions.length > 1 ? (
          // The same setting, found in several regions, is one row.
          <span className="whitespace-nowrap">{regionLabel(row.original)}</span>
        ) : (
          <span className="font-mono text-xs whitespace-nowrap">{regionLabel(row.original)}</span>
        ),
    }),
    helper.accessor((group) => STATUSES.indexOf(group.finding.status), {
      id: "status",
      header: "Status",
      sortFn: (a, b, id) => compare(a.getValue<number>(id), b.getValue<number>(id)),
      cell: ({ row }) => <StatusMark status={row.original.finding.status} />,
    }),
  ]);
}

export function FindingsTable({
  groups,
  onSelect,
}: {
  groups: FindingGroup[];
  onSelect: (group: FindingGroup) => void;
}) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "severity", desc: false }]);
  const columns = useMemo(() => buildColumns(onSelect), [onSelect]);
  const table = useTable({
    features,
    columns,
    data: groups,
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
