import { NextResponse, type NextRequest } from "next/server";
import { AUTH_COOKIE_NAME, SESSION_TTL_MS, checkPassword, issueCookieValue } from "@/lib/auth";

const LOGIN_ERROR_URL = (base: URL, callbackUrl: string) => {
  const u = new URL("/login", base);
  u.searchParams.set("error", "invalid");
  if (callbackUrl) u.searchParams.set("callbackUrl", callbackUrl);
  return u;
};

function safeCallback(raw: string | null): string {
  // Only allow same-origin absolute paths to prevent open-redirect.
  // Also reject legacy `/api/auth/*` paths left over from the previous
  // NextAuth-based implementation — those routes no longer exist and
  // would 404 the user immediately after signing in.
  if (!raw) return "/";
  if (!raw.startsWith("/") || raw.startsWith("//")) return "/";
  if (raw === "/login" || raw.startsWith("/login?")) return "/";
  if (raw.startsWith("/api/")) return "/";
  return raw;
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const form = await req.formData();
  const password = String(form.get("password") ?? "");
  const callbackUrl = safeCallback(String(form.get("callbackUrl") ?? "/"));

  if (!checkPassword(password)) {
    return NextResponse.redirect(LOGIN_ERROR_URL(req.nextUrl, callbackUrl), {
      status: 303,
    });
  }

  const dest = new URL(callbackUrl, req.nextUrl);
  const res = NextResponse.redirect(dest, { status: 303 });
  res.cookies.set({
    name: AUTH_COOKIE_NAME,
    value: issueCookieValue(),
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: Math.floor(SESSION_TTL_MS / 1000),
  });
  return res;
}
