import { useState, useEffect, useCallback } from "react";
import type {
  DayTree,
  TeamEdit,
  TeamInfo,
  ScheduleDay,
  ChangesInfo,
  ViewMode,
  MatchNode,
  Round,
} from "./types";
import {
  fetchToday,
  fetchPanorama,
  fetchTeams,
  fetchSchedule,
  postSimulate,
} from "./api";
import TopBar from "./components/TopBar";
import BracketTree from "./components/BracketTree";
import GroupStandings from "./components/GroupStandings";
import FeatureTooltip from "./components/FeatureTooltip";
import EditDropdown from "./components/EditDropdown";
import ChangesPanel from "./components/ChangesPanel";
import PosterPage from "./components/PosterPage";
import UserGuide from "./components/UserGuide";

export default function App() {
  const [mode, setMode] = useState<ViewMode>("poster");
  const [selectedDate, setSelectedDate] = useState("2026-07-10");
  const [treeData, setTreeData] = useState<DayTree | null>(null);
  const [allTeams, setAllTeams] = useState<TeamInfo[]>([]);
  const [availableDates, setAvailableDates] = useState<ScheduleDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Edit state */
  const [edits, setEdits] = useState<TeamEdit[]>([]);
  const [editing, setEditing] = useState<{
    matchId: number;
    side: "home" | "away";
    currentHome: string;
    currentAway: string;
  } | null>(null);

  /* Hover/Select state - show details in a fixed side panel */
  const [selectedMatch, setSelectedMatch] = useState<{
    home: { name: string; flag: string; features: Record<string, number> };
    away: { name: string; flag: string; features: Record<string, number> };
    homeWinProb: number;
    awayWinProb: number;
    drawProb: number;
    score: string;
  } | null>(null);

  const [changes, setChanges] = useState<ChangesInfo[]>([]);
  const [hasEdits, setHasEdits] = useState(false);

  /* Load initial data */
  useEffect(() => {
    async function init() {
      try {
        const [teamsRes, scheduleRes] = await Promise.all([
          fetchTeams(),
          fetchSchedule(),
        ]);
        setAllTeams(teamsRes.teams);
        setAvailableDates(scheduleRes.schedule);
        if (scheduleRes.schedule.length > 0) {
          setSelectedDate(scheduleRes.schedule[0].date);
        }
      } catch (e: any) {
        console.error("Init failed:", e);
      }
    }
    init();
  }, []);

  /* Fetch tree data when mode/date changes */
  const loadTree = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data =
        mode === "panorama"
          ? await fetchPanorama()
          : await fetchToday(selectedDate);
      setTreeData(data);
      setEdits([]);
      setChanges([]);
      setHasEdits(false);
      setSelectedMatch(null);
    } catch (e: any) {
      setError(e.message);
      console.error("Load tree failed:", e);
    } finally {
      setLoading(false);
    }
  }, [mode, selectedDate]);

  useEffect(() => {
    loadTree();
  }, [loadTree]);

  /* Edit handlers */
  function handleEditTeam(matchId: number, side: "home" | "away") {
    const match = (() => {
      if (!treeData) return null;
      for (const r of treeData.rounds) {
        for (const m of r.matches) {
          if (m.match_id === matchId) return m;
        }
      }
      return null;
    })();
    if (match) {
      setEditing({
        matchId,
        side,
        currentHome: match.home.name,
        currentAway: match.away.name,
      });
    }
  }

  function handleEditSelect(edit: TeamEdit, injuryHome?: number, injuryAway?: number) {
    setEdits((prev) => {
      const idx = prev.findIndex((e) => e.match_id === edit.match_id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = edit;
        return next;
      }
      return [...prev, edit];
    });
    setHasEdits(true);
    setEditing(null);
    // Store injury impact for backend
    if (injuryHome || injuryAway) {
      (edit as any).injury_home = injuryHome;
      (edit as any).injury_away = injuryAway;
    }

    // 立即更新 treeData，让用户看到球队名变化，无需等待后端
    if (treeData) {
      const newTree: DayTree = JSON.parse(JSON.stringify(treeData));
      for (const r of newTree.rounds) {
        for (const m of r.matches) {
          if (m.match_id === edit.match_id) {
            // 更新主队
            m.home.name = edit.home;
            const homeInfo = allTeams.find((t) => t.name === edit.home);
            if (homeInfo) {
              if (homeInfo.flag) m.home.flag = homeInfo.flag;
              if (homeInfo.name_cn) m.home.name_cn = homeInfo.name_cn;
            }
            // 更新客队
            m.away.name = edit.away;
            const awayInfo = allTeams.find((t) => t.name === edit.away);
            if (awayInfo) {
              if (awayInfo.flag) m.away.flag = awayInfo.flag;
              if (awayInfo.name_cn) m.away.name_cn = awayInfo.name_cn;
            }
            m.score = "?-?";
            m.winner = "TBD";
            m.is_future = true;
            break;
          }
        }
      }
      setTreeData(newTree);
    }
  }

  async function applyEdits() {
    if (edits.length === 0) return;
    setLoading(true);
    try {
      const data = await postSimulate(
        mode,
        mode === "day" ? selectedDate : undefined,
        edits
      );
      setTreeData(data);
      setChanges(data.changes ?? []);
      setHasEdits(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setEdits([]);
    setChanges([]);
    setHasEdits(false);
    setSelectedMatch(null);
    loadTree();
  }

  function handleRun() {
    applyEdits();
  }

  function handleExport() {
    import("html2canvas").then((mod) => {
      const el = document.getElementById("tree-container");
      if (!el) return;
      mod.default(el, {
        backgroundColor: "#0f1a2e",
        scale: 2,
      }).then((canvas: HTMLCanvasElement) => {
        const link = document.createElement("a");
        link.download = `worldcup-bracket-${mode}-${selectedDate}.png`;
        link.href = canvas.toDataURL();
        link.click();
      });
    });
  }

  /* Hover 改为设置 selectedMatch，显示在右侧固定面板 */
  function handleHoverTeam(
    matchInfo: {
      home: { name: string; flag: string; features: Record<string, number> };
      away: { name: string; flag: string; features: Record<string, number> };
      homeWinProb: number;
      awayWinProb: number;
      drawProb: number;
      score: string;
    } | null,
    _pos: { x: number; y: number } | null
  ) {
    if (matchInfo) {
      setSelectedMatch(matchInfo);
    }
  }

  function handleClosePanel() {
    setSelectedMatch(null);
  }

  if (mode === "poster") {
    return <PosterPage onEnter={() => setMode("day")} />;
  }

  return (
    <div className="flex min-h-screen flex-col bg-bg text-white">
      <TopBar
        mode={mode}
        selectedDate={selectedDate}
        availableDates={availableDates}
        onModeChange={setMode}
        onDateChange={setSelectedDate}
        onReset={handleReset}
        onExport={handleExport}
        onRun={handleRun}
        onRefresh={loadTree}
        hasEdits={hasEdits}
        loading={loading}
        onHome={() => setMode("poster")}
      />

      {/* Error banner */}
      {error && (
        <div className="mx-4 mt-2 rounded-lg bg-red-900/60 px-4 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Group standings */}
      {treeData && treeData.groups && treeData.groups.length > 0 && (
        <div className="px-4 pt-2">
          <GroupStandings groups={treeData.groups} rounds={treeData.rounds} />
        </div>
      )}

      {/* Main area: bracket + side panel */}
      <div className="flex flex-1 gap-0 p-2">
        {/* Bracket tree */}
        <div id="tree-container" className="flex-1 overflow-auto p-2">
          {treeData && !loading ? (
            <BracketTree
              data={treeData}
              onEditTeam={handleEditTeam}
              onHoverTeam={handleHoverTeam}
            />
          ) : loading ? (
            <div className="flex items-center justify-center pt-20">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#4a6fa5] border-t-transparent" />
            </div>
          ) : null}
        </div>

        {/* 右侧固定详情面板 - 替代浮动 tooltip */}
        {selectedMatch && (
          <div className="w-[340px] shrink-0 overflow-y-auto">
            <FeatureTooltip
              matchInfo={selectedMatch}
              pos={{ x: 0, y: 0 }}
              onClose={handleClosePanel}
              accuracy={treeData?.accuracy}
              accuracyCorrect={treeData?.accuracy_correct}
              accuracyTotal={treeData?.accuracy_total}
            />
          </div>
        )}
      </div>

      {/* 不再使用浮动 tooltip, 改用右侧面板 */}

      {/* Edit dropdown */}
      {editing && (
        <EditDropdown
          matchId={editing.matchId}
          currentHome={editing.currentHome}
          currentAway={editing.currentAway}
          homeFlag={allTeams.find(t => t.name === editing.currentHome)?.flag}
          awayFlag={allTeams.find(t => t.name === editing.currentAway)?.flag}
          allTeams={allTeams}
          onSelect={handleEditSelect}
          onClose={() => setEditing(null)}
        />
      )}

      {/* User guide floating button */}
      <UserGuide />

      {/* Changes panel */}
      {changes.length > 0 && (
        <ChangesPanel
          changes={changes}
          onClose={() => setChanges([])}
        />
      )}
    </div>
  );
}
