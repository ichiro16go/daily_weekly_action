/**
 * Shared-password auth utilities for the 運用保守 dashboard.
 *
 * Design:
 *  - Single shared password stored in DASHBOARD_PASSWORD env.
 *  - On successful login, we set an HMAC-signed cookie of the form
 *    `<expiryEpochMs>.<hexHmac>`. The HMAC key is DASHBOARD_AUTH_SECRET.
 *  - Proxy verifies the cookie (constant-time HMAC compare + expiry check)
 *    on every request without needing any external session store.
 *  - Cookie flags: HttpOnly + Secure (in prod) + SameSite=Lax.
 *
 * Required env:
 *   DASHBOARD_PASSWORD     - shared password
 *   DASHBOARD_AUTH_SECRET  - HMAC secret (openssl rand -base64 32)
 */

import { createHmac, timingSafeEqual } from "node:crypto";

export const AUTH_COOKIE_NAME = "dashboard-auth";
export const SESSION_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

function requireSecret(): string {
  const s = process.env.DASHBOARD_AUTH_SECRET;
  if (!s || s.length < 16) {
    throw new Error("DASHBOARD_AUTH_SECRET must be set (>= 16 chars)");
  }
  return s;
}

function requirePassword(): string {
  const p = process.env.DASHBOARD_PASSWORD;
  if (!p) throw new Error("DASHBOARD_PASSWORD must be set");
  return p;
}

function sign(expiryMs: number, secret: string): string {
  return createHmac("sha256", secret).update(String(expiryMs)).digest("hex");
}

/** Timing-safe compare that tolerates unequal input lengths. */
function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a, "utf8");
  const bb = Buffer.from(b, "utf8");
  if (ab.length !== bb.length) return false;
  return timingSafeEqual(ab, bb);
}

/** Validate the submitted password against DASHBOARD_PASSWORD. */
export function checkPassword(submitted: string): boolean {
  const expected = requirePassword();
  return safeEqual(submitted, expected);
}

/** Build a signed cookie value valid for SESSION_TTL_MS from now. */
export function issueCookieValue(now: number = Date.now()): string {
  const expiry = now + SESSION_TTL_MS;
  const sig = sign(expiry, requireSecret());
  return `${expiry}.${sig}`;
}

/**
 * Verify a cookie value: parse `<expiry>.<sig>`, HMAC-recompute, timing-safe
 * compare, and check expiry. Returns true iff the cookie is valid and unexpired.
 */
export function verifyCookieValue(
  value: string | undefined,
  now: number = Date.now(),
): boolean {
  if (!value) return false;
  const dot = value.indexOf(".");
  if (dot <= 0 || dot === value.length - 1) return false;
  const expiryStr = value.slice(0, dot);
  const sig = value.slice(dot + 1);
  const expiry = Number(expiryStr);
  if (!Number.isFinite(expiry) || expiry <= now) return false;
  const secret = process.env.DASHBOARD_AUTH_SECRET;
  if (!secret) return false;
  const expected = sign(expiry, secret);
  return safeEqual(sig, expected);
}
