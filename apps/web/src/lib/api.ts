import { getSupabase } from "./supabase";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface ApiOptions {
    method?: "GET" | "POST" | "PATCH" | "DELETE";
    body?: unknown;
    orgId?: string;
    signal?: AbortSignal;
    /** For public endpoints that require no auth. */
    anonymous?: boolean;
}

async function bearer(): Promise<string | null> {
    const supa = getSupabase();
    if (!supa) return null;
    const { data } = await supa.auth.getSession();
    return data.session?.access_token ?? null;
}

export async function api<T>(path: string, opts: ApiOptions = {}): Promise<T> {
    const headers: Record<string, string> = { "content-type": "application/json" };

    if (!opts.anonymous) {
        const token = await bearer();
        if (token) headers.authorization = `Bearer ${token}`;
    }
    if (opts.orgId) headers["x-organization-id"] = opts.orgId;

    const res = await fetch(`${BASE}${path}`, {
        method: opts.method ?? "GET",
        headers,
        body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
        signal: opts.signal,
    });
    if (!res.ok) {
        const detail = await res.text();
        throw new Error(`${res.status} ${res.statusText}: ${detail}`);
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
}
