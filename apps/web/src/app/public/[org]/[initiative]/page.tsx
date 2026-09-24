import Link from "next/link";

interface Summary {
    initiative_id: string;
    org_slug: string;
    org_name: string;
    initiative_slug: string;
    initiative_name: string;
    description: string | null;
    category: string | null;
    status: string;
    contribution_count: number;
    contribution_total: string;
    allocated_total: string;
    paid_total: string;
    unallocated_total: string;
    allocation_pct: string;
}

interface ResourceRow {
    resource_name: string;
    unit: string;
    received: string;
    distributed: string;
    damaged: string;
    lost: string;
    disposed: string;
}

interface FlagRow {
    event_id: string;
    event_type: string;
    quantity: string;
    reason: string | null;
    created_at: string;
}

interface AnchorRow {
    id: string;
    merkle_root: string;
    event_count: number;
    chain_id: number;
    contract_address: string | null;
    tx_hash: string | null;
    block_number: number | null;
    status: string;
    submitted_at: string | null;
    confirmed_at: string | null;
}

interface PageData {
    summary: Summary;
    resources: ResourceRow[];
    reconciliation_flags: FlagRow[];
    anchor_batches: AnchorRow[];
}

// Next 16's dynamic route props expose params as a Promise.
type PageProps = { params: Promise<{ org: string; initiative: string }> };

async function fetchDetail(org: string, initiative: string): Promise<PageData | null> {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    try {
        const res = await fetch(
            `${base}/api/v1/public/organizations/${encodeURIComponent(org)}/initiatives/${encodeURIComponent(initiative)}`,
            { cache: "no-store" },
        );
        if (!res.ok) return null;
        return (await res.json()) as PageData;
    } catch {
        return null;
    }
}

export default async function InitiativePublicPage({ params }: PageProps) {
    const { org, initiative } = await params;
    const data = await fetchDetail(org, initiative);

    if (!data) {
        return (
            <main className="mx-auto max-w-3xl px-6 py-16">
                <h1 className="text-2xl font-semibold">Initiative not found</h1>
                <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">
                    Either the initiative does not exist, or the backend at{" "}
                    <code>NEXT_PUBLIC_API_BASE_URL</code> is not reachable.
                </p>
                <Link href="/" className="mt-6 inline-block text-sm underline">
                    ← Back to home
                </Link>
            </main>
        );
    }

    const { summary, resources, reconciliation_flags, anchor_batches } = data;

    return (
        <main className="mx-auto max-w-5xl px-6 py-12">
            <p className="text-sm text-zinc-500">
                <Link href="/" className="hover:underline">ImpactLedger</Link>
                {" / "}
                {summary.org_name}
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">
                {summary.initiative_name}
            </h1>
            {summary.description && (
                <p className="mt-3 max-w-3xl text-zinc-600 dark:text-zinc-400">
                    {summary.description}
                </p>
            )}
            <div className="mt-2 inline-block rounded-full bg-zinc-900 px-3 py-1 text-xs uppercase tracking-wider text-white dark:bg-white dark:text-zinc-900">
                {summary.status}
            </div>

            <section className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <Stat label="Contributions" value={summary.contribution_total} count={summary.contribution_count} />
                <Stat label="Allocated" value={summary.allocated_total} />
                <Stat label="Paid" value={summary.paid_total} />
                <Stat label="Unallocated" value={summary.unallocated_total} />
            </section>

            <section className="mt-14">
                <h2 className="text-xl font-semibold">Physical resources</h2>
                {resources.length === 0 ? (
                    <p className="mt-3 text-sm text-zinc-500">No resource movements recorded yet.</p>
                ) : (
                    <table className="mt-4 w-full text-sm">
                        <thead className="text-left text-xs uppercase text-zinc-500">
                            <tr>
                                <th className="py-2">Resource</th>
                                <th>Unit</th>
                                <th className="text-right">Received</th>
                                <th className="text-right">Distributed</th>
                                <th className="text-right">Lost/Damaged/Disposed</th>
                            </tr>
                        </thead>
                        <tbody>
                            {resources.map((r) => (
                                <tr key={r.resource_name} className="border-t border-zinc-200 dark:border-zinc-800">
                                    <td className="py-2">{r.resource_name}</td>
                                    <td>{r.unit}</td>
                                    <td className="text-right">{r.received}</td>
                                    <td className="text-right">{r.distributed}</td>
                                    <td className="text-right">
                                        {Number(r.lost) + Number(r.damaged) + Number(r.disposed)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>

            <section className="mt-14">
                <h2 className="text-xl font-semibold">Reconciliation flags</h2>
                <p className="mt-1 text-sm text-zinc-500">
                    Rulebook Rule 08 — discrepancies remain visible.
                </p>
                {reconciliation_flags.length === 0 ? (
                    <p className="mt-3 text-sm text-zinc-500">No reconciliation flags.</p>
                ) : (
                    <ul className="mt-4 space-y-2">
                        {reconciliation_flags.map((f) => (
                            <li key={f.event_id} className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950/40">
                                <span className="font-medium">{f.event_type}</span>
                                {" — "}
                                qty {f.quantity}
                                {f.reason ? ` (${f.reason})` : ""}{" "}
                                <span className="text-xs text-zinc-500">{f.created_at}</span>
                            </li>
                        ))}
                    </ul>
                )}
            </section>

            <section className="mt-14">
                <h2 className="text-xl font-semibold">Cryptographic anchors</h2>
                <p className="mt-1 text-sm text-zinc-500">
                    Rulebook §22 — Merkle roots anchored to Base Sepolia.
                </p>
                {anchor_batches.length === 0 ? (
                    <p className="mt-3 text-sm text-zinc-500">No anchor batches yet.</p>
                ) : (
                    <table className="mt-4 w-full text-sm">
                        <thead className="text-left text-xs uppercase text-zinc-500">
                            <tr>
                                <th className="py-2">Batch</th>
                                <th>Events</th>
                                <th>Status</th>
                                <th>Transaction</th>
                            </tr>
                        </thead>
                        <tbody>
                            {anchor_batches.map((a) => (
                                <tr key={a.id} className="border-t border-zinc-200 dark:border-zinc-800">
                                    <td className="py-2 font-mono text-xs">{a.id.slice(0, 8)}…</td>
                                    <td>{a.event_count}</td>
                                    <td>{a.status}</td>
                                    <td>
                                        {a.tx_hash ? (
                                            <a
                                                className="font-mono text-xs underline"
                                                href={`https://sepolia.basescan.org/tx/${a.tx_hash}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                            >
                                                {a.tx_hash.slice(0, 10)}…
                                            </a>
                                        ) : (
                                            "—"
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>
        </main>
    );
}

function Stat({ label, value, count }: { label: string; value: string; count?: number }) {
    return (
        <div className="rounded-2xl border border-zinc-200 p-5 dark:border-zinc-800">
            <div className="text-xs uppercase tracking-wider text-zinc-500">{label}</div>
            <div className="mt-2 text-2xl font-semibold">{value}</div>
            {typeof count === "number" && (
                <div className="mt-1 text-xs text-zinc-500">{count.toLocaleString()} entries</div>
            )}
        </div>
    );
}
