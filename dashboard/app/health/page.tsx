import { getStaleRanking, getOverdueRanking, getNeglectedRanking, getLabelCohort } from "@/lib/data";

const CLOSE_STATUSES = ["Done", "完了", "Close", "Resolved", "解決済み", "リリース済み"];
const DEFAULT_BASE_URL = "https://epark-tech.atlassian.net";

function openIssuesUrl(baseUrl: string, label: string) {
  const statusFilter = CLOSE_STATUSES.map((s) => `"${s}"`).join(", ");
  const jql = `labels = "${label}" AND status NOT IN (${statusFilter}) ORDER BY updated DESC`;
  return `${baseUrl}/issues/?jql=${encodeURIComponent(jql)}`;
}

function formatRate(rate: number) {
  return `${rate.toFixed(1)}%`;
}

export default function HealthPage() {
  const stale = getStaleRanking();
  const overdue = getOverdueRanking();
  const neglected = getNeglectedRanking();
  const cohort = getLabelCohort();
  const cohorts = cohort.cohorts ?? [];
  const baseUrl = cohort.base_url ?? DEFAULT_BASE_URL;
  const totalTickets = cohorts.reduce((sum, item) => sum + item.total, 0);
  const totalClosed = cohorts.reduce((sum, item) => sum + item.closed, 0);
  const averageCloseRate = totalTickets > 0 ? (totalClosed / totalTickets) * 100 : 0;

  return (
    <div className="space-y-10">
      <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">🩺 チーム健全性</h1>

      {/* 滞留チケット */}
      <section>
        <h2 className="text-lg font-semibold mb-3 text-gray-700 dark:text-gray-200">🚨 滞留チケット（IN PROGRESS 日数順）</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800 text-gray-500">
              <tr>
                <th className="px-4 py-2 text-left w-8">#</th>
                <th className="px-4 py-2 text-left">チケット</th>
                <th className="px-4 py-2 text-left">担当者</th>
                <th className="px-4 py-2 text-right">滞留日数</th>
              </tr>
            </thead>
            <tbody>
              {(Array.isArray(stale) ? stale : []).map((t, i) => (
                <tr key={t.key} className="border-t border-gray-100 dark:border-gray-800">
                  <td className="px-4 py-2 text-gray-400">{i + 1}</td>
                  <td className="px-4 py-2">
                    <a href={t.url || "#"} target="_blank" rel="noopener noreferrer"
                      className="font-mono text-blue-600 dark:text-blue-400 hover:underline">{t.key}</a>
                    <span className="ml-2">{t.summary}</span>
                  </td>
                  <td className="px-4 py-2">{t.assignee}</td>
                  <td className="px-4 py-2 text-right font-bold">
                    <span className={t.days_stale > 14 ? "text-red-600" : t.days_stale > 7 ? "text-orange-500" : ""}>
                      {t.days_stale}日
                    </span>
                  </td>
                </tr>
              ))}
              {(!Array.isArray(stale) || stale.length === 0) && (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">滞留チケットなし 🎉</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* 期限超過チケット */}
      <section>
        <h2 className="text-lg font-semibold mb-3 text-gray-700 dark:text-gray-200">⚠️ 期限超過チケット（超過日数順）</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800 text-gray-500">
              <tr>
                <th className="px-4 py-2 text-left w-8">#</th>
                <th className="px-4 py-2 text-left">チケット</th>
                <th className="px-4 py-2 text-left">担当者</th>
                <th className="px-4 py-2 text-center">期限</th>
                <th className="px-4 py-2 text-right">超過日数</th>
              </tr>
            </thead>
            <tbody>
              {(Array.isArray(overdue) ? overdue : []).map((t, i) => (
                <tr key={t.key} className="border-t border-gray-100 dark:border-gray-800">
                  <td className="px-4 py-2 text-gray-400">{i + 1}</td>
                  <td className="px-4 py-2">
                    <a href={t.url || "#"} target="_blank" rel="noopener noreferrer"
                      className="font-mono text-blue-600 dark:text-blue-400 hover:underline">{t.key}</a>
                    <span className="ml-2">{t.summary}</span>
                  </td>
                  <td className="px-4 py-2">{t.assignee}</td>
                  <td className="px-4 py-2 text-center">{t.duedate}</td>
                  <td className="px-4 py-2 text-right font-bold text-red-600">{t.days_overdue}日</td>
                </tr>
              ))}
              {(!Array.isArray(overdue) || overdue.length === 0) && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">期限超過チケットなし 🎉</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* 放置チケット */}
      <section>
        <h2 className="text-lg font-semibold mb-3 text-gray-700 dark:text-gray-200">📥 放置チケット（起票日からの日数）</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800 text-gray-500">
              <tr>
                <th className="px-4 py-2 text-left w-8">#</th>
                <th className="px-4 py-2 text-left">チケット</th>
                <th className="px-4 py-2 text-left">担当</th>
                <th className="px-4 py-2 text-left">ステータス</th>
                <th className="px-4 py-2 text-center">起票日</th>
                <th className="px-4 py-2 text-right">経過日数</th>
              </tr>
            </thead>
            <tbody>
              {(Array.isArray(neglected) ? neglected : []).map((t, i) => (
                <tr key={t.key} className="border-t border-gray-100 dark:border-gray-800">
                  <td className="px-4 py-2 text-gray-400">{i + 1}</td>
                  <td className="px-4 py-2">
                    <a href={t.url || "#"} target="_blank" rel="noopener noreferrer"
                      className="font-mono text-blue-600 dark:text-blue-400 hover:underline">{t.key}</a>
                    <span className="ml-2">{t.summary}</span>
                  </td>
                  <td className="px-4 py-2">{t.assignee}</td>
                  <td className="px-4 py-2">{t.status}</td>
                  <td className="px-4 py-2 text-center">{t.created}</td>
                  <td className="px-4 py-2 text-right font-bold">
                    <span className={t.days_since_created >= 90 ? "text-red-600" : t.days_since_created >= 60 ? "text-orange-500" : t.days_since_created >= 30 ? "text-yellow-600" : ""}>
                      {t.days_since_created}日
                    </span>
                  </td>
                </tr>
              ))}
              {(!Array.isArray(neglected) || neglected.length === 0) && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">放置チケットなし 🎉</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* 期間ラベル別継続状況 */}
      <section>
        <div className="flex flex-wrap items-baseline justify-between gap-3 mb-3">
          <h2 className="text-lg font-semibold text-gray-700 dark:text-gray-200">🏷️ 期間ラベル別 継続状況</h2>
          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <span className="inline-flex items-center rounded-full px-2.5 py-1 bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">閉じ率 = 完了 ÷ 総件数</span>
            <span className="inline-flex items-center rounded-full px-2.5 py-1 bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300">継続率 = 継続中 ÷ 総件数</span>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 shadow-sm">
            <p className="text-xs text-gray-400 mb-1">対象ラベル数</p>
            <p className="text-2xl font-bold text-gray-800 dark:text-gray-100">{cohorts.length}</p>
          </div>
          <div className="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 shadow-sm">
            <p className="text-xs text-gray-400 mb-1">総チケット数</p>
            <p className="text-2xl font-bold text-gray-800 dark:text-gray-100">{totalTickets}</p>
          </div>
          <div className="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 shadow-sm">
            <p className="text-xs text-gray-400 mb-1">全体閉じ率</p>
            <p className="text-2xl font-bold text-gray-800 dark:text-gray-100">{averageCloseRate.toFixed(1)}%</p>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/80 text-gray-600 dark:text-gray-300">
              <tr>
                <th className="px-4 py-3 text-left">期間ラベル</th>
                <th className="px-4 py-3 text-right">総件数</th>
                <th className="px-4 py-3 text-right">完了</th>
                <th className="px-4 py-3 text-right">閉じ率</th>
                <th className="px-4 py-3 text-right">継続中</th>
                <th className="px-4 py-3 text-right">継続率</th>
              </tr>
            </thead>
            <tbody>
              {cohorts.map((item) => (
                <tr key={item.label}
                  className="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-100">
                    <a href={openIssuesUrl(baseUrl, item.label)} target="_blank" rel="noopener noreferrer"
                      className="text-indigo-600 dark:text-indigo-400 hover:underline">
                      {item.label} ↗
                    </a>
                  </td>
                  <td className="px-4 py-3 text-right">{item.total}</td>
                  <td className="px-4 py-3 text-right">{item.closed}</td>
                  <td className="px-4 py-3 text-right">
                    <span className="inline-flex min-w-20 justify-end rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                      {formatRate(item.close_rate)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">{item.open}</td>
                  <td className="px-4 py-3 text-right">
                    <span className="inline-flex min-w-20 justify-end rounded-full bg-amber-50 px-2.5 py-1 text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                      {formatRate(item.continuation_rate)}
                    </span>
                  </td>
                </tr>
              ))}
              {cohorts.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-gray-400">
                    表示できるコホートデータがありません。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-gray-400 mt-2">※ ラベルをクリックで Jira の継続中チケット一覧へ</p>
      </section>
    </div>
  );
}
