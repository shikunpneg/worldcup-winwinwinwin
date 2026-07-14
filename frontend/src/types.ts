/* ------------------------------------------------------------------ */
/*  TypeScript interfaces matching the backend API response structure  */
/* ------------------------------------------------------------------ */

export interface TeamFeatures {
  points: number;
  elo: number;
  goals_against_per_game: number;
  market_value: number;
  stamina: number;
  chances_created_pg: number;
  possession: number;
  pressing_intensity: number;
  build_up_score: number;
  sot_per_game: number;
  star_goals: number;
}

export interface TeamNode {
  name: string;
  name_cn?: string;
  flag: string;
  features: TeamFeatures;
}

/* Group standings */
export interface GroupTeam {
  name: string;
  name_cn?: string;
  flag: string;
  rank: number;
  points: number;
  mp: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  qualified: boolean;
}

export interface GroupData {
  name: string;
  teams: GroupTeam[];
}

export interface Probabilities {
  home_win: number;
  draw: number;
  away_win: number;
}

export interface MatchNode {
  match_id: number;
  stage: string;
  datetime: string;
  home: TeamNode;
  away: TeamNode;
  score: string;
  winner: string;
  penalty_winner?: string;
  home_win_prob: number;
  away_win_prob: number;
  probabilities: Probabilities;
  is_today: boolean;
  is_future: boolean;
  feeds_from?: number[];
}

export interface Round {
  name: string;
  today: boolean;
  matches: MatchNode[];
}

export interface DayTree {
  date: string;
  has_today?: boolean;
  mode?: string;
  groups: GroupData[];
  rounds: Round[];
  changes?: ChangesInfo[];
  accuracy?: number;
  accuracy_correct?: number;
  accuracy_total?: number;
}

export interface ChangesInfo {
  match_id: number;
  stage: string;
  differences: Record<string, { original: string; simulated: string }>;
}

export interface TeamInfo {
  name: string;
  name_cn?: string;
  flag: string;
  points: number;
  market_value: number;
}

export interface TeamsResponse {
  teams: TeamInfo[];
  total: number;
}

export interface ScheduleDay {
  date: string;
  match_count: number;
  completed_count: number;
  all_completed: boolean;
  matches: ScheduleMatch[];
}

export interface ScheduleMatch {
  date: string;
  match_id: number;
  stage: string;
  home: string;
  away: string;
  home_cn?: string;
  away_cn?: string;
  status: string;
  score?: string;
}

export interface ScheduleResponse {
  schedule: ScheduleDay[];
  total: number;
}

export interface TeamEdit {
  match_id: number;
  home: string;
  away: string;
  injury_home?: number;
  injury_away?: number;
}

export interface SimulateRequest {
  mode: "day" | "panorama";
  date?: string;
  edits: TeamEdit[];
}

export type ViewMode = "poster" | "day" | "panorama";

/** Feature display metadata: label, unit, icon, max for bar rendering */
export interface FeatureMeta {
  key: keyof TeamFeatures;
  label: string;
  icon: string;
  unit: string;
  max: number;
  decimals: number;
}

export const FEATURES: FeatureMeta[] = [
  { key: "elo",                 label: "Elo 评分",               icon: "\uD83C\uDFC6", unit: "",      max: 2000, decimals: 0 },
  { key: "points",              label: "赛事积分",               icon: "\uD83D\uDCCA", unit: "",      max: 20,   decimals: 0 },
  { key: "star_goals",          label: "射手榜进球",             icon: "\u2B50",       unit: "",      max: 20,   decimals: 1 },
  { key: "market_value",        label: "身价(亿)",               icon: "\uD83D\uDCB0", unit: "",      max: 20,   decimals: 2 },
  { key: "possession",          label: "控球率",                 icon: "\u23F1\uFE0F", unit: "%",     max: 70,   decimals: 0 },
  { key: "sot_per_game",        label: "射正/场",                icon: "\uD83E\uDD45", unit: "",      max: 10,   decimals: 1 },
  { key: "chances_created_pg",  label: "创造力/场",              icon: "\uD83C\uDFAF", unit: "",      max: 15,   decimals: 1 },
  { key: "goals_against_per_game", label: "防守(失球/场)",       icon: "\uD83D\uDEE1\uFE0F", unit: "", max: 3,  decimals: 2 },
  { key: "stamina",             label: "体力值",                 icon: "\u26A1",       unit: "",      max: 1,    decimals: 2 },
  { key: "pressing_intensity",  label: "逼抢强度",               icon: "\uD83D\uDCAA", unit: "",      max: 30,   decimals: 1 },
  { key: "build_up_score",      label: "传控风格",               icon: "\uD83D\uDCD0", unit: "",      max: 80,   decimals: 1 },
];
