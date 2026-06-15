import { readFileSync } from "fs";
import { join } from "path";

const DATA_DIR = join(process.cwd(), "data");

function load<T>(filename: string): T {
  try {
    const raw = readFileSync(join(DATA_DIR, filename), "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    // ビルド時にデータがない場合はダミーを返す
    return {} as T;
  }
}

export interface TeamSummary {
  monthly_leadtime: { month: string; avg_days: number; median_days: number; count: number }[];
  weekly_leadtime: { week: string; avg_days: number; median_days: number; count: number }[];
  weekly_closed: { week: string; count: number }[];
  current_wip: number;
  wip_limit: number;
}

export interface MemberStats {
  members: Record<string, {
    weeks: { week: string; closed: number }[];
    in_progress: number;
  }>;
  wip_limit: number;
}

export interface MemberLeadtime {
  members: Record<string, { month: string; avg_days: number; median_days: number; count: number }[]>;
}

export interface StaleTicket {
  key: string;
  summary: string;
  assignee: string;
  days_stale: number;
  url: string;
}

export interface OverdueTicket {
  key: string;
  summary: string;
  assignee: string;
  duedate: string;
  days_overdue: number;
  url: string;
}

export interface WipStatus {
  wip_limit: number;
  total_wip: number;
  members: {
    name: string;
    count: number;
    over_limit: boolean;
    tickets: { key: string; summary: string; days: number }[];
  }[];
}

export interface Meta {
  updated_at: string;
  data_files: number;
}

export interface KpiData {
  half_label: string;
  prev_label: string;
  targets: {
    weekly_closed: number;
    lead_time_median: number;
  };
  current: {
    total_closed: number;
    weekly_closed: number;
    weeks_elapsed: number;
    lead_time_median: number;
    lead_time_avg: number;
    lead_time_sample_count: number;
  };
  previous: {
    total_closed: number;
    weekly_closed: number;
  };
  projection: {
    remaining_weeks: number;
    needed_weekly_to_hit_target: number;
    projected_total_at_current_pace: number;
  };
}

export const getTeamSummary = () => load<TeamSummary>("team_summary.json");
export const getMemberStats = () => load<MemberStats>("member_stats.json");
export const getMemberLeadtime = () => load<MemberLeadtime>("member_leadtime.json");
export const getStaleRanking = () => load<StaleTicket[]>("stale_ranking.json");
export const getOverdueRanking = () => load<OverdueTicket[]>("overdue_ranking.json");
export const getWipStatus = () => load<WipStatus>("wip_status.json");
export const getKpi = () => load<KpiData>("kpi.json");
export const getMeta = () => load<Meta>("meta.json");
