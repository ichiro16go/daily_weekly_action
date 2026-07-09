import type { Metadata } from "next";
import { getCalendarData, getWeeklyClosedTickets } from "@/lib/data";
import { CalendarView } from "./CalendarView";

export const metadata: Metadata = {
  title: "Calendar | 運用保守チーム Dashboard",
  description: "担当者ごとの未完了チケットを月次で確認できるチームカレンダー",
};

export default function CalendarPage() {
  const calendar = getCalendarData();
  const closedTickets = getWeeklyClosedTickets();

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">🗓️ チームカレンダー</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            メンバーごとの未完了チケットを月次のガント風ビューで確認できます。
          </p>
        </div>
        {calendar.generated_at && (
          <span className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-800 px-3 py-1 rounded-full">
            最終更新: {new Date(calendar.generated_at).toLocaleString("ja-JP")}
          </span>
        )}
      </div>

      <CalendarView data={calendar} closedTickets={closedTickets} />
    </div>
  );
}
