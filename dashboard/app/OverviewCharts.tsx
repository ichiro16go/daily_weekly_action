"use client";

import { BarChart, LineChart } from "@/components/Charts";
import type { TeamSummary } from "@/lib/data";

export function OverviewCharts({ team }: { team: TeamSummary }) {
  const weeklyLabels = team.weekly_closed?.map((w) => w.week) ?? [];
  const weeklyData = team.weekly_closed?.map((w) => w.count) ?? [];

  const ltLabels = team.monthly_leadtime?.map((m) => m.month) ?? [];
  const ltAvg = team.monthly_leadtime?.map((m) => m.avg_days) ?? [];
  const ltMedian = team.monthly_leadtime?.map((m) => m.median_days) ?? [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <BarChart
          title="週次クローズ件数"
          labels={weeklyLabels}
          datasets={[{ label: "クローズ", data: weeklyData, backgroundColor: "rgba(59,130,246,0.6)" }]}
        />
      </div>
      <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <LineChart
          title="リードタイム推移（月次）"
          labels={ltLabels}
          datasets={[
            { label: "平均", data: ltAvg, borderColor: "#f59e0b", backgroundColor: "rgba(245,158,11,0.1)" },
            { label: "中央値", data: ltMedian, borderColor: "#10b981", backgroundColor: "rgba(16,185,129,0.1)" },
          ]}
        />
      </div>
    </div>
  );
}
