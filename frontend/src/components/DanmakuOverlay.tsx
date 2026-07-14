import { useEffect, useState, useRef } from "react";

interface DanmakuItem {
  text: string;
  source: string;
  likes: number;
  emojis: string[];
}

interface ActiveDanmaku {
  id: number;
  item: DanmakuItem;
  top: number;
  speed: number;
  color: string;
}

const COLORS = ["#ff6b6b", "#ffd93d", "#6bcb77", "#4d96ff", "#ff8fab", "#c9b1ff", "#a0e9ff"];

export default function DanmakuOverlay() {
  const [danmakuList, setDanmakuList] = useState<DanmakuItem[]>([]);
  const [active, setActive] = useState<ActiveDanmaku[]>([]);
  const [paused, setPaused] = useState(false);
  const idRef = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetch("/danmaku.json")
      .then((r) => r.json())
      .then((data: DanmakuItem[]) => setDanmakuList(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (danmakuList.length === 0) return;
    if (timerRef.current) clearInterval(timerRef.current);

    timerRef.current = setInterval(() => {
      if (paused) return;
      // Batch: collect multiple new items and add them in ONE setState
      const batch: ActiveDanmaku[] = [];
      const count = Math.floor(2 + Math.random() * 3);
      for (let i = 0; i < count; i++) {
        const item = danmakuList[Math.floor(Math.random() * danmakuList.length)];
        const newId = idRef.current++;
        const top = 5 + Math.random() * 65;
        const speed = 10 + Math.random() * 8;
        const color = COLORS[Math.floor(Math.random() * COLORS.length)];
        batch.push({ id: newId, item, top, speed, color });

        // Schedule removal per item
        setTimeout(() => {
          setActive((prev) => {
            const next = prev.filter((d) => d.id !== newId);
            return next.length < prev.length ? next : prev;
          });
        }, (speed + 3) * 1000);
      }
      setActive((prev) => {
        if (prev.length >= 15) return prev;
        return [...prev, ...batch].slice(0, 20);
      });
    }, 1200);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [danmakuList, paused]);

  return (
    <div
      ref={containerRef}
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        pointerEvents: "none",
        zIndex: 20,
      }}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {active.map((d) => (
        <div
          key={d.id}
          style={{
            position: "absolute",
            whiteSpace: "nowrap",
            top: `${d.top}%`,
            left: "100%",
            transform: "translate3d(0, -50%, 0)",
            fontSize: "15px",
            fontWeight: 700,
            color: d.color,
            textShadow: "0 0 10px rgba(0,0,0,0.95), 0 0 4px rgba(0,0,0,0.8), 2px 2px 4px rgba(0,0,0,0.6)",
            opacity: 0.92,
            willChange: "transform",
            animation: `danmaku-scroll ${d.speed}s linear forwards`,
            animationPlayState: paused ? "paused" : "running",
            pointerEvents: "auto",
            cursor: "pointer",
            userSelect: "none",
            fontFamily: "'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', sans-serif",
            letterSpacing: "1px",
            transition: "opacity 0.2s",
            lineHeight: 1.6,
          }}
          className="danmaku-item"
          title={`来源: ${d.item.source} · 点赞: ${d.item.likes}`}
        >
          {d.item.emojis && d.item.emojis.length > 0 && (
            <span style={{ marginRight: 6, fontSize: 17 }}>{d.item.emojis[0]}</span>
          )}
          {d.item.text}
          <span style={{ marginLeft: 10, fontSize: 11, opacity: 0.5, fontWeight: 400, verticalAlign: "middle" }}>
            · {d.item.source}
          </span>
        </div>
      ))}

      <style>{`
        @keyframes danmaku-scroll {
          from { transform: translate3d(0, -50%, 0); }
          to { transform: translate3d(-300vw, -50%, 0); }
        }
        .danmaku-item {
          will-change: transform;
          backface-visibility: hidden;
        }
        .danmaku-item:hover {
          opacity: 1 !important;
          text-shadow: 0 0 16px rgba(255,255,255,0.3), 0 0 8px rgba(0,0,0,0.95) !important;
        }
      `}</style>
    </div>
  );
}
