/**
 * Next.js 16 Proxy — shared-password auth gate.
 *
 * Runs on every non-static request. If the signed auth cookie is missing
 * or invalid, redirects to /login (with a `callbackUrl` param).
 *
 * Note: proxy runs on every prefetch, so we keep it cheap — a single
 * HMAC verify per request. No external calls, no DB.
 */

import { NextResponse, type NextRequest } from "next/server";
import { AUTH_COOKIE_NAME, verifyCookieValue } from "@/lib/auth";

const PUBLIC_PATHS = new Set<string>(["/login"]);
const PUBLIC_PREFIXES = ["/api/login", "/api/logout"];

function isPublic(pathname: string): boolean {
  if (PUBLIC_PATHS.has(pathname)) return true;
  return PUBLIC_PREFIXES.some((p) => pathname.startsWith(p));
}

export function proxy(req: NextRequest): NextResponse {
  const { pathname, search } = req.nextUrl;

  if (isPublic(pathname)) return NextResponse.next();

  const cookie = req.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (verifyCookieValue(cookie)) return NextResponse.next();

  const loginUrl = new URL("/login", req.nextUrl);
  loginUrl.searchParams.set("callbackUrl", pathname + search);
  return NextResponse.redirect(loginUrl);
}

// Skip static assets and image optimizer.
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon\\.ico|.*\\.png$).*)"],
};
