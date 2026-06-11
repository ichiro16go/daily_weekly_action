"use client";

import { BarChart, LineChart } from "@/components/Charts";
import type { MemberStats, MemberLeadtime } from "@/lib/data";

const COLORS = [
  "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4",
];

export function MemberCharts({
  stats,
  leadtime,
  memberNames,
}: {
  stats: MemberStats;
  leadtime: MemberLeadtime;
  memberNames: string[];
}) {
  // 週次完了数の積み上げバー
  const weeks = stats.members?.[memberNames[0]]?.weeks?.map((w) => w.week) ?? [];
  const closedDatasets = memberNames.map((name, i) => ({
    label: name,
    data: stats.members[name]?.weeks?.map((w) => w.closed) ?? [],
    backgroundColor: COLORS[i % COLORS.length],
  }));

  // リードタイム（メンバー別折れ線）
  const ltMembers = Object.keys(leadtime.members ?? {}).filter((n) => n !== "未アサイン");
  const ltMonths = leadtime.members?.[ltMembers[0]]?.map((m) => m.month) ?? [];
  const ltDatasets = ltMembers.map((name, i) => ({
    label: name,
    data: leadtime.members[name]?.map((m) => m.median_days) ?? [],
    borderColor: COLORS[i % COLORS.length],
    backgroundColor: "transparent",
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <BarChart
          title="メンバー別 週次完了数"
          labels={weeks}
          datasets={closedDatasets}
        />
      </div>
      <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <LineChart
          title="メンバー別 リードタイム中央値（月次）"
          labels={ltMonths}
          datasets={ltDatasets}
        />
      </div>
    </div>
  );
}
