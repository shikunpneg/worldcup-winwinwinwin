import type {
  DayTree,
  TeamsResponse,
  ScheduleResponse,
  TeamEdit,
  ViewMode,
} from "./types";

const BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

export function fetchToday(date: string): Promise<DayTree> {
  return fetchJson<DayTree>(`${BASE}/today?date=${encodeURIComponent(date)}`);
}

export function fetchPanorama(): Promise<DayTree> {
  return fetchJson<DayTree>(`${BASE}/panorama`);
}

export function fetchTeams(): Promise<TeamsResponse> {
  return fetchJson<TeamsResponse>(`${BASE}/teams`);
}

export function fetchSchedule(): Promise<ScheduleResponse> {
  return fetchJson<ScheduleResponse>(`${BASE}/schedule`);
}

export function postRefreshData(): Promise<{ status: string; message: string }> {
  return fetchJson<{ status: string; message: string }>(`${BASE}/refresh-data`, {
    method: "POST",
  });
}

export function postSimulate(
  mode: ViewMode,
  date: string | undefined,
  edits: TeamEdit[]
): Promise<DayTree> {
  const body = { mode, date, edits };
  return fetchJson<DayTree>(`${BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
