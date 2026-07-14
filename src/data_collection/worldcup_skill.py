"""
WorldCupDataSkill - 2026 World Cup data collection skill.
Collects matches, standings, team stats, cards, market values, and coaches data.
"""

import os
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime

from .api_client import ApiClient
from .static_data import get_coach, get_cards
from .players import get_market_value, get_top_scorers, get_team_top_scorers, get_team_assisters
from .utils import SimpleCache, ensure_dir, safe_int


# Map game type to stage label
STAGE_MAP = {
    "group": "Group Stage",
    "r32": "Round of 32",
    "r16": "Round of 16",
    "qf": "Quarter-finals",
    "sf": "Semi-finals",
    "third": "Third Place",
    "final": "Final",
}


class WorldCupDataSkill:
    """Main skill class for World Cup data collection."""

    def __init__(self, data_dir: str = "./worldcup_data", cache_ttl: int = 60):
        self.data_dir = data_dir
        self.cache = SimpleCache(ttl=cache_ttl)
        self.api = ApiClient()
        ensure_dir(self.data_dir)

    def collect_all(self) -> Dict[str, pd.DataFrame]:
        """Collect all data and return as a dictionary of DataFrames."""
        print("[INFO] Starting full data collection...")

        matches = self.fetch_matches()
        standings = self.fetch_standings()
        team_stats = self.fetch_team_stats()
        cards = self.fetch_cards()
        players = self.fetch_players()

        print("[INFO] Data collection complete.")
        return {
            "matches": matches,
            "standings": standings,
            "team_stats": team_stats,
            "cards": cards,
            "players": players,
        }

    def fetch_matches(self) -> pd.DataFrame:
        """Fetch all matches from the API."""
        cached = self.cache.get("matches")
        if cached is not None:
            print("[INFO] Returning cached matches data.")
            return cached

        print("[INFO] Fetching matches from API...")
        data = self.api.get_games()

        if not data:
            print("[WARN] No match data received from API, returning empty DataFrame.")
            df = pd.DataFrame(columns=[
                "match_id", "group", "stage", "home_team",
                "away_team", "home_score", "away_score",
                "status", "datetime", "stadium"
            ])
            self.cache.set("matches", df)
            return df

        rows = []
        for m in data:
            if not isinstance(m, dict):
                continue

            # Determine match status
            time_elapsed = m.get("time_elapsed", "notstarted")
            finished = str(m.get("finished", "FALSE")).upper()
            if finished == "TRUE":
                status = "completed"
            elif time_elapsed and str(time_elapsed).lower() not in ("notstarted", ""):
                status = "live"
            else:
                status = "scheduled"

            # Map stage
            game_type = m.get("type", "group")
            stage = STAGE_MAP.get(game_type, game_type)

            # Determine group (group matches only)
            group = m.get("group", "")
            game_id = m.get("id", m.get("_id", ""))

            # Parse score
            home_score = m.get("home_score")
            away_score = m.get("away_score")

            rows.append({
                "match_id": game_id,
                "group": group,
                "stage": stage,
                "home_team": m.get("home_team_name_en", m.get("home_team_label", "")),
                "away_team": m.get("away_team_name_en", m.get("away_team_label", "")),
                "home_score": safe_int(home_score) if home_score not in (None, "", "null", "-") else 0,
                "away_score": safe_int(away_score) if away_score not in (None, "", "null", "-") else 0,
                "status": status,
                "datetime": m.get("date", m.get("local_date", "")),
                "stadium": m.get("stadium_id", ""),
            })

        df = pd.DataFrame(rows)

        # Sort by match_id if possible
        if not df.empty and "match_id" in df.columns:
            try:
                df["match_id_num"] = pd.to_numeric(df["match_id"], errors="coerce")
                df = df.sort_values("match_id_num").drop(columns=["match_id_num"])
            except (KeyError, ValueError):
                pass

        self.cache.set("matches", df)
        print(f"[INFO] Loaded {len(df)} matches.")
        return df

    def fetch_standings(self) -> pd.DataFrame:
        """Fetch group standings from the API via groups data."""
        cached = self.cache.get("standings")
        if cached is not None:
            print("[INFO] Returning cached standings data.")
            return cached

        print("[INFO] Fetching standings from API...")

        # Try to get standings from match data (compute from completed matches)
        matches = self.fetch_matches()
        if matches.empty:
            df = pd.DataFrame(columns=[
                "group", "team", "rank", "points", "matches_played",
                "wins", "draws", "losses", "goals_for", "goals_against", "goal_diff"
            ])
            self.cache.set("standings", df)
            return df

        completed = matches[
            matches["status"].str.lower().isin(["completed", "finished", "ft", "final"])
        ].copy()

        # Only group stage matches count for standings
        group_matches = completed[completed["stage"] == "Group Stage"].copy()

        if group_matches.empty:
            # If no group matches completed, use all completed matches
            group_matches = completed

        # Compute standings per group
        standings = {}
        for _, row in group_matches.iterrows():
            group = row.get("group", "Unknown")
            home = row["home_team"]
            away = row["away_team"]
            hs = row["home_score"]
            as_ = row["away_score"]

            for team in [home, away]:
                key = (group, team)
                if key not in standings:
                    standings[key] = {
                        "group": group, "team": team,
                        "mp": 0, "w": 0, "d": 0, "l": 0,
                        "gf": 0, "ga": 0,
                    }

            standings[(group, home)]["mp"] += 1
            standings[(group, away)]["mp"] += 1
            standings[(group, home)]["gf"] += hs
            standings[(group, home)]["ga"] += as_
            standings[(group, away)]["gf"] += as_
            standings[(group, away)]["ga"] += hs

            if hs > as_:
                standings[(group, home)]["w"] += 1
                standings[(group, away)]["l"] += 1
            elif hs < as_:
                standings[(group, away)]["w"] += 1
                standings[(group, home)]["l"] += 1
            else:
                standings[(group, home)]["d"] += 1
                standings[(group, away)]["d"] += 1

        # Build rows with ranking
        rows = []
        # Group by group name
        from itertools import groupby
        sorted_items = sorted(standings.values(), key=lambda x: (x["group"], -(x["w"]*3 + x["d"]), -(x["gf"] - x["ga"])))
        for grp, grp_items in groupby(sorted_items, key=lambda x: x["group"]):
            grp_list = sorted(grp_items, key=lambda x: (-(x["w"]*3 + x["d"]), -(x["gf"] - x["ga"]), -(x["gf"])))
            for rank, s in enumerate(grp_list, 1):
                gd = s["gf"] - s["ga"]
                pts = s["w"] * 3 + s["d"]
                rows.append({
                    "group": s["group"],
                    "team": s["team"],
                    "rank": rank,
                    "points": pts,
                    "matches_played": s["mp"],
                    "wins": s["w"],
                    "draws": s["d"],
                    "losses": s["l"],
                    "goals_for": s["gf"],
                    "goals_against": s["ga"],
                    "goal_diff": gd,
                })

        df = pd.DataFrame(rows)
        self.cache.set("standings", df)
        groups_count = df["group"].nunique() if not df.empty and "group" in df.columns else 0
        print(f"[INFO] Computed standings for {len(df)} teams across {groups_count} groups.")
        return df

    def fetch_team_stats(self) -> pd.DataFrame:
        """Compute team statistics from matches data."""
        cached = self.cache.get("team_stats")
        if cached is not None:
            return cached

        print("[INFO] Computing team statistics...")
        matches = self.fetch_matches()
        if matches.empty:
            df = pd.DataFrame(columns=[
                "team", "matches_played", "wins", "draws", "losses",
                "goals_for", "goals_against", "goal_diff", "points",
                "market_value", "coach"
            ])
            self.cache.set("team_stats", df)
            return df

        played = matches[matches["status"].str.lower().isin(["completed", "finished", "ft", "final"])].copy()

        stats = {}
        for _, row in played.iterrows():
            home = row["home_team"]
            away = row["away_team"]
            hs = row["home_score"]
            as_ = row["away_score"]

            for team in [home, away]:
                if not team:
                    continue
                if team not in stats:
                    stats[team] = {"wins": 0, "draws": 0, "losses": 0,
                                   "gf": 0, "ga": 0, "matches": 0}

            if not home or not away:
                continue

            stats[home]["matches"] += 1
            stats[away]["matches"] += 1
            stats[home]["gf"] += hs
            stats[home]["ga"] += as_
            stats[away]["gf"] += as_
            stats[away]["ga"] += hs

            if hs > as_:
                stats[home]["wins"] += 1
                stats[away]["losses"] += 1
            elif hs < as_:
                stats[away]["wins"] += 1
                stats[home]["losses"] += 1
            else:
                stats[home]["draws"] += 1
                stats[away]["draws"] += 1

        rows = []
        for team, s in stats.items():
            c = get_cards(team)
            rows.append({
                "team": team,
                "matches_played": s["matches"],
                "wins": s["wins"],
                "draws": s["draws"],
                "losses": s["losses"],
                "goals_for": s["gf"],
                "goals_against": s["ga"],
                "goal_diff": s["gf"] - s["ga"],
                "points": s["wins"] * 3 + s["draws"],
                "market_value": get_market_value(team),
                "coach": get_coach(team),
                "yellow_cards": c["yellow"],
                "red_cards": c["red"],
                "fouls": c["fouls"],
                "fair_play_score": c["yellow"] * 1 + c["red"] * 4,
            })

        df = pd.DataFrame(rows).sort_values("points", ascending=False).reset_index(drop=True)
        self.cache.set("team_stats", df)
        print(f"[INFO] Computed stats for {len(df)} teams.")
        return df

    def fetch_cards(self) -> pd.DataFrame:
        """Fetch cards/discipline data from static source."""
        cached = self.cache.get("cards")
        if cached is not None:
            return cached

        # Build from static data for all teams in matches
        print("[INFO] Loading cards data from static source...")
        matches = self.fetch_matches()

        # Collect all unique team names
        teams = set()
        if not matches.empty:
            all_teams = pd.concat([
                matches[matches["status"] == "completed"]["home_team"],
                matches[matches["status"] == "completed"]["away_team"]
            ]).unique()
            teams = set(t for t in all_teams if t)

        if not teams:
            df = pd.DataFrame(columns=["team", "yellow_cards", "red_cards", "fouls", "fair_play_score"])
            self.cache.set("cards", df)
            return df

        rows = []
        for team in sorted(teams):
            c = get_cards(team)
            fair_play = c["yellow"] * 1 + c["red"] * 4
            rows.append({
                "team": team,
                "yellow_cards": c["yellow"],
                "red_cards": c["red"],
                "fouls": c["fouls"],
                "fair_play_score": fair_play,
            })

        df = pd.DataFrame(rows).sort_values("fair_play_score").reset_index(drop=True)
        self.cache.set("cards", df)
        print(f"[INFO] Loaded cards data for {len(df)} teams.")
        return df

    def fetch_market_values(self) -> Dict[str, int]:
        """Return market value mapping."""
        from .players import TEAM_MARKET_VALUES
        return dict(TEAM_MARKET_VALUES)

    def fetch_coaches(self) -> Dict[str, str]:
        """Return coach mapping."""
        from .static_data import COACHES
        return dict(COACHES)

    def fetch_players(self) -> pd.DataFrame:
        """Fetch top scorers and key player stats."""
        cached = self.cache.get("players")
        if cached is not None:
            return cached

        print("[INFO] Building player statistics from match data...")
        matches = self.fetch_matches()

        # Extract scorers from API match data
        team_players = {}  # team -> {player -> goals}
        if not matches.empty:
            data = self.api.get_games()
            if data:
                for g in data:
                    if g.get('finished') != 'TRUE':
                        continue
                    ht = g.get('home_team_name_en', '')
                    at = g.get('away_team_name_en', '')
                    for team_name, scorer_field in [(ht, 'home_scorers'), (at, 'away_scorers')]:
                        scorers_str = g.get(scorer_field, 'null')
                        if not scorers_str or scorers_str == 'null':
                            continue
                        import re
                        scorers_str = scorers_str.strip('{}"').strip('"')
                        entries = re.findall(r'"([^"]*)"', scorers_str)
                        if not entries:
                            entries = [s.strip() for s in scorers_str.split(',')]
                        for entry in entries:
                            m = re.match(r'([\w\s\.\'\-\u00C0-\u024F]+?)\s+(\d+)\'?', entry)
                            pname = m.group(1).strip() if m else entry.strip().rstrip("'").strip()
                            if not pname or len(pname) < 2:
                                continue
                            if team_name not in team_players:
                                team_players[team_name] = {}
                            team_players[team_name][pname] = team_players[team_name].get(pname, 0) + 1

        # Build DataFrame
        rows = []
        # Add known top scorers from ESPN data
        from .players import TOP_SCORERS
        for name, data in sorted(TOP_SCORERS.items(), key=lambda x: -x[1]["goals"]):
            rows.append({
                "player": name,
                "team": data["team"],
                "position": data.get("position", ""),
                "goals": data["goals"],
                "assists": data.get("assists", 0),
            })

        # Also add goalscorers from API that are not in top scorers
        api_players_added = set(name for name in TOP_SCORERS)
        for team_name, scorers in team_players.items():
            for pname, goals in sorted(scorers.items(), key=lambda x: -x[1]):
                if pname not in api_players_added and goals >= 1:
                    rows.append({
                        "player": pname,
                        "team": team_name,
                        "position": "",
                        "goals": goals,
                        "assists": 0,
                    })
                    api_players_added.add(pname)

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("goals", ascending=False).reset_index(drop=True)

        self.cache.set("players", df)
        print(f"[INFO] Player stats for {len(df)} players.")
        return df

    def get_quarter_finalists(self) -> List[str]:
        """Get current quarter-finalists based on standings."""
        print("[INFO] Determining quarter-finalists...")
        standings = self.fetch_standings()
        if standings.empty:
            print("[WARN] No standings data available.")
            return []

        # Top 2 from each group advance
        top_teams = (
            standings.sort_values(
                ["group", "points", "goal_diff", "goals_for"],
                ascending=[True, False, False, False]
            )
            .groupby("group")
            .head(2)["team"]
            .tolist()
        )
        return top_teams

    def get_teams_by_group(self) -> Dict[str, List[str]]:
        """Get teams grouped by their group."""
        standings = self.fetch_standings()
        if standings.empty:
            return {}
        result = {}
        for grp in sorted(standings["group"].unique()):
            grp_data = standings[standings["group"] == grp].sort_values("rank")
            result[grp] = grp_data["team"].tolist()
        return result

    def export_csv(self, data_dict: Dict[str, pd.DataFrame]):
        """Export all DataFrames to CSV files."""
        print(f"[INFO] Exporting data to {self.data_dir}...")
        ensure_dir(self.data_dir)

        for name, df in data_dict.items():
            if df is not None and not df.empty:
                path = os.path.join(self.data_dir, f"{name}.csv")
                df.to_csv(path, index=False, encoding="utf-8-sig")
                print(f"  -> Saved {path} ({len(df)} rows)")
            else:
                print(f"  -> Skipped {name} (no data)")

        print("[INFO] Export complete.")

    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        print("[INFO] Cache cleared.")


def print_data_summary(data: Dict[str, pd.DataFrame]):
    """Print a summary of collected data."""
    print("\n" + "=" * 60)
    print("DATA COLLECTION SUMMARY")
    print("=" * 60)
    for name, df in data.items():
        if df is not None and not df.empty:
            print(f"\n[{name.upper()}] - {len(df)} rows")
            print(df.to_string(max_rows=8))
        else:
            print(f"\n[{name.upper()}] - No data")


if __name__ == "__main__":
    skill = WorldCupDataSkill()
    data = skill.collect_all()
    skill.export_csv(data)
    print_data_summary(data)

    qf = skill.get_quarter_finalists()
    print(f"\nCurrent round-of-16 qualifiers (top 2 per group): {qf}")
