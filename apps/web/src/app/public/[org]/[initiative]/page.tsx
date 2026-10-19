import type { Metadata } from "next";
import Link from "next/link";

interface Summary {
    org_name: string;
    initiative_name: string;
    description: string | null;
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
    status: string;
    tx_hash: string | null;
}

interface PageData {
    summary: Summary;
    resources: ResourceRow[];
    reconciliation_flags: FlagRow[];
    anchor_batches: AnchorRow[];
}

type FetchResult =
    | { kind: "ok"; data: PageData }
    | { kind: "not-found" }
    | { kind: "error"; status: number | null };

async function fetchDetail(org: string, initiative: string): Promise<FetchResult> {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    try {
        const res = await fetch(
            `${base}/api/v1/public/organizations/${encodeURIComponent(org)}/initiatives/${encodeURIComponent(initiative)}`,
            { cache: "no-store" },
        );
        if (res.status === 404) return { kind: "not-found" };
        if (!res.ok) return { kind: "error", status: res.status };
        return { kind: "ok", data: (await res.json()) as PageData };
    } catch {
        return { kind: "error", status: null };
    }
}

export async function generateMetadata({
    params,
}: {
    params: Promise<{ org: string; initiative: string }>;
}): Promise<Metadata> {
    const { org, initiative } = await params;
    return {
        title: `${initiative} · ${org}`,
        description: `Public transparency record for ${initiative} published by ${org}.`,
    };
}

function anchorBadgeClass(status: string): string {
    const s = status.toLowerCase();
    if (s.includes("confirm") || s.includes("anchor") || s.includes("success")) {
        return "badge badge-ok";
    }
    if (s.includes("fail") || s.includes("error")) {
        return "badge badge-danger";
    }
    if (s.includes("pend") || s.includes("queue")) {
        return "badge badge-warn";
    }
    return "badge badge-neutral";
}

