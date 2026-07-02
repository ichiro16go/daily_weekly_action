import { getMemberStats, getMemberLeadtime } from "@/lib/data";
import { MemberCharts } from "./MemberCharts";

export default function MembersPage() {
  const stats = getMemberStats();
  const leadtime = getMemberLeadtime();

  const memberNames = Object.keys(stats.members ?? {}).filter((n) => n !== "未アサイン");

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">👥 メンバー別分析</h1>

      {/* 対応中サマリーテーブル */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-4 py-2 text-left">メンバー</th>
              <th className="px-4 py-2 text-right">対応中</th>
              <th className="px-4 py-2 text-right">今週完了</th>
              <th className="px-4 py-2 text-right">WIP状態</th>
            </tr>
          </thead>
          <tbody>
            {memberNames.map((name) => {
              const m = stats.members[name];
              const lastWeek = m?.weeks?.at(-1)?.closed ?? 0;
              const overLimit = (m?.in_progress ?? 0) > (stats.wip_limit ?? 5);
              return (
                <tr key={name} className="border-t border-gray-100 dark:border-gray-800">
                  <td className="px-4 py-2 font-medium">{name}</td>
                  <td className={`px-4 py-2 text-right ${overLimit ? "text-red-600 font-bold" : ""}`}>
                    {m?.in_progress ?? 0}
                  </td>
                  <td className="px-4 py-2 text-right">{lastWeek}</td>
                  <td className="px-4 py-2 text-right">
                    {overLimit ? "🚨 超過" : "✅ 正常"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* グラフ */}
      <MemberCharts stats={stats} leadtime={leadtime} memberNames={memberNames} />
    </div>
  );
}
