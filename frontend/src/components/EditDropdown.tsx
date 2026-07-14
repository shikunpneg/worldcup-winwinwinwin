import { useState, useEffect, useRef } from "react";
import type { TeamEdit } from "../types";

interface Props {
  matchId: number;
  currentHome: string;
  currentAway: string;
  homeFlag?: string;
  awayFlag?: string;
  allTeams: { name: string; flag: string }[];
  onSelect: (edit: TeamEdit, injuryHome?: number, injuryAway?: number) => void;
  onClose: () => void;
}

export default function EditDropdown({ matchId, currentHome, currentAway, homeFlag, awayFlag, allTeams, onSelect, onClose }: Props) {
  const [homeSearch, setHomeSearch] = useState("");
  const [awaySearch, setAwaySearch] = useState("");
  const [newHome, setNewHome] = useState(currentHome);
  const [newAway, setNewAway] = useState(currentAway);
  const [injuryHome, setInjuryHome] = useState(0);
  const [injuryAway, setInjuryAway] = useState(0);
  const [tab, setTab] = useState<"home"|"away"|"injury">("home");
  const homeRef = useRef<HTMLInputElement>(null);

  useEffect(() => { homeRef.current?.focus(); }, []);

  const homeFiltered = homeSearch.trim()
    ? allTeams.filter(t => t.name.toLowerCase().includes(homeSearch.toLowerCase()))
    : allTeams;
  const awayFiltered = awaySearch.trim()
    ? allTeams.filter(t => t.name.toLowerCase().includes(awaySearch.toLowerCase()))
    : allTeams;

  const homeTeam = allTeams.find(t => t.name === newHome);
  const awayTeam = allTeams.find(t => t.name === newAway);

  function handleConfirm() {
    const edit: TeamEdit = { match_id: matchId, home: newHome, away: newAway };
    onSelect(edit, injuryHome > 0 ? injuryHome : undefined, injuryAway > 0 ? injuryAway : undefined);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-[10000] flex items-start justify-center pt-16">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      <div className="relative z-10 w-[400px] rounded-xl border border-[#3a5a8a] bg-[#0f1a2e] shadow-2xl">

        {/* Header */}
        <div className="border-b border-[#2a4a7a] p-3 text-center text-sm font-bold text-white">
          ✏️ 编辑比赛 · What-If 推演
        </div>

        {/* Current match display */}
        <div className="flex items-center justify-center gap-3 border-b border-[#1a2d4a] px-4 py-3">
          <span className="text-lg">{homeFlag || "🏳"}</span>
          <span className="text-sm font-bold text-white">{currentHome}</span>
          <span className="text-xs text-[#556688]">VS</span>
          <span className="text-sm font-bold text-white">{currentAway}</span>
          <span className="text-lg">{awayFlag || "🏳"}</span>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[#2a4a7a]">
          <button onClick={() => setTab("home")}
            className={`flex-1 py-2 text-xs font-bold transition ${tab === "home" ? "border-b-2 border-[#f0c040] text-[#f0c040]" : "text-[#556688]"}`}
          >替换主队</button>
          <button onClick={() => setTab("away")}
            className={`flex-1 py-2 text-xs font-bold transition ${tab === "away" ? "border-b-2 border-[#f0c040] text-[#f0c040]" : "text-[#556688]"}`}
          >替换客队</button>
          <button onClick={() => setTab("injury")}
            className={`flex-1 py-2 text-xs font-bold transition ${tab === "injury" ? "border-b-2 border-[#f0c040] text-[#f0c040]" : "text-[#556688]"}`}
          >伤停模拟</button>
        </div>

        {/* Tab content */}
        <div className="p-3" style={{ minHeight: 200 }}>

          {/* Home replacement */}
          {tab === "home" && (
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="text-xs text-[#8899bb]">当前主队:</span>
                <span className="text-xs font-bold text-[#f0c040]">{homeTeam?.flag} {newHome}</span>
              </div>
              <input ref={homeRef} type="text" value={homeSearch}
                onChange={e => setHomeSearch(e.target.value)}
                placeholder="搜索主队..."
                className="mb-2 w-full rounded bg-[#1a2d4a] px-3 py-2 text-sm text-white outline-none placeholder:text-[#556688]"
              />
              <div className="max-h-[180px] overflow-y-auto">
                {homeFiltered.map(t => (
                  <button key={t.name} onClick={() => { setNewHome(t.name); setHomeSearch(""); }}
                    className={`flex w-full items-center gap-2 px-2 py-1.5 text-left text-sm transition rounded ${t.name === newHome ? "bg-[#2a4a7a] text-[#f0c040]" : "text-white hover:bg-[#1a2d4a]"}`}
                  >
                    <span>{t.flag}</span>
                    <span>{t.name}</span>
                    {t.name === newHome && <span className="ml-auto text-[10px] text-[#f0c040]">✓</span>}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Away replacement */}
          {tab === "away" && (
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="text-xs text-[#8899bb]">当前客队:</span>
                <span className="text-xs font-bold text-[#f0c040]">{awayTeam?.flag} {newAway}</span>
              </div>
              <input type="text" value={awaySearch}
                onChange={e => setAwaySearch(e.target.value)}
                placeholder="搜索客队..."
                className="mb-2 w-full rounded bg-[#1a2d4a] px-3 py-2 text-sm text-white outline-none placeholder:text-[#556688]"
              />
              <div className="max-h-[180px] overflow-y-auto">
                {awayFiltered.map(t => (
                  <button key={t.name} onClick={() => { setNewAway(t.name); setAwaySearch(""); }}
                    className={`flex w-full items-center gap-2 px-2 py-1.5 text-left text-sm transition rounded ${t.name === newAway ? "bg-[#2a4a7a] text-[#f0c040]" : "text-white hover:bg-[#1a2d4a]"}`}
                  >
                    <span>{t.flag}</span>
                    <span>{t.name}</span>
                    {t.name === newAway && <span className="ml-auto text-[10px] text-[#f0c040]">✓</span>}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Injury simulation */}
          {tab === "injury" && (
            <div className="space-y-4">
              <p className="text-xs text-[#8899bb]">模拟核心球员伤停，降低球队战斗力</p>

              <div>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs text-white">{homeTeam?.flag} {newHome} 伤停程度</span>
                  <span className="text-xs font-bold text-[#ff6b6b]">{injuryHome > 0 ? `-${injuryHome}%` : "无"}</span>
                </div>
                <input type="range" min="0" max="50" value={injuryHome}
                  onChange={e => setInjuryHome(Number(e.target.value))}
                  className="w-full accent-[#ff6b6b]"
                />
                <div className="flex justify-between text-[10px] text-[#556688]">
                  <span>健康</span>
                  <span>轻伤</span>
                  <span>重伤</span>
                  <span>缺阵</span>
                </div>
              </div>

              <div>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs text-white">{awayTeam?.flag} {newAway} 伤停程度</span>
                  <span className="text-xs font-bold text-[#ff6b6b]">{injuryAway > 0 ? `-${injuryAway}%` : "无"}</span>
                </div>
                <input type="range" min="0" max="50" value={injuryAway}
                  onChange={e => setInjuryAway(Number(e.target.value))}
                  className="w-full accent-[#ff6b6b]"
                />
                <div className="flex justify-between text-[10px] text-[#556688]">
                  <span>健康</span>
                  <span>轻伤</span>
                  <span>重伤</span>
                  <span>缺阵</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-[#2a4a7a] p-3">
          {newHome !== currentHome || newAway !== currentAway || injuryHome > 0 || injuryAway > 0 ? (
            <div className="flex-1 text-[10px] text-[#8899bb]">
              {newHome !== currentHome && <>主队: {currentHome} → {newHome} </>}
              {newAway !== currentAway && <>客队: {currentAway} → {newAway} </>}
              {injuryHome > 0 && <>主队战力-{injuryHome}% </>}
              {injuryAway > 0 && <>客队战力-{injuryAway}% </>}
            </div>
          ) : <div className="flex-1" />}
          <button onClick={onClose}
            className="rounded-lg bg-[#1a2d4a] px-4 py-1.5 text-xs text-[#8899bb] hover:text-white"
          >取消</button>
          <button onClick={handleConfirm}
            className="rounded-lg bg-gradient-to-r from-[#d4af37] to-[#f0c040] px-4 py-1.5 text-xs font-bold text-[#030811]"
          >确认</button>
        </div>
      </div>
    </div>
  );
}
