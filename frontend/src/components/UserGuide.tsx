import { useState } from "react";

const GUIDE_STEPS = [
  {
    title: "🔄 切换赛场视图",
    desc: "顶部栏切换「日视图」查看当天比赛，或「全景图」查看完整淘汰赛树。",
  },
  {
    title: "✏️ 编辑球队（What-If 推演）",
    desc: "鼠标悬停比赛框 → 点击右上角 ✏️ 按钮 → 选择新球队 → 立即看到变化。",
  },
  {
    title: "▶ 运行预测",
    desc: "编辑球队后，点击顶部栏「▶ 运行预测」按钮，模型重新预测所有比赛。",
  },
  {
    title: "📊 查看球队详情",
    desc: "点击左侧比赛框，右侧面板显示球队特征评分、胜率、模型准确率。",
  },
  {
    title: "🔄 重置编辑",
    desc: "点击「重置」按钮回到原始数据，清除所有编辑和模拟结果。",
  },
  {
    title: "📸 导出图片",
    desc: "点击「导出 PNG」可将当前赛程树保存为图片。",
  },
];

export default function UserGuide() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Help button - fixed bottom-right */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-4 right-4 z-[9999] flex h-10 w-10 items-center justify-center rounded-full bg-[#f0c040] text-lg font-bold text-black shadow-lg transition-all hover:scale-110 hover:shadow-xl"
        title="操作指南"
      >
        ?
      </button>

      {/* Guide panel */}
      {open && (
        <div className="fixed bottom-16 right-4 z-[9999] w-80 rounded-lg border border-[#3a5a8a] bg-[#0f1a2e]/95 p-4 shadow-2xl backdrop-blur">
          <div className="mb-3 flex items-center justify-between border-b border-[#2a4a7a] pb-2">
            <span className="text-sm font-bold text-white">📖 操作指南</span>
            <button
              onClick={() => setOpen(false)}
              className="text-sm text-[#8899bb] hover:text-white"
            >
              ✕
            </button>
          </div>
          <div className="space-y-3">
            {GUIDE_STEPS.map((step, i) => (
              <div key={i} className="border-b border-[#1a2d4a] pb-2 last:border-0">
                <div className="text-sm font-bold text-[#f0c040]">{step.title}</div>
                <div className="mt-0.5 text-xs text-[#8899bb]">{step.desc}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
