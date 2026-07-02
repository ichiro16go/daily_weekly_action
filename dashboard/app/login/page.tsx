import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { AUTH_COOKIE_NAME, verifyCookieValue } from "@/lib/auth";

type SearchParams = Promise<{ callbackUrl?: string; error?: string }>;

const ERROR_MESSAGES: Record<string, string> = {
  invalid: "パスワードが違います。",
};

function safeCallback(raw: string | undefined): string {
  if (!raw) return "/";
  if (!raw.startsWith("/") || raw.startsWith("//")) return "/";
  if (raw === "/login" || raw.startsWith("/login?")) return "/";
  if (raw.startsWith("/api/")) return "/";
  return raw;
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { callbackUrl, error } = await searchParams;
  const safeCb = safeCallback(callbackUrl);

  const cookie = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (verifyCookieValue(cookie)) redirect(safeCb);

  const errorMessage = error ? ERROR_MESSAGES[error] ?? "認証エラーが発生しました。" : null;

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm p-8 space-y-6">
        <div className="space-y-1 text-center">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            運用保守 Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            パスワードを入力してください
          </p>
        </div>

        {errorMessage && (
          <div
            role="alert"
            className="text-sm text-red-700 bg-red-50 dark:bg-red-950/40 dark:text-red-300 border border-red-200 dark:border-red-900 rounded-md px-3 py-2"
          >
            {errorMessage}
          </div>
        )}

        <form method="post" action="/api/login" className="space-y-3">
          <input type="hidden" name="callbackUrl" value={safeCb} />
          <label className="block">
            <span className="sr-only">Password</span>
            <input
              type="password"
              name="password"
              required
              autoFocus
              autoComplete="current-password"
              className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="パスワード"
            />
          </label>
          <button
            type="submit"
            className="w-full inline-flex items-center justify-center rounded-md bg-indigo-600 text-white px-4 py-2 text-sm font-medium hover:bg-indigo-700 transition"
          >
            サインイン
          </button>
        </form>
      </div>
    </main>
  );
}
