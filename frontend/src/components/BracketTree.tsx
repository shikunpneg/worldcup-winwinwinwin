import { useRef, useEffect, useCallback, useState } from "react";

import * as d3 from "d3";

import type { DayTree, Round, MatchNode } from "../types";



interface Props {

  data: DayTree;

  onEditTeam: (matchId: number, side: "home" | "away") => void;

  onHoverTeam: (

    matchInfo: {

      home: { name: string; flag: string; features: Record<string, number> };

      away: { name: string; flag: string; features: Record<string, number> };

      homeWinProb: number;

      awayWinProb: number;

      drawProb: number;

      score: string;

    } | null,

    pos: { x: number; y: number } | null

  ) => void;

}



const COLORS = {

  bg: "#0f1a2e",

  matchBox: "#1a2d4a",

  futureBox: "#2a1a3a",

  completedBox: "#0a2a1a",

  line: "#4a6fa5",

  accent: "#f0c040",

  text: "#e8e8e8",

  dimText: "#8899bb",

  completedBorder: "#2a8a4a",

};



const BOX_W = 280;

const BOX_H = 86;

const COL_GAP = 100;

const ROW_GAP = 50;

const PADDING = 60;



function isTBD(name: string) {

  return name === "TBD" || name.includes("Winner Match") || name.includes("Loser Match");

}



/** Which rounds can be edited in "day" vs "panorama" mode */

function isEditable(match: MatchNode): boolean {

  // Allow editing all non-TBD matches (including completed for what-if)
  if (isTBD(match.home.name) || isTBD(match.away.name)) return false;

  return true;

}



