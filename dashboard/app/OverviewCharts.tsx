"use client";

import { useState } from "react";
import { BarChart, LineChart } from "@/components/Charts";
import type { TeamSummary } from "@/lib/data";

export function OverviewCharts({ team }: { team: TeamSummary }) {
  const [ltView, setLtView] = useState<"weekly" | "monthly">("weekly");

  const weeklyLabels = team.weekly_closed?.map((w) => w.week) ?? [];
  const weeklyData = team.weekly_closed?.map((w) => w.count) ?? [];

  const ltMonthlyLabels = team.monthly_leadtime?.map((m) => m.month) ?? [];
  const ltMonthlyAvg = team.monthly_leadtime?.map((m) => m.avg_days) ?? [];
  const ltMonthlyMedian = team.monthly_leadtime?.map((m) => m.median_days) ?? [];

  const ltWeeklyLabels = team.weekly_leadtime?.map((w) => w.week) ?? [];
  const ltWeeklyAvg = team.weekly_leadtime?.map((w) => w.avg_days) ?? [];
  const ltWeeklyMedian = team.weekly_leadtime?.map((w) => w.median_days) ?? [];

  const ltLabels = ltView === "weekly" ? ltWeeklyLabels : ltMonthlyLabels;
  const ltAvg = ltView === "weekly" ? ltWeeklyAvg : ltMonthlyAvg;
  const ltMedian = ltView === "weekly" ? ltWeeklyMedian : ltMonthlyMedian;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white dark:bg-gray-900 rounded-xl p-5 border border-gray-100 dark:border-gray-800 shadow-sm">
        <BarChart
          title="週次クローズ件数"
          labels={weeklyLabels}
          datasets={[{ label: "クローズ", data: weeklyData, backgroundColor: "rgba(99,102,241,0.65)" }]}
        />
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
      </div>
    </div>
  );
}
