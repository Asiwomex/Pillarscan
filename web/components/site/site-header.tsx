"use client";

import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";

import { Mark } from "@/components/site/mark";
import { REPO_URL } from "@/lib/links";
import { cn } from "@/lib/utils";

const NAV = [
  { id: "demo", label: "Demo" },
  { id: "how-it-works", label: "How it works" },
  { id: "checks", label: "Checks" },
  { id: "status", label: "Status" },
];

// How far below the top of the window a section must reach to count as current.
const ACTIVE_LINE = 96;

/** The last section whose top has passed under the header, if any. */
function currentSection(): string | null {
  let current: string | null = null;
  for (const item of NAV) {
    const section = document.getElementById(item.id);
    if (section && section.getBoundingClientRect().top <= ACTIVE_LINE) current = item.id;
  }
  return current;
}

export function SiteHeader() {
  const [active, setActive] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 8);
      setActive(currentSection());
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-40 border-b bg-night transition-colors duration-150",
        scrolled || menuOpen ? "border-night-line" : "border-transparent",
      )}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <a href="#top" className="flex items-center gap-2.5" onClick={() => setMenuOpen(false)}>
          <Mark className="size-6" sound="var(--sound-bright)" />
          <span className="text-lg font-semibold tracking-tight">Pillarscan</span>
        </a>

        <nav aria-label="Sections" className="hidden items-center gap-1 text-sm md:flex">
          {NAV.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              aria-current={active === item.id ? "location" : undefined}
              className={cn(
                "rounded-md px-3 py-2 transition-colors duration-150 hover:text-on-night",
                active === item.id ? "bg-night-raised text-on-night" : "text-on-night-muted",
              )}
            >
              {item.label}
            </a>
          ))}
          <a
            href={REPO_URL}
            className="ml-3 rounded-md border border-night-line px-3 py-2 font-medium transition-colors duration-150 hover:border-on-night-muted"
          >
            Source
          </a>
        </nav>

        <button
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          aria-expanded={menuOpen}
          aria-controls="mobile-menu"
          className="flex size-11 items-center justify-center rounded-md border border-night-line md:hidden"
        >
          {menuOpen ? <X className="size-5" aria-hidden="true" /> : <Menu className="size-5" aria-hidden="true" />}
          <span className="sr-only">{menuOpen ? "Close menu" : "Open menu"}</span>
        </button>
      </div>

      {menuOpen && (
        <nav
          id="mobile-menu"
          aria-label="Sections"
          className="border-t border-night-line px-4 pt-2 pb-4 md:hidden"
        >
          {NAV.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              onClick={() => setMenuOpen(false)}
              aria-current={active === item.id ? "location" : undefined}
              className={cn(
                "flex h-12 items-center border-b border-night-line text-lg",
                active === item.id ? "text-sound-bright" : "text-on-night",
              )}
            >
              {item.label}
            </a>
          ))}
          <a
            href={REPO_URL}
            className="mt-4 flex h-12 items-center justify-center rounded-md border border-night-line font-semibold"
          >
            Read the source
          </a>
        </nav>
      )}
    </header>
  );
}
