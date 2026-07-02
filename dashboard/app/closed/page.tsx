import { getWeeklyClosedTickets } from "@/lib/data";
import Link from "next/link";

export default async function ClosedThisWeekPage({
  searchParams,
}: {
  searchParams?: Promise<{ week?: string }>;
}) {
  const params = (await searchParams) ?? {};
  const data = getWeeklyClosedTickets();
  const weeks = Array.isArray(data.weeks) ? data.weeks : [];

  if (weeks.length === 0) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">✅ 週次クローズ一覧</h1>
        <p className="text-gray-500">
          データがまだ生成されていません。次回の update-dashboard 実行後に表示されます。
        </p>
      </div>
    );
  }

  const selectedWeekStart = params.week ?? weeks[0].week_start;
  const selected = weeks.find((w) => w.week_start === selectedWeekStart) ?? weeks[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">✅ 週次クローズ一覧</h1>
        <span className="text-sm text-gray-500">
          {selected.week_start} 〜 {selected.week_end}（{selected.count} 件）
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {weeks.map((w) => {
          const active = w.week_start === selected.week_start;
          return (
            <Link
              key={w.week_start}
              href={`/closed?week=${w.week_start}`}
              className={`px-3 py-1.5 rounded-lg text-sm border transition-all ${
                active
                  ? "bg-indigo-50 dark:bg-indigo-950 border-indigo-200 dark:border-indigo-900 text-indigo-700 dark:text-indigo-300 font-medium"
                  : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
              }`}
            >
              {w.label}
              <span className="ml-1.5 text-xs text-gray-400">({w.count})</span>
            </Link>
          );
        })}
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800 text-gray-500">
            <tr>
              <th className="px-4 py-2 text-left w-8">#</th>
              <th className="px-4 py-2 text-left">チケット</th>
              <th className="px-4 py-2 text-left">担当</th>
              <th className="px-4 py-2 text-left">タイプ</th>
              <th className="px-4 py-2 text-left">完了日時</th>
              <th className="px-4 py-2 text-right">LT</th>
            </tr>
          </thead>
          <tbody>
            {selected.tickets.map((t, i) => (
              <tr key={t.key} className="border-t border-gray-100 dark:border-gray-800">
                <td className="px-4 py-2 text-gray-400">{i + 1}</td>
                <td className="px-4 py-2">
                  <a
                    href={t.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {t.key}
                  </a>
                  <span className="ml-2">{t.summary}</span>
                </td>
                <td className="px-4 py-2 whitespace-nowrap">{t.assignee}</td>
                <td className="px-4 py-2 whitespace-nowrap text-gray-500">
                  {t.issuetype}
                  {t.is_subtask && (
                    <span className="ml-1 text-xs text-gray-400">(sub)</span>
                  )}
                </td>
                <td className="px-4 py-2 whitespace-nowrap text-gray-500">
                  {t.resolved_at ?? "—"}
                </td>
                <td className="px-4 py-2 text-right whitespace-nowrap">
                  {t.lead_time_days === null ? (
                    "—"
                  ) : (
                    <span
                      className={
                        t.lead_time_days > 30
                          ? "text-red-600 dark:text-red-400 font-semibold"
                          : t.lead_time_days > 14
                          ? "text-orange-500"
                          : ""
                      }
                    >
                      {t.lead_time_days}日
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {selected.tickets.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  この週のクローズはありません
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
