import { getTeamSummary, getWipStatus, getMeta } from "@/lib/data";
import { OverviewCharts } from "./OverviewCharts";

export default function OverviewPage() {
  const team = getTeamSummary();
  const wip = getWipStatus();
  const meta = getMeta();

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
