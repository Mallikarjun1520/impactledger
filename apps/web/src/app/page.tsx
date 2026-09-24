import Link from "next/link";

export default function Home() {
    return (
        <main className="min-h-screen bg-zinc-50 text-zinc-900 dark:bg-black dark:text-zinc-100">
            <section className="mx-auto max-w-4xl px-6 py-24">
                <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
                    ImpactLedger
                </h1>
                <p className="mt-6 max-w-2xl text-lg text-zinc-600 dark:text-zinc-400">
                    Tracks and verifies the recorded lifecycle of funds and resources.
                    Immutable domain events, deterministic invariants, cryptographic
                    anchoring on Base Sepolia — so donors and auditors can see what
                    was recorded, how the records connect, and that the history has
                    not been silently rewritten.
                </p>

                <div className="mt-10 flex flex-wrap gap-4">
                    <Link
                        href="/public/demo-relief/flood-relief-2026"
                        className="rounded-full bg-zinc-900 px-6 py-3 text-sm font-medium text-white transition hover:bg-zinc-800 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
                    >
                        View a public initiative
                    </Link>
                    <a
                        href="https://sepolia.basescan.org"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="rounded-full border border-zinc-300 px-6 py-3 text-sm font-medium text-zinc-900 transition hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-100 dark:hover:bg-zinc-900"
                    >
                        Anchor chain: Base Sepolia
                    </a>
                </div>

                <div className="mt-16 grid gap-8 sm:grid-cols-2">
                    <Feature title="Immutable events">
                        Every recorded contribution, allocation, purchase, and
                        distribution becomes an append-only event. Corrections and
                        reversals are new events, never edits.
                    </Feature>
                    <Feature title="Deterministic rules">
                        Restrictions, allocation caps, physical conservation, and
                        segregation of duties are enforced by code that either
                        accepts or refuses — never by a model.
                    </Feature>
                    <Feature title="Off-chain evidence">
                        Invoices, delivery notes, and photos stay in private
                        storage. Only their SHA-256 participates in the on-chain
                        Merkle root.
                    </Feature>
                    <Feature title="Transparency that includes discrepancies">
                        The public view exposes reconciliation flags: recorded
                        vs. observed, expected vs. received. Nothing is hidden to
                        make an organization look better.
                    </Feature>
                </div>
            </section>
        </main>
    );
}

function Feature({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
            <h3 className="text-lg font-semibold">{title}</h3>
            <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
                {children}
            </p>
        </div>
    );
}
