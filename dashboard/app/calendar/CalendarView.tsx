"use client";

import { useMemo, useState } from "react";
import type { CalendarData } from "@/lib/data";

const MEMBER_COLUMN_WIDTH = 176;
const DAY_COLUMN_WIDTH = 52;
const BAR_HEIGHT = 28;
const BAR_GAP = 8;

type VisibleTask = CalendarData["members"][string]["tasks"][number] & {
    start: Date;
    end: Date;
    rawStart: Date;
    rawEnd: Date;
    hasStartDate: boolean;
    hasDueDate: boolean;
    isBeforeRange: boolean;
    isAfterRange: boolean;
    lane: number;
    left: number;
    width: number;
};

export function CalendarView({ data }: { data: CalendarData }) {
    const initialDate = useMemo(
        () => (data.generated_at ? new Date(data.generated_at) : new Date()),
        [data.generated_at],
    );
    const [anchorDate, setAnchorDate] = useState(initialDate);

    const today = useMemo(
        () =>
            startOfDay(
                data.generated_at ? new Date(data.generated_at) : new Date(),
            ),
        [data.generated_at],
    );

    const range = useMemo(() => getMonthRange(anchorDate), [anchorDate]);

    const days = useMemo(
        () => listDays(range.start, range.end),
        [range.end, range.start],
    );
    const timelineWidth = days.length * DAY_COLUMN_WIDTH;
    const members = Object.entries(data.members ?? {});

    return (
        <section className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl shadow-sm">
            <div className="flex flex-col gap-4 border-b border-gray-100 dark:border-gray-800 px-4 py-4 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                        <NavButton
                            label="前月"
                            onClick={() =>
                                setAnchorDate(shiftAnchor(anchorDate, -1))
                            }
                        >
                            ←
                        </NavButton>
                        <NavButton
                            label="次月"
                            onClick={() =>
                                setAnchorDate(shiftAnchor(anchorDate, 1))
                            }
                        >
                            →
                        </NavButton>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                    <span className="font-medium text-sm text-gray-700 dark:text-gray-200">
                        {range.label}
                    </span>
                    <Legend
                        label="進行中"
                        className="bg-indigo-200 dark:bg-green-800 border-green-400 dark:border-green-600"
                    />
                    <Legend
                        label="未着手/対応待ち"
                        className="bg-gray-200 dark:bg-gray-700 border-gray-300 dark:border-gray-600"
                    />
                    <Legend
                        label="期限超過(〜6日)"
                        className="bg-red-200 dark:bg-red-800 border-red-400 dark:border-red-600"
                    />
                    <Legend
                        label="期限超過(7-13日)"
                        className="bg-red-300 dark:bg-red-800 border-red-500 dark:border-red-600"
                    />
                    <Legend
                        label="期限超過(14日〜)"
                        className="bg-red-400 dark:bg-red-700 border-red-600 dark:border-red-500"
                    />
                    <Legend
                        label="開始/終了日 未設定"
                        className="bg-amber-50 dark:bg-amber-950 border-amber-400 dark:border-amber-600 border-dashed"
                    />
                    <span>
                        終了日は 終了日(WBSGantt) を参照（未設定時は期限を使用）
                    </span>
                </div>
            </div>

            <div className="overflow-x-auto">
                <div
                    className="min-w-max"
                    style={{ width: MEMBER_COLUMN_WIDTH + timelineWidth }}
                >
                    <div className="flex border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/80">
                        <div
                            className="sticky left-0 z-20 flex shrink-0 items-center border-r border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/95 px-4 py-3 text-sm font-semibold text-gray-700 dark:text-gray-200"
                            style={{ width: MEMBER_COLUMN_WIDTH }}
                        >
                            メンバー
                        </div>
                        <div className="flex" style={{ width: timelineWidth }}>
                            {days.map((day) => (
                                <div
                                    key={day.toISOString()}
                                    className={`shrink-0 border-r border-gray-100 dark:border-gray-800 px-1 py-2 text-center ${
                                        isSameDay(day, today)
                                            ? "bg-indigo-50 dark:bg-indigo-950/40"
                                            : ""
                                    }`}
                                    style={{ width: DAY_COLUMN_WIDTH }}
                                >
                                    <div className="text-[11px] text-gray-400 dark:text-gray-500">
                                        {formatWeekday(day)}
                                    </div>
                                    <div className="text-xs font-medium text-gray-700 dark:text-gray-200">
                                        {day.getDate()}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {members.map(([name, member]) => {
                        const tasks = layoutTasks(
                            member.tasks ?? [],
                            range.start,
                            range.end,
                            today,
                        );
                        const lanes = Math.max(
                            tasks.reduce(
                                (max, task) => Math.max(max, task.lane + 1),
                                0,
                            ),
                            1,
                        );
                        const rowHeight = lanes * (BAR_HEIGHT + BAR_GAP) + 16;

                        return (
                            <div
                                key={name}
                                className="flex border-b border-gray-100 dark:border-gray-800 last:border-b-0"
                            >
                                <div
                                    className="sticky left-0 z-10 shrink-0 border-r border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-4"
                                    style={{
                                        width: MEMBER_COLUMN_WIDTH,
                                        minHeight: rowHeight,
                                    }}
                                >
                                    <div className="font-medium text-gray-800 dark:text-gray-100">
                                        {name}
                                    </div>
                                    <div className="mt-1 text-xs text-gray-400">
                                        {member.tasks?.length ?? 0}件
                                    </div>
                                </div>
                                <div
                                    className="relative shrink-0 bg-white dark:bg-gray-900"
                                    style={{
                                        width: timelineWidth,
                                        minHeight: rowHeight,
                                    }}
                                >
                                    <DayGrid days={days} today={today} />
                                    {tasks.map((task) => {
                                        const created = parseDate(task.created);
                                        const elapsedDays = daysBetween(
                                            created,
                                            today,
                                        );
                                        const overdueDays = task.dueDate
                                            ? Math.max(
                                                  daysBetween(
                                                      parseDate(task.dueDate),
                                                      today,
                                                  ),
                                                  0,
                                              )
                                            : 0;
                                        const dueOutsideRange =
                                            !!task.dueDate &&
                                            (task.rawEnd < range.start ||
                                                task.rawEnd > range.end);
                                        const startSourceLabel =
                                            task.hasStartDate
                                                ? `開始: ${task.startDate}`
                                                : `開始: 未設定 (起案 ${task.created})`;
                                        const endSourceLabel = task.hasDueDate
                                            ? `終了: ${task.dueDate}`
                                            : `終了: 未設定`;
                                        const tooltip = [
                                            `${task.key} · ${task.summary}`,
                                            `状態: ${task.status}`,
                                            startSourceLabel,
                                            endSourceLabel,
                                            `経過日数: ${elapsedDays}日`,
                                            overdueDays > 0
                                                ? `期限超過: ${overdueDays}日`
                                                : null,
                                            dueOutsideRange && task.dueDate
                                                ? `(表示月外: ${formatMonthDay(parseDate(task.dueDate))})`
                                                : null,
                                            !task.hasStartDate &&
                                            !task.hasDueDate
                                                ? "※ 開始日・終了日が未設定のためバー位置は概算です"
                                                : null,
                                        ]
                                            .filter(Boolean)
                                            .join("\n");
                                        const showOverdueDateInLabel =
                                            overdueDays > 0 &&
                                            dueOutsideRange &&
                                            task.dueDate;
                                        const labelText = showOverdueDateInLabel
                                            ? `${task.key} · ${task.summary}（終了日 ${formatMonthDay(parseDate(task.dueDate!))}）`
                                            : `${task.key} · ${task.summary}`;
                                        return (
                                            <a
                                                key={`${name}-${task.key}-${task.created}`}
                                                href={task.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                title={tooltip}
                                                className={`absolute flex items-center rounded-lg border px-2 text-[11px] font-medium text-gray-700 dark:text-gray-100 shadow-sm transition-transform hover:-translate-y-0.5 hover:shadow ${getTaskClassName(
                                                    task,
                                                    today,
                                                )}`}
                                                style={{
                                                    left: task.left,
                                                    top:
                                                        8 +
                                                        task.lane *
                                                            (BAR_HEIGHT +
                                                                BAR_GAP),
                                                    width: task.width,
                                                    height: BAR_HEIGHT,
                                                }}
                                            >
                                                <span className="truncate">
                                                    {labelText}
                                                </span>
                                            </a>
                                        );
                                    })}
                                    {tasks.length === 0 && (
                                        <div className="flex h-full items-center px-4 text-xs text-gray-400">
                                            表示範囲内のタスクはありません
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}

                    {members.length === 0 && (
                        <div className="px-6 py-12 text-center text-sm text-gray-400">
                            カレンダーデータがありません。
                        </div>
                    )}
                </div>
            </div>
        </section>
    );
}

function NavButton({
    children,
    label,
    onClick,
}: {
    children: React.ReactNode;
    label: string;
    onClick: () => void;
}) {
    return (
        <button
            type="button"
            aria-label={label}
            onClick={onClick}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 bg-white text-sm text-gray-600 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-800"
        >
            {children}
        </button>
    );
}

function Legend({ label, className }: { label: string; className: string }) {
    return (
        <span className="inline-flex items-center gap-1.5">
            <span
                className={`inline-block h-3 w-3 rounded-sm border ${className}`}
            />
            {label}
        </span>
    );
}

function DayGrid({ days, today }: { days: Date[]; today: Date }) {
    return (
        <>
            {days.map((day) => {
                const weekend = day.getDay() === 0 || day.getDay() === 6;
                const isToday = isSameDay(day, today);
                let bg = "";
                if (isToday) {
                    bg = "bg-indigo-50/50 dark:bg-indigo-950/20";
                } else if (weekend) {
                    bg = "bg-gray-50 dark:bg-gray-800/40";
                }
                return (
                    <div
                        key={day.toISOString()}
                        className={`absolute top-0 bottom-0 border-r border-gray-100 dark:border-gray-800 ${bg}`}
                        style={{
                            left: daysBetween(days[0], day) * DAY_COLUMN_WIDTH,
                            width: DAY_COLUMN_WIDTH,
                        }}
                    />
                );
            })}
        </>
    );
}

function layoutTasks(
    tasks: CalendarData["members"][string]["tasks"],
    rangeStart: Date,
    rangeEnd: Date,
    today: Date,
): VisibleTask[] {
    const visible = tasks
        .map((task) => {
            const hasStartDate = !!task.startDate;
            const hasDueDate = !!task.dueDate;
            // 開始日: Jira Start Date 優先、無ければ created にフォールバック
            const rawStart = parseDate(task.startDate ?? task.created);
            // 終了日: WBSGantt 終了日優先、無ければ「今日」（進行中継続を示唆）にフォールバック
            const rawEnd = task.dueDate ? parseDate(task.dueDate) : today;

            // 全くレンジ外（未来開始、または過去終了でクランプ不要）
            // 開始がレンジより未来 → 表示しない
            if (rawStart > rangeEnd) {
                return null;
            }

            const isBeforeRange = rawEnd < rangeStart;
            const isAfterRange = rawStart > rangeEnd;

            // 表示位置: クランプ
            const start = maxDate(rawStart, rangeStart);
            const end = minDate(maxDate(rawEnd, rawStart), rangeEnd);
            const clampedStart = start > end ? rangeStart : start;
            const clampedEnd = start > end ? rangeStart : end;

            return {
                ...task,
                start: clampedStart,
                end: clampedEnd,
                rawStart,
                rawEnd,
                hasStartDate,
                hasDueDate,
                isBeforeRange,
                isAfterRange,
                lane: 0,
                left:
                    daysBetween(rangeStart, clampedStart) * DAY_COLUMN_WIDTH +
                    2,
                width: Math.max(
                    (daysBetween(clampedStart, clampedEnd) + 1) *
                        DAY_COLUMN_WIDTH -
                        4,
                    28,
                ),
            };
        })
        .filter((task): task is VisibleTask => task !== null)
        .sort(
            (a, b) =>
                a.start.getTime() - b.start.getTime() ||
                a.end.getTime() - b.end.getTime(),
        );

    const laneEnds: Date[] = [];
    for (const task of visible) {
        let laneIndex = laneEnds.findIndex((laneEnd) => laneEnd < task.start);
        if (laneIndex === -1) {
            laneIndex = laneEnds.length;
            laneEnds.push(task.end);
        } else {
            laneEnds[laneIndex] = task.end;
        }
        task.lane = laneIndex;
    }

    return visible;
}

function getTaskClassName(task: VisibleTask, today: Date) {
    // 開始・終了日ともに未設定 → 視認性のため薄い amber + 点線枠で表現
    if (!task.hasStartDate && !task.hasDueDate) {
        return "bg-amber-50 dark:bg-amber-950/40 border-amber-400 dark:border-amber-600 border-dashed text-amber-800 dark:text-amber-200";
    }
    if (task.dueDate) {
        const due = parseDate(task.dueDate);
        if (due < today) {
            const overdueDays = daysBetween(due, today);
            if (overdueDays >= 14) {
                return "bg-red-400 dark:bg-red-700 border-red-600 dark:border-red-500 text-white";
            }
            if (overdueDays >= 7) {
                return "bg-red-300 dark:bg-red-800 border-red-500 dark:border-red-600";
            }
            return "bg-red-200 dark:bg-red-800 border-red-400 dark:border-red-600";
        }
    }
    if (task.status.toLowerCase().includes("progress")) {
        return "bg-green-200 dark:bg-green-800 border-green-400 dark:border-green-600";
    }
    return "bg-gray-200 dark:bg-gray-700 border-gray-300 dark:border-gray-600";
}

function shiftAnchor(anchor: Date, direction: -1 | 1) {
    return new Date(anchor.getFullYear(), anchor.getMonth() + direction, 1);
}

function getMonthRange(date: Date) {
    const start = new Date(date.getFullYear(), date.getMonth(), 1);
    const end = new Date(date.getFullYear(), date.getMonth() + 1, 0);

    return {
        start,
        end,
        label: `${date.getFullYear()}年${date.getMonth() + 1}月`,
    };
}

function listDays(start: Date, end: Date) {
    const days: Date[] = [];
    const current = new Date(start);
    while (current <= end) {
        days.push(new Date(current));
        current.setDate(current.getDate() + 1);
    }
    return days;
}

function parseDate(value: string) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
}

function startOfDay(date: Date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function daysBetween(start: Date, end: Date) {
    return Math.round(
        (startOfDay(end).getTime() - startOfDay(start).getTime()) / 86_400_000,
    );
}

function minDate(a: Date, b: Date) {
    return a <= b ? a : b;
}

function maxDate(a: Date, b: Date) {
    return a >= b ? a : b;
}

function formatWeekday(date: Date) {
    return date.toLocaleDateString("ja-JP", { weekday: "short" });
}

function formatMonthDay(date: Date) {
    return `${date.getMonth() + 1}/${date.getDate()}`;
}

function isSameDay(a: Date, b: Date) {
    return (
        a.getFullYear() === b.getFullYear() &&
        a.getMonth() === b.getMonth() &&
        a.getDate() === b.getDate()
    );
}
