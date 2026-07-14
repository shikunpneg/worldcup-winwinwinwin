import type { GroupData, Round } from "../types";

interface Props {
  groups: GroupData[];
  rounds?: Round[];
}

export default function GroupStandings({ groups, rounds }: Props) {
  if (!groups || groups.length === 0) return null;

  // Build a map: team_name -> R32 match label
  const r32Map = new Map<string, string>();
  if (rounds) {
    const r32 = rounds.find((r) => r.name === "Round of 32");
    if (r32) {
      r32.matches.forEach((m, mi) => {
        r32Map.set(m.home.name, `32强 #${mi + 1}`);
        r32Map.set(m.away.name, `32强 #${mi + 1}`);
      });
    }
  }

  return (
    <div className="mb-6">
      <h2 className="mb-3 text-center text-sm font-bold uppercase tracking-wider text-[#f0c040]">
        📋 小组赛积分榜
      </h2>
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
        {groups.map((grp) => (
          <div
            key={grp.name}
            className="overflow-hidden rounded-lg border border-[#1a2d4a] bg-[#0a1424]/80 text-xs"
          >
            {/* Group header */}
            <div className="border-b border-[#1a2d4a] bg-[#0f1a2e] px-2 py-1.5 text-center font-bold text-[#f0c040]">
              {grp.name}
            </div>

            {/* Team rows */}
            <table className="w-full">
              <thead>
                <tr className="text-[9px] text-[#556688]">
                  <th className="w-5 px-1 py-0.5 text-left">#</th>
                  <th className="px-1 py-0.5 text-left">球队</th>
                  <th className="w-5 px-0.5 py-0.5 text-center">赛</th>
                  <th className="w-5 px-0.5 py-0.5 text-center">胜</th>
                  <th className="w-5 px-0.5 py-0.5 text-center">平</th>
                  <th className="w-5 px-0.5 py-0.5 text-center">负</th>
                  <th className="w-5 px-0.5 py-0.5 text-center">进</th>
                  <th className="w-5 px-0.5 py-0.5 text-center">失</th>
                  <th className="w-5 px-0.5 py-0.5 text-center">净</th>
                  <th className="w-6 px-1 py-0.5 text-center">分</th>
                </tr>
              </thead>
              <tbody>
                {grp.teams.map((t) => (
                  <tr
                    key={t.name}
                    className={`border-t border-[#1a2d4a]/50 ${
                      t.qualified ? "bg-[#0a2a1a]/40" : ""
                    }`}
                  >
                    <td className="px-1 py-1 text-center text-[#8899bb]">
                      {t.rank}
                    </td>
                    <td className="px-1 py-1">
                      <div className="flex items-center gap-1">
                        <span className="text-sm">{t.flag}</span>
                        <div className="flex flex-col leading-tight">
                          <span className={`truncate font-medium ${t.qualified ? "text-[#2a8a4a]" : "text-[#e8e8e8]"}`}>
                            {t.name_cn || t.name}
                          </span>
                          {t.name_cn && t.name_cn !== t.name && (
                            <span className="truncate text-[9px] text-[#8899bb]">{t.name}</span>
                          )}
                        </div>
                        {t.qualified && (
                          <>
                            <span className="ml-auto rounded bg-[#2a8a4a]/20 px-1 text-[9px] text-[#2a8a4a]">
                              晋级
                            </span>
                            {r32Map.has(t.name) && (
                              <span className="ml-0.5 rounded bg-[#1a2d4a] px-1 text-[9px] text-[#f0c040]">
                                {r32Map.get(t.name)}
                              </span>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                    <td className="px-0.5 py-1 text-center text-[#8899bb]">{t.mp}</td>
                    <td className="px-0.5 py-1 text-center text-[#e8e8e8]">{t.wins}</td>
                    <td className="px-0.5 py-1 text-center text-[#8899bb]">{t.draws}</td>
                    <td className="px-0.5 py-1 text-center text-[#8899bb]">{t.losses}</td>
                    <td className="px-0.5 py-1 text-center text-[#e8e8e8]">{t.goals_for}</td>
                    <td className="px-0.5 py-1 text-center text-[#8899bb]">{t.goals_against}</td>
                    <td className="px-0.5 py-1 text-center font-medium text-[#e8e8e8]">
                      {t.goal_diff > 0 ? `+${t.goal_diff}` : t.goal_diff}
                    </td>
                    <td className="px-1 py-1 text-center font-bold text-[#f0c040]">{t.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}