export default function BracketTree({ data, onEditTeam, onHoverTeam }: Props) {

  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [zoomMode, setZoomMode] = useState(false);



  const layout = useCallback(() => {

    if (!svgRef.current || !data.rounds.length) return;



    // Reorder rounds: move "Today" section to the end for chronological left-to-right
    const rounds = [...data.rounds].sort((a, b) => {
      if (a.today && !b.today) return 1;
      if (!a.today && b.today) return -1;
      return 0;
    });

    const numCols = rounds.length;

    const maxRows = Math.max(...rounds.map((r) => r.matches.length));



    const svgW = PADDING * 2 + numCols * (BOX_W + COL_GAP) - COL_GAP;

    const svgH = PADDING * 2 + maxRows * (BOX_H + ROW_GAP) - ROW_GAP;



    const svg = d3.select(svgRef.current);

    svg.selectAll("*").remove();



    svg

      .attr("width", svgW)

      .attr("height", svgH)

      .attr("viewBox", `0 0 ${svgW} ${svgH}`)

      .style("touch-action", "auto")

      // Only attach zoom behavior when zoomMode is ON
      if (zoomMode) {
        svg.style("touch-action", "none")
          .call(
            d3.zoom<SVGSVGElement, unknown>()
              .scaleExtent([0.2, 5])
              .on("zoom", (event) => {
                container.attr("transform", event.transform);
              })
          );
      } else {
        zoomRef.current = null;
      };



    const container = svg.append("g").attr("class", "zoom-container");

    const defs = container.append("defs");

    defs

      .append("filter")

      .attr("id", "glow")

      .append("feDropShadow")

      .attr("dx", 0)

      .attr("dy", 0)

      .attr("stdDeviation", 4)

      .attr("flood-color", COLORS.accent)

      .attr("flood-opacity", 0.6);



    /* ---- Legend (fixed at SVG level, not affected by zoom) ---- */
    const legendY = svgH - 30;
    const legendItems = [
      { label: "已完赛", color: COLORS.completedBox, border: COLORS.completedBorder, icon: "\u2705" },
      { label: "今日预测", color: COLORS.matchBox, border: COLORS.accent, icon: "\uD83D\uDD2E" },
      { label: "未来预测", color: COLORS.futureBox, border: "#4a2a6a", icon: "\uD83D\uDCC5" },
    ];
    let lx = PADDING;
    legendItems.forEach((item) => {
      const lg = svg.append("g").attr("transform", `translate(${lx},${legendY + 4})`);
      lg.append("rect")
        .attr("width", 14).attr("height", 14).attr("rx", 3).attr("ry", 3)
        .attr("fill", item.color).attr("stroke", item.border).attr("stroke-width", 1.5);
      lg.append("text")
        .attr("x", 20).attr("y", 12)
        .attr("fill", COLORS.dimText).attr("font-size", "12px")
        .text(`${item.icon} ${item.label}`);
      const tw = 90;
      lx += tw + 12;
    });

    

      /* ---- Node positions ---- */

    interface NodePos {

      match: MatchNode;

      x: number;

      y: number;

      roundIdx: number;

    }

    const nodes: NodePos[] = [];

    const nodeMap = new Map<number, NodePos>();


    rounds.forEach((round, ri) => {

      const count = round.matches.length;

      const totalH = count * BOX_H + (count - 1) * ROW_GAP;

      const startY = (svgH - totalH) / 2;

      const x = PADDING + ri * (BOX_W + COL_GAP);



      round.matches.forEach((match, mi) => {

        const node = {

          match,

          x,

          y: startY + mi * (BOX_H + ROW_GAP),

          roundIdx: ri,

        };

        nodes.push(node);

        nodeMap.set(match.match_id, node);

      });

    });



    /* ---- Connecting lines (using feeds_from metadata) ---- */

    const lineGen = d3

      .line<{ x: number; y: number }>()

      .x((d) => d.x)

      .y((d) => d.y)

      .curve(d3.curveBasis);

    // Draw lines based on feeds_from metadata
    for (const n of nodes) {
      const feeds = n.match.feeds_from;
      if (!feeds || feeds.length === 0) continue;

      // Check if feeder nodes exist in this view
      const resolved = feeds.filter((fid: number) => nodeMap.has(fid));
      if (resolved.length === 0) {
        // Feeder matches not in view (e.g. Today on different day)
        // Fallback: connect from last bracket round
        const prevNodes = nodes.filter((nd: any) => nd.roundIdx === n.roundIdx - 1);
        if (prevNodes.length >= 2) {
          const midX = (prevNodes[0].x + BOX_W + n.x) / 2;
          const drawOne = (s: any) => {
            const pts = [
              { x: s.x + BOX_W, y: s.y + BOX_H / 2 },
              { x: midX, y: s.y + BOX_H / 2 },
              { x: midX, y: n.y + BOX_H / 2 },
              { x: n.x, y: n.y + BOX_H / 2 },
            ];
            container.append("path").attr("d", lineGen(pts))
              .attr("fill", "none").attr("stroke", COLORS.line)
              .attr("stroke-width", 2.5).attr("opacity", 0.4);
          };
          for (let pi = 0; pi < prevNodes.length - 1; pi += 2) {
            drawOne(prevNodes[pi]);
            if (prevNodes[pi + 1]) drawOne(prevNodes[pi + 1]);
          }
        }
        continue;
      }

      for (const fromId of resolved) {
        const srcNode = nodeMap.get(fromId);
        if (!srcNode) continue;

        const midX = (srcNode.x + BOX_W + n.x) / 2;
        const points = [
          { x: srcNode.x + BOX_W, y: srcNode.y + BOX_H / 2 },
          { x: midX, y: srcNode.y + BOX_H / 2 },
          { x: midX, y: n.y + BOX_H / 2 },
          { x: n.x, y: n.y + BOX_H / 2 },
        ];
        container
          .append("path")
          .attr("d", lineGen(points))
          .attr("fill", "none")
          .attr("stroke", COLORS.line)
          .attr("stroke-width", 2.5)
          .attr("opacity", 0.4);
      }
    }



    /* ---- Column labels ---- */

    const stageLabels: Record<string, string> = {

      "Group Stage": "小组赛",

      "Round of 32": "32强",

      "Round of 16": "16强",

      "Quarter-finals": "8强",

      "Semi-finals": "4强",

      "Third Place": "三四名",

      Final: "决赛",

    };



    rounds.forEach((round, ri) => {

      const label = stageLabels[round.name] || round.name;

      const x = PADDING + ri * (BOX_W + COL_GAP) + BOX_W / 2;



      container

        .append("text")

        .attr("x", x)

        .attr("y", 22)

        .attr("text-anchor", "middle")

        .attr("fill", COLORS.dimText)

        .attr("font-size", "15px")

        .attr("font-weight", "700")

        .text(label);



      const dateSet = new Set(round.matches.map((m) => m.datetime?.slice(0, 10)).filter(Boolean));

      if (dateSet.size) {

        const dates = Array.from(dateSet).map((d) => {

          if (d.includes("/")) {

            const parts = d.split("/");

            if (parts.length === 3) return `${parts[0]}/${parts[1]}`;

          }

          return d.slice(5);

        }).join(", ");

        container

          .append("text")

          .attr("x", x)

          .attr("y", 40)

          .attr("text-anchor", "middle")

          .attr("fill", COLORS.accent)

          .attr("font-size", "13px")

          .text(dates);

      }

    });



    /* ---- Draw match boxes ---- */

    nodes.forEach(({ match, x, y }) => {

      const g = container.append("g").attr("transform", `translate(${x},${y})`);



      const isToday = match.is_today === true;
      const isCompleted = !isToday && match.is_future === false && match.score && match.score !== "?-?";
      const isFuture = match.is_future === true && !isToday;

      const isChampion =

        match.stage === "Final" && match.winner && match.winner !== "TBD";

      const homeIsTBD = isTBD(match.home.name);

      const awayIsTBD = isTBD(match.away.name);

      const canEdit = isEditable(match);



      /* ---- Pick box color ---- */

      let boxColor = match.is_today ? COLORS.matchBox : COLORS.futureBox;

      let borderColor = match.is_today ? "#2a4a7a" : "#2a4a7a";

      let borderWidth = 1;

      if (isCompleted) {

        boxColor = COLORS.completedBox;

        borderColor = COLORS.completedBorder;

      }

      if (isChampion) {

        borderColor = COLORS.accent;

        borderWidth = 2.5;

      }



      /* Box background */

      const rect = g

        .append("rect")

        .attr("width", BOX_W)

        .attr("height", BOX_H)

        .attr("rx", 8)

        .attr("ry", 8)

        .attr("fill", boxColor)

        .attr("stroke", borderColor)

        .attr("stroke-width", borderWidth);



      if (isChampion) {

        rect.attr("filter", "url(#glow)").attr("class", "champion-glow");

      }



      /* Today indicator — gold left bar */

      if (match.is_today) {

        g.append("rect")

          .attr("x", 0)

          .attr("y", 0)

          .attr("width", 4)

          .attr("height", BOX_H)

          .attr("rx", 2)

          .attr("fill", COLORS.accent);

      }



      /* Home team row - dual language */

      const homeY1 = 20;

      const homeY2 = 34;

      const awayY1 = 62;

      const awayY2 = 76;

      const scoreFontSize = 20;

      const homeHasCn = !homeIsTBD && match.home.name_cn && match.home.name_cn !== match.home.name;

      const awayHasCn = !awayIsTBD && match.away.name_cn && match.away.name_cn !== match.away.name;



      /* Home flag */

      g.append("text")

        .attr("x", 12)

        .attr("y", 24)

        .attr("font-size", "18px")

        .text(homeIsTBD ? "\u2753" : match.home.flag);



      /* Home name(s) */

      if (homeHasCn) {

        g.append("text")

          .attr("x", 34)

          .attr("y", homeY1)

          .attr("fill", COLORS.text)

          .attr("font-size", "14px")

          .attr("font-weight", "600")

          .text(match.home.name_cn!);

        g.append("text")

          .attr("x", 34)

          .attr("y", homeY2)

          .attr("fill", COLORS.dimText)

          .attr("font-size", "11px")

          .text(match.home.name);

      } else {

        g.append("text")

          .attr("x", 34)

          .attr("y", 24)

          .attr("fill", homeIsTBD ? COLORS.dimText : COLORS.text)

          .attr("font-size", "16px")

          .attr("font-weight", "600")

          .text(homeIsTBD ? "待定" : match.home.name);

      }



      /* Away flag */

      g.append("text")

        .attr("x", 12)

        .attr("y", 68)

        .attr("font-size", "18px")

        .text(awayIsTBD ? "\u2753" : match.away.flag);



      /* Away name(s) */

      if (awayHasCn) {

        g.append("text")

          .attr("x", 34)

          .attr("y", awayY1)

          .attr("fill", COLORS.text)

          .attr("font-size", "14px")

          .attr("font-weight", "600")

          .text(match.away.name_cn!);

        g.append("text")

          .attr("x", 34)

          .attr("y", awayY2)

          .attr("fill", COLORS.dimText)

          .attr("font-size", "11px")

          .text(match.away.name);

      } else {

        g.append("text")

          .attr("x", 34)

          .attr("y", 68)

          .attr("fill", awayIsTBD ? COLORS.dimText : COLORS.text)

          .attr("font-size", "16px")

          .attr("font-weight", "600")

          .text(awayIsTBD ? "待定" : match.away.name);

      }



      /* ---- Score (right side) ---- */

      const scoreText = match.score || (homeIsTBD || awayIsTBD ? "?-?" : "?-?");

      const scoreColor = isCompleted ? COLORS.completedBorder : (homeIsTBD || awayIsTBD ? COLORS.dimText : (isToday ? "#ffd700" : COLORS.accent));

      g.append("text")

        .attr("x", BOX_W - 12)

        .attr("y", BOX_H / 2 + 7)

        .attr("text-anchor", "end")

        .attr("fill", scoreColor)

        .attr("font-size", `${scoreFontSize}px`)

        .attr("font-weight", "700")

        .text(scoreText);



      /* ---- Champion trophy ---- */

      if (isChampion) {

        g.append("text")

          .attr("x", BOX_W - 80)

          .attr("y", BOX_H / 2 + 8)

          .attr("font-size", "22px")

          .text("\uD83C\uDFC6");

      }



      /* ---- Badges ---- */



      /* "已完赛" badge for completed matches */

      if (isCompleted) {

        g.append("rect")

          .attr("x", BOX_W - 64)

          .attr("y", 3)

          .attr("width", 60)

          .attr("height", 18)

          .attr("rx", 9)

          .attr("fill", COLORS.completedBorder)

          .attr("opacity", 0.25);

        g.append("text")

          .attr("x", BOX_W - 35)

          .attr("y", 15)

          .attr("text-anchor", "middle")

          .attr("fill", COLORS.completedBorder)

          .attr("font-size", "10px")

          .attr("font-weight", "700")

          .text("\u2705 \u5DF2\u5B8C\u8D5B");

      }



      /* "今日预测" badge for today's matches */

      if (isToday && !isCompleted) {

        g.append("rect")

          .attr("x", BOX_W - 72)

          .attr("y", 3)

          .attr("width", 68)

          .attr("height", 18)

          .attr("rx", 9)

          .attr("fill", COLORS.accent)

          .attr("opacity", 0.3);

        g.append("text")

          .attr("x", BOX_W - 39)

          .attr("y", 15)

          .attr("text-anchor", "middle")

          .attr("fill", COLORS.accent)

          .attr("font-size", "10px")

          .attr("font-weight", "700")

          .text("\uD83D\uDD2E \u4ECA\u65E5\u9884\u6D4B");

      }



      /* "预测" badge for future matches */

      if (isFuture && !isToday && !isCompleted && !homeIsTBD && !awayIsTBD) {

        g.append("rect")

          .attr("x", BOX_W - 52)

          .attr("y", 3)

          .attr("width", 48)

          .attr("height", 18)

          .attr("rx", 9)

          .attr("fill", "#4a2a6a")

          .attr("opacity", 0.5);

        g.append("text")

          .attr("x", BOX_W - 29)

          .attr("y", 15)

          .attr("text-anchor", "middle")

          .attr("fill", "#b080d0")

          .attr("font-size", "10px")

          .attr("font-weight", "700")

          .text("\uD83D\uDCC5 \u9884\u6D4B");

      }



      /* ---- Winner indicator ---- */

      if (match.winner && match.winner !== "TBD") {

        const isHomeWinner = match.winner === match.home.name;

        const homeWinY = homeY1 + 2;

        const awayWinY = awayY2 - 2;

        // Gold dot next to winner side

        g.append("circle")

          .attr("cx", BOX_W - 4)

          .attr("cy", isHomeWinner ? homeWinY : awayWinY)

          .attr("r", 4)

          .attr("fill", COLORS.accent);

        // Up/Down arrow

        g.append("text")

          .attr("x", BOX_W - 14)

          .attr("y", isHomeWinner ? homeWinY + 4 : awayWinY + 4)

          .attr("text-anchor", "end")

          .attr("fill", COLORS.accent)

          .attr("font-size", "10px")

          .text(isHomeWinner ? "\u25B2" : "\u25BC");

      }

      /* ---- Penalty winner badge ---- */

      if (match.penalty_winner && match.penalty_winner !== "") {

        g.append("rect")

          .attr("x", BOX_W / 2 - 30)

          .attr("y", BOX_H - 21)

          .attr("width", 60)

          .attr("height", 18)

          .attr("rx", 4)

          .attr("fill", COLORS.accent)

          .attr("opacity", 0.2);

        g.append("text")

          .attr("x", BOX_W / 2)

          .attr("y", BOX_H - 8)

          .attr("text-anchor", "middle")

          .attr("fill", COLORS.accent)

          .attr("font-size", "10px")

          .attr("font-weight", "700")

          .text("\uD83D\uDC4F \u70B9\u7403\u53D6\u80DC");

      }



      /* ---- Invisible hover area (full box) — sticky tooltip (no mouseleave clear) ---- */
      g.append("rect")
        .attr("width", BOX_W)
        .attr("height", BOX_H)
        .attr("rx", 8)
        .attr("ry", 8)
        .attr("fill", "transparent")
        .attr("cursor", "pointer")
        .on("mouseenter", (event: MouseEvent) => {
          if (homeIsTBD) return;
          onHoverTeam(
            {
              home: { name: match.home.name, flag: match.home.flag, features: match.home.features as unknown as Record<string, number> },
              away: { name: match.away.name, flag: match.away.flag, features: match.away.features as unknown as Record<string, number> },
              homeWinProb: match.home_win_prob,
              awayWinProb: match.away_win_prob,
              drawProb: match.probabilities?.draw ?? 0,
              score: match.score,
            },
            { x: event.pageX, y: event.pageY }
          );
        });
      // NOTE: no mouseleave — tooltip stays visible until user clicks close or hovers another match



      /* ---- Edit buttons — only for editable matches (rendered on top) ---- */

      if (canEdit) {

        const btnSize = 24;

        const btnRadius = 5;



        /* Home edit — top-right corner */

        const homeEditG = g.append("g").attr("class", "edit-btn-group").attr("cursor", "pointer");

        homeEditG

          .append("rect")

          .attr("x", BOX_W - btnSize - 4)

          .attr("y", 3)

          .attr("width", btnSize + 2)

          .attr("height", btnSize - 2)

          .attr("rx", btnRadius)

          .attr("ry", btnRadius)

          .attr("fill", COLORS.accent);

        homeEditG

          .append("text")

          .attr("x", BOX_W - btnSize / 2 - 2)

          .attr("y", 20)

          .attr("text-anchor", "middle")

          .attr("font-size", "14px")

          .attr("fill", "#000")

          .text("\u270F\uFE0F");

        homeEditG

          .append("rect")

          .attr("x", BOX_W - btnSize - 8)

          .attr("y", 0)

          .attr("width", btnSize + 8)

          .attr("height", BOX_H / 2)

          .attr("fill", "transparent")

          .on("click", (event: MouseEvent) => {

            event.stopPropagation();

            onEditTeam(match.match_id, "home");

          });



        /* Away edit — bottom-right corner (mirror) */

        const awayEditG = g.append("g").attr("class", "edit-btn-group").attr("cursor", "pointer");

        awayEditG

          .append("rect")

          .attr("x", BOX_W - btnSize - 4)

          .attr("y", BOX_H / 2 + 3)

          .attr("width", btnSize + 2)

          .attr("height", btnSize - 2)

          .attr("rx", btnRadius)

          .attr("ry", btnRadius)

          .attr("fill", COLORS.accent);

        awayEditG

          .append("text")

          .attr("x", BOX_W - btnSize / 2 - 2)

          .attr("y", BOX_H / 2 + 20)

          .attr("text-anchor", "middle")

          .attr("font-size", "14px")

          .attr("fill", "#000")

          .text("\u270F\uFE0F");

        awayEditG

          .append("rect")

          .attr("x", BOX_W - btnSize - 8)

          .attr("y", BOX_H / 2)

          .attr("width", btnSize + 8)

          .attr("height", BOX_H / 2)

          .attr("fill", "transparent")

          .on("click", (event: MouseEvent) => {

            event.stopPropagation();

            onEditTeam(match.match_id, "away");

          });



        /* ---- Hover hint for edit buttons ---- */

        container

          .append("text")

          .attr("x", x + BOX_W - 38)

          .attr("y", y - 6)

          .attr("fill", COLORS.accent)

          .attr("font-size", "11px")

          .attr("text-anchor", "end")

          .attr("opacity", 0)

          .attr("class", "edit-hint")

          .text("点击更换球队");

      }

    });

  }, [data, onEditTeam, onHoverTeam, zoomMode]);



  useEffect(() => {

    layout();

  }, [layout]);



  const zoomIn = () => {
    if (zoomRef.current && svgRef.current) {
      d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 1.3);
    }
  };
  const zoomOut = () => {
    if (zoomRef.current && svgRef.current) {
      d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 0.7);
    }
  };
  const zoomReset = () => {
    if (zoomRef.current && svgRef.current) {
      d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.transform, d3.zoomIdentity);
    }
  };

  return (

    <div className="w-full overflow-auto" style={{ position: "relative", minHeight: "400px" }}>

      <svg ref={svgRef} style={{ width: "100%", display: "block" }} />

      {/* Controls: mode toggle + zoom buttons (top-left, zoom off by default) */}
      <div style={{ position: "absolute", top: 12, left: 12, zIndex: 50, display: "flex", gap: 6, alignItems: "center" }}>
        <button onClick={() => setZoomMode(!zoomMode)}
          style={{ width: 44, height: 36, borderRadius: 6, border: "1px solid " + (zoomMode ? "#2a8a4a" : "#3a5a8a"), background: zoomMode ? "#1a3a2a" : "#1a2d4a", color: zoomMode ? "#4aed8a" : "#8899bb", fontSize: 11, fontWeight: "bold", cursor: "pointer", lineHeight: "36px", textAlign: "center" }}
          title={zoomMode ? "点击切换到拖动模式" : "点击切换到缩放模式"}>{zoomMode ? "拖动" : "缩放"}</button>
        <button onClick={zoomIn}
          style={{ width: 36, height: 36, borderRadius: 6, background: "#1a2d4a", border: "1px solid #3a5a8a", color: "#f0c040", fontSize: 18, fontWeight: "bold", cursor: "pointer", lineHeight: "36px", textAlign: "center" }}
          title="放大">+</button>
        <button onClick={zoomOut}
          style={{ width: 36, height: 36, borderRadius: 6, background: "#1a2d4a", border: "1px solid #3a5a8a", color: "#f0c040", fontSize: 18, fontWeight: "bold", cursor: "pointer", lineHeight: "36px", textAlign: "center" }}
          title="缩小">−</button>
        <button onClick={zoomReset}
          style={{ width: 36, height: 36, borderRadius: 6, background: "#1a2d4a", border: "1px solid #3a5a8a", color: "#8899bb", fontSize: 12, cursor: "pointer", lineHeight: "36px", textAlign: "center" }}
          title="重置缩放">⟲</button>
      </div>

    </div>

  );

}

