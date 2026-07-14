interface Props {
  matchInfo: {
    home: { name: string; flag: string; features: Record<string, number> };
    away: { name: string; flag: string; features: Record<string, number> };
    homeWinProb: number;
    awayWinProb: number;
    drawProb: number;
    score: string;
  };
  pos: { x: number; y: number };
  onClose: () => void;
  accuracy?: number;
  accuracyCorrect?: number;
  accuracyTotal?: number;
}

/* Feature display config */
const FEATURE_CONFIG: {
  key: string;
  label: string;
  icon: string;
  max: number;
  unit: string;
  decimals: number;
}[] = [
  { key: "elo", label: "Elo 评分", icon: "\uD83C\uDFC6", max: 2000, unit: "", decimals: 0 },
  { key: "points", label: "赛事积分", icon: "\uD83D\uDCCA", max: 20, unit: "", decimals: 0 },
  { key: "star_goals", label: "射手榜进球", icon: "\u2B50", max: 20, unit: "", decimals: 1 },
  { key: "market_value", label: "身价(亿)", icon: "\uD83D\uDCB0", max: 20, unit: "亿", decimals: 2 },
  { key: "possession", label: "控球率", icon: "\u23F1\uFE0F", max: 70, unit: "%", decimals: 0 },
  { key: "sot_per_game", label: "射正/场", icon: "\uD83E\uDD45", max: 10, unit: "", decimals: 1 },
  { key: "chances_created_pg", label: "创造力/场", icon: "\uD83C\uDFAF", max: 15, unit: "", decimals: 1 },
  { key: "goals_against_per_game", label: "防守(失球/场)", icon: "\uD83D\uDEE1\uFE0F", max: 3, unit: "", decimals: 2 },
  { key: "stamina", label: "体力值", icon: "\u26A1", max: 1, unit: "", decimals: 2 },
  { key: "pressing_intensity", label: "逼抢强度", icon: "\uD83D\uDCAA", max: 30, unit: "", decimals: 1 },
  { key: "build_up_score", label: "传控风格", icon: "\uD83D\uDCD0", max: 80, unit: "", decimals: 1 },
];

function TeamFeatureBars({ team, label }: { team: { name: string; flag: string; features: Record<string, number> }; label: string }) {
  return (
    <div>
      <div className="mb-1 flex items-center gap-1.5 border-b border-[#2a4a7a] pb-1">
        <span className="text-base">{team.flag}</span>
        <span className="text-sm font-bold text-white">{team.name}</span>
        <span className="ml-auto text-xs text-[#8899bb]">{label}</span>
      </div>
      <div className="space-y-1">
        {FEATURE_CONFIG.map((cfg) => {
          const val = team.features[cfg.key] ?? 0;
          const pct = Math.min(val / cfg.max, 1);
          return (
            <div key={cfg.key} className="flex items-center gap-2 text-xs">
              <span className="w-4 text-center" style={{ fontSize: "11px" }}>
                {cfg.icon}
              </span>
              <span className="w-[72px] shrink-0 text-[#8899bb]">{cfg.label}</span>
              <div className="flex-1">
                <div className="h-1.5 overflow-hidden rounded-full bg-[#1a2d4a]">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${pct * 100}%`,
                      background: "linear-gradient(90deg, #4a6fa5, #f0c040)",
                    }}
                  />
                </div>
              </div>
              <span className="w-14 text-right font-mono text-white">
                {val.toFixed(cfg.decimals)}
                {cfg.unit}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function FeatureTooltip({ matchInfo, pos, onClose, accuracy, accuracyCorrect, accuracyTotal }: Props) {
  const { home, away, homeWinProb, awayWinProb, drawProb, score } = matchInfo;

  /* Prediction confidence = max probability */
  const confidence = Math.max(homeWinProb, drawProb, awayWinProb);

  return (
    <div className="rounded-lg border border-[#3a5a8a] bg-[#0f1a2e]/95 p-3 shadow-xl backdrop-blur" style={{ position: "sticky", top: 12 }}>
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute right-2 top-2 text-[#8899bb] hover:text-white text-sm leading-none"
        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
      >
        ✕
      </button>

      {/* Prediction confidence bar */}
      <div className="mb-2 flex items-center gap-2 rounded bg-[#1a2d4a] px-2 py-1">
        <span className="text-xs text-[#8899bb]">预测置信度</span>
        <div className="flex-1 h-2 rounded-full bg-[#0a1424] overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${(confidence * 100).toFixed(0)}%`,
              background: confidence > 0.7
                ? 'linear-gradient(90deg, #2a8a4a, #4aed8a)'
                : confidence > 0.4
                  ? 'linear-gradient(90deg, #b8860b, #f0c040)'
                  : 'linear-gradient(90deg, #8a2a2a, #ed4a4a)',
            }}
          />
        </div>
        <span className="text-xs font-bold font-mono text-white w-10 text-right">
          {(confidence * 100).toFixed(0)}%
        </span>
      </div>
      {/* Model accuracy bar */}
      {accuracy !== undefined && accuracyTotal !== undefined && accuracyTotal > 0 && (
        <div className="mb-2 flex items-center gap-2 rounded bg-[#1a2d4a] px-2 py-1">
          <span className="text-xs text-[#8899bb]">模型总准确率</span>
          <div className="flex-1 h-2 rounded-full bg-[#0a1424] overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${(accuracy * 100).toFixed(0)}%`,
                background: accuracy > 0.7
                  ? 'linear-gradient(90deg, #2a8a4a, #4aed8a)'
                  : accuracy > 0.5
                    ? 'linear-gradient(90deg, #b8860b, #f0c040)'
                    : 'linear-gradient(90deg, #8a2a2a, #ed4a4a)',
              }}
            />
          </div>
          <span className="text-xs font-bold font-mono text-white w-24 text-right">
            {(accuracy * 100).toFixed(1)}% ({accuracyCorrect}/{accuracyTotal})
          </span>
        </div>
      )}

      {/* Predicted score header */}
      <div className="mb-2 flex items-center justify-center gap-3 border-b border-[#2a4a7a] pb-2">
        <span className="text-lg">{home.flag}</span>
        <span className="max-w-[90px] truncate text-sm font-bold text-white">{home.name}</span>
        <span className="rounded-md bg-[#2a4a7a] px-3 py-0.5 font-mono text-lg font-bold text-[#f0c040]">
          {score}
        </span>
        <span className="max-w-[90px] truncate text-sm font-bold text-white">{away.name}</span>
        <span className="text-lg">{away.flag}</span>
      </div>

      {/* Win probabilities */}
      <div className="mb-3 flex gap-1 text-center text-xs">
        <div className="flex-1 rounded bg-green-900/40 px-1 py-1">
          <div className="text-green-400">主胜</div>
          <div className="font-bold text-white">
            {(homeWinProb * 100).toFixed(1)}%
          </div>
        </div>
        <div className="flex-1 rounded bg-yellow-900/40 px-1 py-1">
          <div className="text-yellow-400">平局</div>
          <div className="font-bold text-white">
            {(drawProb * 100).toFixed(1)}%
          </div>
        </div>
        <div className="flex-1 rounded bg-red-900/40 px-1 py-1">
          <div className="text-red-400">客胜</div>
          <div className="font-bold text-white">
            {(awayWinProb * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Home team features */}
      <TeamFeatureBars team={home} label="主队" />

      <div className="my-2 border-t border-[#2a4a7a]" />

      {/* Away team features */}
      <TeamFeatureBars team={away} label="客队" />
    </div>
  );
}

