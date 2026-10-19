import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Method & limitations",
  description:
    "How ImpactLedger assesses relief-operation records, what its deterministic rules check, and what the result cannot tell you.",
};

const RULES = [
  {
    title: "Unknown is never treated as zero",
    body: "A field left blank means the figure was not provided. It is never silently coerced to 0, because that would manufacture a finding the records do not support.",
  },
  {
    title: "Only supplied terms are used",
    body: "Expected balances are computed from the terms you actually provided. If receipts or losses are missing, the equation is not padded with assumptions.",
  },
  {
    title: "Every finding names its inputs",
    body: "Each finding lists the exact figures that triggered it, so a reader can reproduce the conclusion instead of trusting a black box.",
  },
  {
    title: "Evidence coverage counts references, not existence",
    body: "A reference string counts as evidence coverage. The assessment does not confirm that the referenced document exists or that it supports the claim.",
  },
  {
    title: "Discrepancies stay visible",
    body: "Reconciliation differences, unmatched resources and rejected comparisons are reported, never suppressed to make a result look cleaner.",
  },
];

export default function MethodPage() {
  return (
    <main className="container-x py-12">
      <article className="prose-lite max-w-3xl">
        <p className="kpi-label">Reference</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">
          Method &amp; limitations
        </h1>
        <p className="mt-4">
          ImpactLedger assesses the internal consistency of the figures that
          were reported for a relief operation. This page explains the rules the
          assessment applies, and — just as importantly — what the result cannot
          tell you.
        </p>

        <h2>What the assessment checks</h2>
        <ul>
          <li>
            <strong>Financial:</strong> whether allocations exceed recorded
            contributions, and whether expenditure exceeds the approved
            allocation.
          </li>
          <li>
            <strong>Resources</strong>: whether distributions exceed recorded
            receipts, and whether a physical count agrees with the expected
            balance.
          </li>
          <li>
            <strong>Destinations</strong>: whether the destination breakdown
            accounts for the recorded distribution total, and whether it
            references resources that are not tracked.
          </li>
          <li>
            <strong>Linkage</strong>: whether a resource batch identifies the
            money that funded it, and whether a funding reference is reused
            ambiguously.
          </li>
          <li>
            <strong>Evidence</strong>: the share of records that carry a
            document or receipt reference.
          </li>
          <li>
            <strong>Completeness</strong>: which inputs are missing that would
            be needed to reach a conclusion.
          </li>
        </ul>
      </article>

      <section aria-labelledby="rules-heading" className="mt-14">
        <h2 id="rules-heading" className="text-xl font-semibold">
          Invariants the engine holds to
        </h2>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {RULES.map((rule) => (
            <div key={rule.title} className="card card-pad">
              <h3 className="font-semibold">{rule.title}</h3>
              <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                {rule.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      <article className="prose-lite mt-14 max-w-3xl">
        <h2>Reconciliation formulas</h2>
        <p>
          Expected remaining quantity is computed from the terms provided:
        </p>
        <pre className="panel mono mt-3 overflow-x-auto text-sm">
{`expected remaining =
    opening quantity
  + receipts
  + transfers in
  − distributions
  − transfers out
  − losses
  − disposals`}
        </pre>
        <p className="mt-4">
          A physical count is compared against that expected balance. A non-zero
          variance is reported as a warning rather than resolved automatically.
        </p>

        <h2 className="mt-8">What the result cannot tell you</h2>
        <ul>
          <li>
            It assesses only the figures entered. It does not read
            ImpactLedger&apos;s database and does not verify that any activity
            actually happened.
          </li>
          <li>
            It assumes a single currency for all amounts; it does not convert
            between currencies.
          </li>
          <li>
            It counts evidence references but does not verify the documents
            behind them.
          </li>
          <li>
            A &ldquo;consistent&rdquo; result means the records are internally
            coherent — not that they are true.
          </li>
        </ul>

        <h2 className="mt-8">Anchoring, in one paragraph</h2>
        <p>
          ImpactLedger can anchor a hash of its recorded events to a public
          blockchain. Anchoring shows that the record has not been altered since
          it was anchored. It does not make the record true, and it is not a
          substitute for verification of the underlying activity.
        </p>
      </article>

      <div className="card card-pad mt-14 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-xl text-sm" style={{ color: "var(--text-muted)" }}>
          Put the method to work on your own hypothetical figures in the
          assessment lab.
        </p>
        <Link href="/lab/impact-assessment" className="btn btn-primary shrink-0">
          Open the lab
        </Link>
      </div>
    </main>
  );
}
