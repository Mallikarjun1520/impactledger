import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

let cached: SupabaseClient | null = null;

/**
 * Browser Supabase client. Returns null during SSR when env is missing so
 * the app can still render server components without a live Supabase.
 */
export function getSupabase(): SupabaseClient | null {
    if (!url || !anonKey) return null;
    if (!cached) {
        cached = createClient(url, anonKey, {
            auth: { persistSession: true, autoRefreshToken: true },
        });
    }
    return cached;
}
