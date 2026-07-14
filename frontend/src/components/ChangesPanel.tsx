import type { ChangesInfo } from "../types";

interface Props {
  changes: ChangesInfo[];
  onClose: () => void;
}

export default function ChangesPanel({ changes, onClose }: Props) {
  if (!changes || changes.length === 0) return null;

  return (
    <div className="border-t border-[#2a4a7a] bg-[#0a1424]">
      <div className="flex items-center justify-between px-4 py-2">
        <h3 className="text-sm font-bold text-[#f0c040]">
          原始 🔜 编辑后对比面板 ({changes.length})
        </h3>
        <button
          onClick={onClose}
          className="rounded px-2 py-0.5 text-xs text-[#8899bb] transition-colors hover:text-white"
        >
          关闭
        </button>
      </div>

      <div className="flex gap-3 overflow-x-auto px-4 pb-3">
        {changes.map((c) => (
          <div
            key={c.match_id}
            className="min-w-[220px] shrink-0 rounded-lg border border-[#2a4a7a] bg-[#1a2d4a] p-3"
          >
            <div className="mb-1 text-xs text-[#8899bb]">
              {c.stage} #{c.match_id}
            </div>
            {Object.entries(c.differences).map(([field, diff]) => (
              <div key={field} className="mb-1 text-xs">
                <span className="text-[#556688]">{field}: </span>
                <span className="text-red-400 line-through">
                  {diff.original}
                </span>
                <span className="mx-1 text-[#556688] text-green-400">→</span>
                <span className="text-green-400 font-semibold">{diff.simulated}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
