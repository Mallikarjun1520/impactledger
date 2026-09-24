/**
 * Client-side Merkle verifier. Mirror of apps/api/app/services/merkle.py so
 * a public viewer can verify a proof against the on-chain root using only
 * hashes served by the platform.
 *
 * Uses the Web Crypto API. Runs in every modern browser and edge runtime.
 */

const LEAF_PREFIX = new Uint8Array([0x00]);
const NODE_PREFIX = new Uint8Array([0x01]);

async function sha256(bytes: Uint8Array): Promise<Uint8Array> {
    const buf = await crypto.subtle.digest("SHA-256", bytes);
    return new Uint8Array(buf);
}

function hexToBytes(hex: string): Uint8Array {
    const clean = hex.startsWith("0x") ? hex.slice(2) : hex;
    if (clean.length % 2 !== 0) throw new Error("Odd-length hex string");
    const out = new Uint8Array(clean.length / 2);
    for (let i = 0; i < out.length; i++) {
        out[i] = parseInt(clean.slice(i * 2, i * 2 + 2), 16);
    }
    return out;
}

function bytesToHex(b: Uint8Array): string {
    return Array.from(b, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function concat(a: Uint8Array, ...rest: Uint8Array[]): Uint8Array {
    const total = rest.reduce((n, x) => n + x.length, a.length);
    const out = new Uint8Array(total);
    out.set(a, 0);
    let offset = a.length;
    for (const r of rest) {
        out.set(r, offset);
        offset += r.length;
    }
    return out;
}

export async function leafHash(eventHashHex: string): Promise<Uint8Array> {
    return sha256(concat(LEAF_PREFIX, hexToBytes(eventHashHex)));
}

export async function nodeHash(left: Uint8Array, right: Uint8Array): Promise<Uint8Array> {
    return sha256(concat(NODE_PREFIX, left, right));
}

export interface MerkleStep {
    sibling: string;   // hex
    is_right: boolean;
}

export async function verifyMerkleProof(
    eventHashHex: string,
    proof: MerkleStep[],
    expectedRootHex: string,
): Promise<boolean> {
    let current = await leafHash(eventHashHex);
    for (const step of proof) {
        const sibling = hexToBytes(step.sibling);
        current = step.is_right ? await nodeHash(current, sibling) : await nodeHash(sibling, current);
    }
    return bytesToHex(current) === expectedRootHex.toLowerCase().replace(/^0x/, "");
}

export { bytesToHex, hexToBytes };
