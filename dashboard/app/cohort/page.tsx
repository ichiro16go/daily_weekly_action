import { getLabelCohort } from "@/lib/data";

const CLOSE_STATUSES = ["Done", "完了", "Close", "Resolved", "解決済み", "リリース済み"];
const DEFAULT_BASE_URL = "https://epark-tech.atlassian.net";

function openIssuesUrl(baseUrl: string, label: string) {
  const statusFilter = CLOSE_STATUSES.map((s) => `"${s}"`).join(", ");
  const jql = `labels = "${label}" AND status NOT IN (${statusFilter}) ORDER BY updated DESC`;
  return `${baseUrl}/issues/?jql=${encodeURIComponent(jql)}`;
}

export default function CohortPage() {
  const cohort = getLabelCohort();
  const cohorts = cohort.cohorts ?? [];
  const baseUrl = cohort.base_url ?? DEFAULT_BASE_URL;
  const totalTickets = cohorts.reduce((sum, item) => sum + item.total, 0);
  const totalClosed = cohorts.reduce((sum, item) => sum + item.closed, 0);
  const averageCloseRate = totalTickets > 0 ? (totalClosed / totalTickets) * 100 : 0;

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">🏷️ 期間ラベル別 継続状況</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          運用保守YYYYMM ラベルごとの総件数、閉じ率、継続率を確認できます。
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryCard label="対象ラベル数" value={`${cohorts.length}`} />
        <SummaryCard label="総チケット数" value={`${totalTickets}`} />
        <SummaryCard label="全体閉じ率" value={`${averageCloseRate.toFixed(1)}%`} />
      </div>

      <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 shadow-sm overflow-x-auto">
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
              <tr key={item.label} className="border-t border-gray-100 dark:border-gray-800">
                <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-100">
                  <a
                    href={openIssuesUrl(baseUrl, item.label)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
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
      </section>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 shadow-sm">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-800 dark:text-gray-100">{value}</p>
    </div>
  );
}

function formatRate(rate: number) {
  return `${rate.toFixed(1)}%`;
}
