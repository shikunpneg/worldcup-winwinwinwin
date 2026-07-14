import DanmakuOverlay from "./DanmakuOverlay";

export default function PosterPage({ onEnter }: { onEnter: () => void }) {
  return (
    <div className="relative min-h-screen w-full overflow-hidden">

      {/* Danmaku (barrage comments) overlay */}
      <DanmakuOverlay />
      {/* Full-screen background image */}
      <img
        src="/poster.png"
        alt="2026 FIFA World Cup Bracket"
        className="absolute inset-0 h-full w-full object-cover"
        style={{ filter: "brightness(0.85) contrast(1.1)" }}
      />

      {/* Dark overlay at bottom for text readability */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#030811] via-transparent to-transparent" />

      {/* Title and CTA */}
      <div className="absolute bottom-0 left-0 right-0 z-10 pb-16 pt-32 text-center">
        <h1 className="mb-2 text-5xl font-bold tracking-tight text-white drop-shadow-lg">
          世界杯预测
        </h1>
        <p className="mb-8 text-lg text-[#c0d0e8] drop-shadow">
          2026 FIFA World Cup · Knockout Stage Prediction
        </p>
        <button
          onClick={onEnter}
          className="rounded-xl bg-gradient-to-r from-[#d4af37] to-[#f0c040] px-10 py-3 text-lg font-bold text-[#030811] shadow-lg shadow-[#d4af37]/30 transition-all hover:scale-105 hover:shadow-xl hover:shadow-[#d4af37]/40"
        >
          进入预测
        </button>
      </div>
    </div>
  );
}
