import type { ViewMode, ScheduleDay } from "../types";

interface Props {
  mode: ViewMode;
  selectedDate: string;
  availableDates: ScheduleDay[];
  onModeChange: (m: ViewMode) => void;
  onDateChange: (d: string) => void;
  onReset: () => void;
  onRun: () => void;
  onExport: () => void;
  onRefresh: () => void;
  hasEdits: boolean;
  loading: boolean;
  onHome: () => void;
}

export default function TopBar({
  mode,
  selectedDate,
  availableDates,
  onModeChange,
  onDateChange,
  onReset,
  onRun,
  onExport,
  onRefresh,
  hasEdits,
  loading,
  onHome,
}: Props) {
  return (
    <header className="flex flex-wrap items-center gap-4 border-b border-[#1a2d4a] bg-[#0a1424] px-4 py-3">
      {/* Home button */}
      <button
        onClick={onHome}
        className="rounded-lg border border-[#2a4a7a] px-2.5 py-1.5 text-sm text-[#8899bb] transition-colors hover:border-[#d4af37] hover:text-[#f0c040]"
        title="返回首页"
      >
        🏠 首页
      </button>

      {/* Logo / Title */}
      <div className="flex items-center gap-2">
        <span className="text-2xl">⚽</span>
        <h1 className="text-lg font-bold text-white">世界杯预测</h1>
      </div>

      <div className="flex-1" />

      {/* Mode toggle */}
      <div className="flex overflow-hidden rounded-lg border border-[#2a4a7a] text-sm">
        <button
          onClick={() => onModeChange("day")}
          className={`px-3 py-1.5 transition-colors ${
            mode === "day"
              ? "bg-[#4a6fa5] text-white"
              : "bg-transparent text-[#8899bb] hover:text-white"
          }`}
        >
          日视图
        </button>
        <button
          onClick={() => onModeChange("panorama")}
          className={`px-3 py-1.5 transition-colors ${
            mode === "panorama"
              ? "bg-[#4a6fa5] text-white"
              : "bg-transparent text-[#8899bb] hover:text-white"
          }`}
        >
          全景模式
        </button>
      </div>

      {/* Date picker (day mode only) */}
      {mode === "day" && (
        <select
          value={selectedDate}
          onChange={(e) => onDateChange(e.target.value)}
          className="rounded-lg border border-[#2a4a7a] bg-[#1a2d4a] px-3 py-1.5 text-sm text-white outline-none"
        >
          {availableDates.map((d) => {
            const label = d.all_completed ? ' [已完成]' : d.completed_count > 0 ? ` [${d.completed_count}/${d.match_count}]` : '';
            return (
              <option key={d.date} value={d.date}>
                {d.date.slice(5)} ({d.match_count}场){label}
              </option>
            );
          })}
        </select>
      )}

      {/* Run prediction */}
      {hasEdits && !loading && (
        <button
          onClick={onRun}
          className="rounded-lg border border-[#2a8a4a] bg-[#1a5a3a] px-3 py-1.5 text-sm text-[#4aed8a] transition-colors hover:bg-[#2a7a4a]"
        >
          ▶ 运行预测
        </button>
      )}

      {/* Reset */}
      {hasEdits && (
        <button
          onClick={onReset}
          className="rounded-lg border border-[#b8860b] px-3 py-1.5 text-sm text-[#f0c040] transition-colors hover:bg-[#b8860b]/20"
        >
          重置
        </button>
      )}

      {/* Refresh */}
      <button
        onClick={onRefresh}
        disabled={loading}
        className="rounded-lg border border-[#4a6fa5] px-3 py-1.5 text-sm text-[#4a6fa5] transition-colors hover:bg-[#4a6fa5]/20 disabled:opacity-40"
        title="刷新数据"
      >
        🔄 {loading ? '刷新中...' : '刷新'}
      </button>

      {/* Export */}
      <button
        onClick={onExport}
        className="rounded-lg bg-[#4a6fa5] px-3 py-1.5 text-sm text-white transition-colors hover:bg-[#5a7fb5]"
      >
        导出 PNG
      </button>

      {/* Loading indicator */}
      {loading && (
        <div className="flex items-center gap-1 text-sm text-[#f0c040]">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-[#f0c040] border-t-transparent" />
          加载中...
        </div>
      )}
    </header>
  );
}
