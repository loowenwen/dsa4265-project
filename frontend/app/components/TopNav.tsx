"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS: Array<{ href: string; label: string }> = [
  { href: "/", label: "Home" },
  { href: "/apply", label: "Apply" },
  { href: "/result", label: "Results" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname.startsWith(href);
}

export default function TopNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-6 py-4 md:px-10">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Atlas Underwriting</p>
          <p className="text-sm font-semibold text-slate-900">Applicant Information Processor</p>
        </div>

        <nav aria-label="Primary" className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 p-1">
          {NAV_ITEMS.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
                  active
                    ? "bg-slate-900 text-white shadow-sm"
                    : "text-slate-600 hover:bg-white hover:text-slate-900"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
