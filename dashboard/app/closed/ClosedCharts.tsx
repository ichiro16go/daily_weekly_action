"use client";

import { Bar, Chart } from "react-chartjs-2";
import { BarChart } from "@/components/Charts";
import type { TeamSummary, MemberStats } from "@/lib/data";

const MEMBER_COLORS = [
  "#3b82f6", "#ef4444", "#10b981", "#f59e0b",
  "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16",
];

export function ClosedCharts({
  team,
  memberStats,
}: {
  team: TeamSummary;
  memberStats: MemberStats;
}) {
  // ── 週次クローズ vs 起案 ──
  const weeklyLabels = team.weekly_closed?.map((w) => w.week) ?? [];
  const weeklyClosedData = team.weekly_closed?.map((w) => w.count) ?? [];
  const createdByWeek = new Map(
    (team.weekly_created ?? []).map((w) => [w.week, w.count])
  );
  const weeklyCreatedData = weeklyLabels.map((w) => createdByWeek.get(w) ?? 0);
  const rateByWeek = new Map(
    (team.weekly_close_rate ?? []).map((r) => [r.week, r.rate])
  );
  const weeklyCloseRatePct = weeklyLabels.map((w) => {
    const r = rateByWeek.get(w);
    return r === undefined || r === null ? null : Math.round(r * 100);
  });

  // ── メンバー別週次完了数（積み上げ棒） ──
  const members = memberStats.members ?? {};
  const memberNames = Object.keys(members).filter((n) => n !== "未アサイン");
  const memberWeekLabels =
    memberNames.length > 0
      ? (members[memberNames[0]]?.weeks?.map((w) => w.week) ?? [])
      : [];
  const memberDatasets = memberNames.map((name, i) => ({
    label: name,
    data: members[name]?.weeks?.map((w) => w.closed) ?? [],
    backgroundColor: MEMBER_COLORS[i % MEMBER_COLORS.length],
    stack: "stack",
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* クローズ vs 起案 */}
      <div className="bg-white dark:bg-gray-900 rounded-xl p-5 border border-gray-100 dark:border-gray-800 shadow-sm">
        <BarChart
          title="週次クローズ vs 起案件数"
          labels={weeklyLabels}
          datasets={[
            {
              label: "クローズ",
              data: weeklyClosedData,
              backgroundColor: "rgba(99,102,241,0.65)",
            },
          ]}
          lineDatasets={[
            {
              label: "起案",
              data: weeklyCreatedData,
              borderColor: "#10b981",
              backgroundColor: "rgba(16,185,129,0.15)",
            },
            {
              label: "閉じ率 (%)",
              data: weeklyCloseRatePct as number[],
              borderColor: "#f59e0b",
              backgroundColor: "rgba(245,158,11,0.15)",
              yAxisID: "y1",
            },
          ]}
        />
        <p className="mt-2 text-[10px] text-gray-400">
          ※ 閉じ率 = 同一週内クローズ ÷ 起案。100% 超は前週以前の消化を示す。
        </p>
      </div>

      {/* メンバー別週次完了数（積み上げ） */}
      <div className="bg-white dark:bg-gray-900 rounded-xl p-5 border border-gray-100 dark:border-gray-800 shadow-sm">
        <p className="text-sm text-gray-500 dark:text-gray-400 font-medium mb-3">
          メンバー別 週次完了数（参考）
        </p>
        {memberNames.length > 0 ? (
          <>
            <Bar
              data={{ labels: memberWeekLabels, datasets: memberDatasets }}
              options={{
                responsive: true,
                plugins: {
                  legend: {
                    position: "bottom",
                    labels: { boxWidth: 12, font: { size: 11 } },
                  },
                },
                scales: {
                  x: { stacked: true, grid: { display: false }, ticks: { font: { size: 11 } } },
                  y: { stacked: true, beginAtZero: true, grid: { color: "rgba(0,0,0,0.04)" }, ticks: { font: { size: 11 } } },
                },
              }}
            />
            <p className="mt-2 text-[10px] text-gray-400">
              ※ assignee の揺れあり（対応→確認→クローズ等）。参考値として扱うこと。
            </p>
          </>
        ) : (
          <p className="text-sm text-gray-400">データがありません</p>
        )}
      </div>
    </div>
  );
}
