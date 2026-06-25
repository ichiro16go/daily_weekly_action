import { getStaleRanking, getOverdueRanking, getNeglectedRanking } from "@/lib/data";

export default function RankingPage() {
  const stale = getStaleRanking();
  const overdue = getOverdueRanking();
  const neglected = getNeglectedRanking();

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">🏆 ランキング</h1>

      {/* 滞留チケット */}
      <section>
        <h2 className="text-lg font-semibold mb-3">🚨 滞留チケット（IN PROGRESS 日数順）</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800">
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
                    <a href={t.url || `#`} target="_blank" rel="noopener noreferrer"
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
        <h2 className="text-lg font-semibold mb-3">⚠️ 期限超過チケット（超過日数順）</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800">
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
                    <a href={t.url || `#`} target="_blank" rel="noopener noreferrer"
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
        <h2 className="text-lg font-semibold mb-3">📥 放置チケット（起票日からの日数）</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800">
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
                    <a href={t.url || `#`} target="_blank" rel="noopener noreferrer"
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
    </div>
  );
}
