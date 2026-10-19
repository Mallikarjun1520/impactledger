import Link from "next/link";

const LIFECYCLE = [
  {
    step: "Contribution",
    detail: "Money or resources are recorded as received, with a reference to the source.",
  },
  {
    step: "Allocation",
    detail: "Funds are committed to an initiative or purpose, bounded by what was received.",
  },
  {
    step: "Procurement",
    detail: "An allocation becomes a purchase or commitment, linked to what it paid for.",
  },
  {
    step: "Receipt",
    detail: "Physical resources are recorded as received into a tracked batch.",
  },
  {
    step: "Movement",
    detail: "Transfers, losses, damage and disposals are recorded as they happen.",
  },
  {
    step: "Distribution",
    detail: "Every distributed unit is tied to a destination and a date.",
  },
  {
    step: "Reconciliation",
    detail: "Expected balances are compared with physical counts; differences stay visible.",
  },
  {
    step: "Anchoring",
    detail: "A hash of the recorded events is anchored, so later edits can be detected.",
  },
];

export default function Home() {
  return (
    <main className="container-x py-12 sm:py-16">
      <section className="max-w-3xl">
        <p className="kpi-label">Traceable relief funding &amp; resources</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">
          ImpactLedger
        </h1>
        <p className="mt-5 text-lg" style={{ color: "var(--text-muted)" }}>
          ImpactLedger records the lifecycle of relief funds and physical
          resources — contributions, allocations, procurement, receipts,
          movements and distributions — and keeps the missing links and
          discrepancies visible instead of hiding them.
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link href="/lab/impact-assessment" className="btn btn-primary">
            Try the assessment lab
          </Link>
          <Link
            href="/public/demo-relief/flood-relief-2026"
            className="btn btn-secondary"
          >
            View a transparency record
          </Link>
        </div>
      </section>

      <div className="alert alert-info mt-8 max-w-3xl" role="note">
        <span aria-hidden="true">ⓘ</span>
        <p>
          ImpactLedger records and reconciles <strong>what was reported</strong>.
          It does not by itself prove that an activity happened. Anchoring shows
          that a record has not been changed since it was written — not that the
          record is true.
        </p>
      </div>

      <section aria-labelledby="capabilities-heading" className="mt-14">
        <h2 id="capabilities-heading" className="text-xl font-semibold">
          What the system does
        </h2>
        <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <Feature title="Append-only events">
            Every recorded contribution, allocation, purchase, receipt and
            distribution is an append-only event. Corrections and reversals are
            new events, never edits.
          </Feature>
          <Feature title="Deterministic rules">
            Restrictions, allocation caps and physical conservation are enforced
            by code that either accepts or refuses — never by a model.
          </Feature>
          <Feature title="Evidence stays private">
            Invoices, delivery notes and photos stay in private storage. Only
            their SHA-256 hash participates in the anchored Merkle root.
          </Feature>
          <Feature title="Discrepancies stay visible">
            Recorded vs. observed and expected vs. received are shown as they
            are. Nothing is smoothed over to make an organisation look better.
          </Feature>
        </div>
      </section>

      <section aria-labelledby="lifecycle-heading" className="mt-14">
        <h2 id="lifecycle-heading" className="text-xl font-semibold">
          The recorded lifecycle
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
          Each stage is an append-only event, linked to the stage before it.
        </p>
        <ol className="mt-5 grid gap-4 sm:grid-cols-2">
          {LIFECYCLE.map((item, index) => (
            <li key={item.step} className="card card-pad flex gap-4">
              <span
                className="mono flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
                style={{
                  background: "var(--accent-soft)",
                  color: "var(--accent)",
                }}
                aria-hidden="true"
              >
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <p className="font-medium">{item.step}</p>
                <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                  {item.detail}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section
        aria-labelledby="discrepancies-heading"
        className="card card-pad mt-14"
      >
        <h2 id="discrepancies-heading" className="text-xl font-semibold">
          Transparency that includes the discrepancies
        </h2>
        <p className="mt-3 max-w-3xl" style={{ color: "var(--text-muted)" }}>
          Most dashboards show only the totals that make an organization look
          good. ImpactLedger&apos;s public view also exposes reconciliation flags:
          quantities received but not distributed, distribution records that
          exceed receipts, and physical counts that disagree with the expected
          balance.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href="/public/demo-relief/flood-relief-2026"
            className="btn btn-secondary"
          >
            See a worked example
          </Link>
          <Link href="/method" className="btn btn-ghost">
            Read the method &amp; limitations
          </Link>
        </div>
      </section>

      <section aria-labelledby="lab-heading" className="mt-14">
        <div className="card card-pad flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="max-w-xl">
            <h2 id="lab-heading" className="text-xl font-semibold">
              Interactive Impact Assessment Lab
            </h2>
            <p className="mt-2" style={{ color: "var(--text-muted)" }}>
              Enter a hypothetical scenario and see whether its financial and
              physical records reconcile. It runs entirely in your browser and
              shows the inputs behind every finding.
            </p>
          </div>
          <Link
            href="/lab/impact-assessment"
            className="btn btn-primary shrink-0"
          >
            Open the lab
          </Link>
        </div>
      </section>
    </main>
  );
}

function Feature({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card card-pad">
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
        {children}
      </p>
    </div>
  );
}
