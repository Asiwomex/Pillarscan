import Link from "next/link";

import { Mark } from "@/components/site/mark";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-start justify-center px-4 sm:px-6">
      <Mark className="size-10" sound="var(--sound-bright)" />
      <h1 className="mt-6 text-[clamp(2rem,6vw,3rem)] leading-tight font-semibold tracking-[-0.02em]">
        Nothing was found at this address.
      </h1>
      <p className="mt-3 text-lg text-on-night-muted">
        The scanner checks AWS accounts, not this URL. The demo is on the home page.
      </p>
      <Link
        href="/"
        className="mt-8 inline-flex h-12 items-center rounded-md bg-sound-bright px-5 font-semibold text-night"
      >
        Go to the home page
      </Link>
    </main>
  );
}
