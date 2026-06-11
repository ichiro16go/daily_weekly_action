import { getTeamSummary, getWipStatus, getMeta, getKpi } from "@/lib/data";
import { OverviewCharts } from "./OverviewCharts";

export default function OverviewPage() {
  const team = getTeamSummary();
  const wip = getWipStatus();
  const meta = getMeta();
  const kpi = getKpi();

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">📊 チーム Overview</h1>
        {meta.updated_at && (
          <span className="text-sm text-gray-500">
            最終更新: {new Date(meta.updated_at).toLocaleString("ja-JP")}
          </span>
        )}
      </div>

      {/* KPI進捗 */}
      {kpi.targets && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <h2 className="text-lg font-bold mb-4">🎯 チームKPI（{kpi.half_label}）</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 週完了数 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">週完了数</span>
                <span className={`text-sm font-bold ${kpi.current.weekly_closed >= kpi.targets.weekly_closed ? "text-green-600" : "text-amber-600"}`}>
                  {kpi.current.weekly_closed >= kpi.targets.weekly_closed ? "✅ 達成" : "📉 未達"}
                </span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold">{kpi.current.weekly_closed}</span>
                <span className="text-gray-500 mb-1">件/週</span>
                <span className="text-sm text-gray-400 mb-1">（目標: {kpi.targets.weekly_closed}件）</span>
              </div>
              <div className="mt-2 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${kpi.current.weekly_closed >= kpi.targets.weekly_closed ? "bg-green-500" : "bg-amber-500"}`}
                  style={{ width: `${Math.min(100, (kpi.current.weekly_closed / kpi.targets.weekly_closed) * 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {Math.round((kpi.current.weekly_closed / kpi.targets.weekly_closed) * 100)}% — 前期: {kpi.previous.weekly_closed}件/週
              </p>
            </div>
            {/* リードタイム中央値 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">リードタイム中央値</span>
                <span className={`text-sm font-bold ${kpi.current.lead_time_median <= kpi.targets.lead_time_median ? "text-green-600" : "text-amber-600"}`}>
                  {kpi.current.lead_time_median <= kpi.targets.lead_time_median ? "✅ 達成" : "📉 未達"}
                </span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold">{kpi.current.lead_time_median}</span>
                <span className="text-gray-500 mb-1">日</span>
                <span className="text-sm text-gray-400 mb-1">（目標: {kpi.targets.lead_time_median}日以下）</span>
              </div>
              <div className="mt-2 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${kpi.current.lead_time_median <= kpi.targets.lead_time_median ? "bg-green-500" : "bg-amber-500"}`}
                  style={{ width: `${Math.min(100, (kpi.targets.lead_time_median / Math.max(kpi.current.lead_time_median, 1)) * 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                サンプル: {kpi.current.lead_time_sample_count}件
              </p>
            </div>
          </div>
          {/* 累計・予測 */}
          <div className="mt-4 pt-4 border-t border-blue-200 dark:border-blue-700 grid grid-cols-3 gap-4 text-center text-sm">
            <div>
              <p className="text-gray-500">上半期累計</p>
              <p className="text-xl font-bold">{kpi.current.total_closed}件</p>
              <p className="text-xs text-gray-400">{kpi.current.weeks_elapsed}週経過</p>
            </div>
            <div>
              <p className="text-gray-500">9月末予測</p>
              <p className="text-xl font-bold">{kpi.projection.projected_total_at_current_pace}件</p>
              <p className="text-xs text-gray-400">残{kpi.projection.remaining_weeks}週</p>
            </div>
            <div>
              <p className="text-gray-500">前期（{kpi.prev_label}）</p>
              <p className="text-xl font-bold">{kpi.previous.total_closed}件</p>
              <p className="text-xs text-gray-400">{kpi.previous.weekly_closed}件/週</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="対応中 (WIP)" value={team.current_wip ?? 0} alert={(team.current_wip ?? 0) > (team.wip_limit ?? 3) * 7} />
        <KpiCard label="WIP上限/人" value={team.wip_limit ?? 3} />
        <KpiCard label="今週クローズ" value={team.weekly_closed?.at(-1)?.count ?? 0} />
        <KpiCard label="リードタイム(中央値)" value={`${team.monthly_leadtime?.at(-1)?.median_days ?? "-"}日`} />
      </div>

      {wip.members?.some((m) => m.over_limit) && (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 className="font-bold text-red-700 dark:text-red-300 mb-2">🚨 WIP上限超過</h3>
          <ul className="space-y-1 text-sm">
            {wip.members.filter((m) => m.over_limit).map((m) => (
              <li key={m.name}>
                <span className="font-medium">{m.name}</span>: {m.count}件（上限 {wip.wip_limit}件を超過）
              </li>
            ))}
          </ul>
        </div>
      )}

      <OverviewCharts team={team} />
    </div>
  );
}

function KpiCard({ label, value, alert }: { label: string; value: number | string; alert?: boolean }) {
  return (
    <div className={`rounded-lg p-4 shadow-sm border ${
      alert ? "bg-red-50 dark:bg-red-950 border-red-300" : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700"
    }`}>
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${alert ? "text-red-600" : ""}`}>{value}</p>
    </div>
  );
}
