"use client";

import { useState } from "react";
import { BarChart, LineChart } from "@/components/Charts";
import type { TeamSummary } from "@/lib/data";

export function OverviewCharts({ team }: { team: TeamSummary }) {
  const [ltView, setLtView] = useState<"weekly" | "monthly">("weekly");

  const weeklyLabels = team.weekly_closed?.map((w) => w.week) ?? [];
  const weeklyClosedData = team.weekly_closed?.map((w) => w.count) ?? [];

  // 起案数を週次クローズと同じ週ラベルで揃える（zip by week label）
  const createdByWeek = new Map(
    (team.weekly_created ?? []).map((w) => [w.week, w.count]),
  );
  const weeklyCreatedData = weeklyLabels.map((w) => createdByWeek.get(w) ?? 0);
  // 閉じ率（クローズ ÷ 起案）を % で。起案 0 の週は null（線が切れる）
  const rateByWeek = new Map(
    (team.weekly_close_rate ?? []).map((r) => [r.week, r.rate]),
  );
  const weeklyCloseRatePct = weeklyLabels.map((w) => {
    const r = rateByWeek.get(w);
    return r === undefined || r === null ? null : Math.round(r * 100);
  });

  const ltMonthlyLabels = team.monthly_leadtime?.map((m) => m.month) ?? [];
  const ltMonthlyAvg = team.monthly_leadtime?.map((m) => m.avg_days) ?? [];
  const ltMonthlyMedian = team.monthly_leadtime?.map((m) => m.median_days) ?? [];

  const ltWeeklyLabels = team.weekly_leadtime?.map((w) => w.week) ?? [];
  const ltWeeklyAvg = team.weekly_leadtime?.map((w) => w.avg_days) ?? [];
  const ltWeeklyMedian = team.weekly_leadtime?.map((w) => w.median_days) ?? [];

  const ltLabels = ltView === "weekly" ? ltWeeklyLabels : ltMonthlyLabels;
  const ltAvg = ltView === "weekly" ? ltWeeklyAvg : ltMonthlyAvg;
  const ltMedian = ltView === "weekly" ? ltWeeklyMedian : ltMonthlyMedian;
  const ltSource = ltView === "weekly" ? team.weekly_leadtime ?? [] : team.monthly_leadtime ?? [];
  const ltOutlierTotal = ltSource.reduce((s, x) => s + (x.outlier_count ?? 0), 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white dark:bg-gray-900 rounded-xl p-5 border border-gray-100 dark:border-gray-800 shadow-sm">
        <BarChart
          title="週次クローズ件数 vs 起案件数（折れ線=起案 / 閉じ率%）"
          labels={weeklyLabels}
          datasets={[{ label: "クローズ", data: weeklyClosedData, backgroundColor: "rgba(99,102,241,0.65)" }]}
          lineDatasets={[
            { label: "起案", data: weeklyCreatedData, borderColor: "#10b981", backgroundColor: "rgba(16,185,129,0.15)" },
            { label: "閉じ率 (%)", data: weeklyCloseRatePct as number[], borderColor: "#f59e0b", backgroundColor: "rgba(245,158,11,0.15)", yAxisID: "y1" },
          ]}
        />
        <p className="mt-2 text-[10px] text-gray-400">※ 閉じ率 = 同一週内クローズ ÷ 起案。100% を超える週は前週以前の積み上がりを消化したことを示す。長期チケットは反映遅れあり。</p>
      </div>
      <div className="bg-white dark:bg-gray-900 rounded-xl p-5 border border-gray-100 dark:border-gray-800 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">リードタイム推移</h3>
          <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
            <button
              onClick={() => setLtView("weekly")}
              className={`px-3 py-1 text-xs rounded-md transition-all ${
                ltView === "weekly"
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm font-medium"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700"
              }`}
            >
              週次
            </button>
            <button
              onClick={() => setLtView("monthly")}
              className={`px-3 py-1 text-xs rounded-md transition-all ${
                ltView === "monthly"
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm font-medium"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700"
              }`}
            >
              月次
            </button>
          </div>
        </div>
        <LineChart
          labels={ltLabels}
          datasets={[
            { label: "平均", data: ltAvg, borderColor: "#6366f1", backgroundColor: "rgba(99,102,241,0.08)" },
            { label: "中央値", data: ltMedian, borderColor: "#06b6d4", backgroundColor: "rgba(6,182,212,0.08)" },
          ]}
        />
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          P95 を超える外れ値 {ltOutlierTotal} 件を除外して集計
        </p>
      </div>
    </div>
  );
}
