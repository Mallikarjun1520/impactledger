import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { SiteNav } from "./components/SiteNav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "ImpactLedger — traceable relief funding and resources",
    template: "%s · ImpactLedger",
  },
  description:
    "ImpactLedger records and verifies the lifecycle of relief funds and physical resources: contributions, allocations, procurement, receipts, movements and distributions — with the missing links and discrepancies shown, not hidden.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <header className="site-header">
          <div className="container-x site-header-inner">
            <Link href="/" className="brand" aria-label="ImpactLedger home">
              <span className="brand-mark" aria-hidden="true">
                IL
              </span>
              ImpactLedger
            </Link>
            <SiteNav />
          </div>
        </header>
        <div id="main" className="flex-1">
          {children}
        </div>
        <footer className="site-footer">
          <div className="container-x flex flex-col gap-2 py-8 sm:flex-row sm:items-center sm:justify-between">
            <p>
              ImpactLedger records what was reported. It does not by itself prove
              that an activity happened.
            </p>
            <nav className="flex gap-4" aria-label="Footer">
              <Link href="/method" className="hover:underline">
                Method &amp; limitations
              </Link>
              <Link href="/lab/impact-assessment" className="hover:underline">
                Assessment lab
              </Link>
            </nav>
          </div>
        </footer>
      </body>
    </html>
  );
}