export default async function InitiativePublicPage({
    params,
}: {
    params: Promise<{ org: string; initiative: string }>;
}) {
    const { org, initiative } = await params;
    const result = await fetchDetail(org, initiative);

    if (result.kind === "not-found") {
        return (
            <main className="container-x py-16">
                <h1 className="text-2xl font-semibold">Initiative not found</h1>
                <p className="mt-3 text-sm" style={{ color: "var(--text-muted)" }}>
                    No public transparency record exists for this organization and
                    initiative.
                </p>
                <Link href="/" className="btn btn-secondary mt-6">
                    Back to home
                </Link>
            </main>
        );
    }

    if (result.kind === "error") {
        return (
            <main className="container-x py-16">
                <div className="alert alert-danger max-w-2xl" role="alert">
                    <span aria-hidden="true">⚠</span>
                    <div>
                        <h1 className="text-lg font-semibold">
                            Transparency data unavailable
                        </h1>
                        <p className="mt-1 text-sm">
                            We could not load this initiative&apos;s public
                            transparency record
                            {result.status ? ` (HTTP ${result.status})` : ""}. This
                            is not the same as saying there are no records — the data
                            may exist but could not be retrieved.
                        </p>
                    </div>
                </div>
                <Link href="/" className="btn btn-secondary mt-6">
                    Back to home
                </Link>
            </main>
        );
    }

    const { summary, resources, reconciliation_flags, anchor_batches } =
        result.data;

    return (
        <main className="container-x py-10">
            <nav className="text-sm" aria-label="Breadcrumb">
                <Link href="/" className="hover:underline" style={{ color: "var(--text-muted)" }}>
                    ImpactLedger
                </Link>
                <span aria-hidden="true" style={{ color: "var(--text-subtle)" }}>
                    {" / "}
                </span>
                <span style={{ color: "var(--text-muted)" }}>{summary.org_name}</span>
            </nav>

            <header className="mt-3">
                <div className="flex flex-wrap items-center gap-3">
                    <h1 className="text-3xl font-semibold tracking-tight">
                        {summary.initiative_name}
                    </h1>
                    <span className="badge badge-neutral">{summary.status}</span>
                </div>
                {summary.description && (
                    <p className="mt-3 max-w-3xl" style={{ color: "var(--text-muted)" }}>
                        {summary.description}
                    </p>
                )}
                <p className="mt-2 text-sm" style={{ color: "var(--text-subtle)" }}>
                    Published by {summary.org_name}
                </p>
            </header>

            <section aria-labelledby="summary-heading" className="mt-8">
                <h2 id="summary-heading" className="sr-only">
                    Financial summary
                </h2>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <Stat
                        label="Contributions"
                        value={summary.contribution_total}
                        hint={`${summary.contribution_count.toLocaleString()} recorded entries`}
                    />
                    <Stat label="Allocated" value={summary.allocated_total} />
                    <Stat label="Paid" value={summary.paid_total} />
                    <Stat
                        label="Unallocated"
                        value={summary.unallocated_total}
                        hint={`${summary.allocation_pct}% of contributions allocated`}
                    />
                </div>
                <p className="help mt-3">
                    Totals reflect what was recorded. A large unallocated figure
                    means funds are received but not yet committed — not that they
                    are missing.
                </p>
            </section>

            <section aria-labelledby="resources-heading" className="mt-12">
                <h2 id="resources-heading" className="text-xl font-semibold">
                    Physical resources
                </h2>
                {resources.length === 0 ? (
                    <p className="mt-3 text-sm" style={{ color: "var(--text-muted)" }}>
                        No resource movements recorded yet.
                    </p>
                ) : (
                    <div className="card mt-4 overflow-x-auto">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th scope="col">Resource</th>
                                    <th scope="col">Unit</th>
                                    <th scope="col" className="num">
                                        Received
                                    </th>
                                    <th scope="col" className="num">
                                        Distributed
                                    </th>
                                    <th scope="col" className="num">
                                        Lost / damaged / disposed
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {resources.map((r) => (
                                    <tr key={r.resource_name}>
                                        <td>{r.resource_name}</td>
                                        <td>{r.unit}</td>
                                        <td className="num">{r.received}</td>
                                        <td className="num">{r.distributed}</td>
                                        <td className="num">
                                            {Number(r.lost) +
                                                Number(r.damaged) +
                                                Number(r.disposed)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>

            <section aria-labelledby="flags-heading" className="mt-12">
                <h2 id="flags-heading" className="text-xl font-semibold">
                    Reconciliation flags
                </h2>
                <p className="help mt-1">
                    Discrepancies between recorded and expected figures remain
                    visible. Rulebook Rule 08.
                </p>
                {reconciliation_flags.length === 0 ? (
                    <p className="mt-3 text-sm" style={{ color: "var(--text-muted)" }}>
                        No reconciliation flags recorded.
                    </p>
                ) : (
                    <ul className="mt-4 flex flex-col gap-2">
                        {reconciliation_flags.map((f) => (
                            <li key={f.event_id} className="alert alert-warn">
                                <span aria-hidden="true">!</span>
                                <div>
                                    <p className="font-medium text-sm">{f.event_type}</p>
                                    <p className="text-sm">
                                        Quantity {f.quantity}
                                        {f.reason ? ` — ${f.reason}` : ""}
                                    </p>
                                    <p className="help mono">{f.created_at}</p>
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </section>

            <section aria-labelledby="anchors-heading" className="mt-12">
                <h2 id="anchors-heading" className="text-xl font-semibold">
                    Cryptographic anchors
                </h2>
                <p className="help mt-1">
                    Merkle roots anchored to Base Sepolia. Anchoring shows a record
                    has not changed since it was anchored — not that it is true.
                </p>
                {anchor_batches.length === 0 ? (
                    <p className="mt-3 text-sm" style={{ color: "var(--text-muted)" }}>
                        No anchor batches recorded yet.
                    </p>
                ) : (
                    <div className="card mt-4 overflow-x-auto">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th scope="col">Batch</th>
                                    <th scope="col" className="num">
                                        Events
                                    </th>
                                    <th scope="col">Status</th>
                                    <th scope="col">Transaction</th>
                                </tr>
                            </thead>
                            <tbody>
                                {anchor_batches.map((a) => (
                                    <tr key={a.id}>
                                        <td className="mono text-xs">
                                            {a.id.slice(0, 8)}…
                                        </td>
                                        <td className="num">{a.event_count}</td>
                                        <td>
                                            <span className={anchorBadgeClass(a.status)}>
                                                {a.status}
                                            </span>
                                        </td>
                                        <td>
                                            {a.tx_hash ? (
                                                <a
                                                    className="mono text-xs underline"
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
                    </div>
                )}
            </section>

            <div className="alert alert-info mt-12" role="note">
                <span aria-hidden="true">ⓘ</span>
                <p>
                    This page shows what was reported for this initiative. To
                    understand how the figures are reconciled and what the result
                    does not prove, see the{" "}
                    <Link href="/method" className="underline">
                        method &amp; limitations
                    </Link>
                    .
                </p>
            </div>
        </main>
    );
}

function Stat({
    label,
    value,
    hint,
}: {
    label: string;
    value: string;
    hint?: string;
}) {
    return (
        <div className="kpi">
            <p className="kpi-label">{label}</p>
            <p className="kpi-value">{value}</p>
            {hint && <p className="kpi-hint">{hint}</p>}
        </div>
    );
}
