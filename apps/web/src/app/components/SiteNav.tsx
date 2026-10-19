"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS: { href: string; label: string; match?: string }[] = [
  { href: "/", label: "Overview" },
  {
    href: "/public/demo-relief/flood-relief-2026",
    label: "Public transparency",
    match: "/public",
  },
  { href: "/lab/impact-assessment", label: "Assessment lab" },
  { href: "/method", label: "Method" },
];

export function SiteNav() {
  const pathname = usePathname();

  return (
    <nav className="site-nav" aria-label="Primary">
      {LINKS.map((link) => {
        const prefix = link.match ?? link.href;
        const active =
          prefix === "/"
            ? pathname === "/"
            : pathname === prefix || pathname.startsWith(`${prefix}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            style={
              active
                ? {
                    background: "var(--accent-soft)",
                    color: "var(--accent)",
                    fontWeight: 600,
                  }
                : undefined
            }
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
