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
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">チーム Overview</h1>
        {meta.updated_at && (
          <span className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-800 px-3 py-1 rounded-full">
            最終更新: {new Date(meta.updated_at).toLocaleString("ja-JP")}
          </span>
        )}
      </div>

      {/* KPI進捗 */}
      {kpi.targets && (
        <div className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-base font-semibold text-gray-700 dark:text-gray-200 mb-5">🎯 チームKPI（{kpi.half_label}）</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* 週完了数 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-500">週完了数</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  kpi.current.weekly_closed >= kpi.targets.weekly_closed
                    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                    : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
                }`}>
                  {kpi.current.weekly_closed >= kpi.targets.weekly_closed ? "達成" : "未達"}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-gray-900 dark:text-gray-50">{kpi.current.weekly_closed}</span>
                <span className="text-sm text-gray-400">件/週</span>
                <span className="text-xs text-gray-400 ml-auto">目標: {kpi.targets.weekly_closed}件</span>
              </div>
              <div className="mt-3 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-indigo-500 transition-all"
                  style={{ width: `${Math.min(100, (kpi.current.weekly_closed / kpi.targets.weekly_closed) * 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-2">
                {Math.round((kpi.current.weekly_closed / kpi.targets.weekly_closed) * 100)}% — 前期: {kpi.previous.weekly_closed}件/週
              </p>
            </div>
            {/* リードタイム中央値 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-500">リードタイム中央値</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  kpi.current.lead_time_median <= kpi.targets.lead_time_median
                    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                    : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
                }`}>
                  {kpi.current.lead_time_median <= kpi.targets.lead_time_median ? "達成" : "未達"}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-gray-900 dark:text-gray-50">{kpi.current.lead_time_median}</span>
                <span className="text-sm text-gray-400">日</span>
                <span className="text-xs text-gray-400 ml-auto">目標: {kpi.targets.lead_time_median}日以下</span>
              </div>
              <div className="mt-3 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-cyan-500 transition-all"
                  style={{ width: `${Math.min(100, (kpi.targets.lead_time_median / Math.max(kpi.current.lead_time_median, 1)) * 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-2">
                サンプル: {kpi.current.lead_time_sample_count}件
              </p>
            </div>
          </div>
          {/* 累計・予測 */}
          <div className="mt-6 pt-5 border-t border-gray-100 dark:border-gray-800 grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-xs text-gray-400 mb-1">上半期累計</p>
              <p className="text-xl font-bold text-gray-800 dark:text-gray-100">{kpi.current.total_closed}件</p>
              <p className="text-xs text-gray-400">{kpi.current.weeks_elapsed}週経過</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">9月末予測</p>
              <p className="text-xl font-bold text-gray-800 dark:text-gray-100">{kpi.projection.projected_total_at_current_pace}件</p>
              <p className="text-xs text-gray-400">残{kpi.projection.remaining_weeks}週</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">前期（{kpi.prev_label}）</p>
              <p className="text-xl font-bold text-gray-800 dark:text-gray-100">{kpi.previous.total_closed}件</p>
              <p className="text-xs text-gray-400">{kpi.previous.weekly_closed}件/週</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <MetricCard label="対応中 (WIP)" value={team.current_wip ?? 0} alert={(team.current_wip ?? 0) > (team.wip_limit ?? 3) * 7} />
        <MetricCard label="WIP上限/人" value={team.wip_limit ?? 3} />
        <MetricCard label="今週クローズ" value={team.weekly_closed?.at(-1)?.count ?? 0} />
        <MetricCard label="今週 新規起票" value={team.weekly_created?.at(-1)?.count ?? 0} />
        {(() => {
          const closed = team.weekly_closed?.at(-1)?.count ?? 0;
          const created = team.weekly_created?.at(-1)?.count ?? 0;
          const diff = closed - created;
          const diffLabel = diff > 0 ? `+${diff}` : `${diff}`;
          return (
            <MetricCard
              label="今週 差分 (クローズ−起案)"
              value={diffLabel}
              alert={diff < 0}
            />
          );
        })()}
        <MetricCard label="リードタイム(中央値)" value={`${team.monthly_leadtime?.at(-1)?.median_days ?? "-"}日`} />
      </div>

      {wip.members?.some((m) => m.over_limit) && (
        <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-xl p-4">
          <h3 className="font-semibold text-red-700 dark:text-red-300 text-sm mb-2">🚨 WIP上限超過</h3>
          <ul className="space-y-1 text-sm text-red-600 dark:text-red-400">
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

function MetricCard({ label, value, alert }: { label: string; value: number | string; alert?: boolean }) {
  return (
    <div className={`rounded-xl p-4 border transition-all ${
      alert
        ? "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-900"
        : "bg-white dark:bg-gray-900 border-gray-100 dark:border-gray-800 shadow-sm"
    }`}>
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${alert ? "text-red-600 dark:text-red-400" : "text-gray-800 dark:text-gray-100"}`}>{value}</p>
    </div>
  );
}
