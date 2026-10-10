// Fixed locale and time zone, so the server and the browser render the
// same text and hydration does not mismatch.
const TIMESTAMP = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

export function formatTimestamp(iso: string): string {
  return `${TIMESTAMP.format(new Date(iso))} UTC`;
}

const DAY = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

/** A short label for a scan in the history list: "9 Oct, 23:51". */
export function formatDay(iso: string): string {
  return DAY.format(new Date(iso));
}
