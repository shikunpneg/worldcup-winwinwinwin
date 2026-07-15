"""
FastAPI backend for World Cup 2026 prediction visualization.
Wraps existing trainable_elo.py models as REST APIs.

Endpoints:
  GET  /api/today?date=      -> 日视图: 当天赛程树 + 球队特征
  GET  /api/panorama         -> 全景模式: 完整 bracket
  POST /api/simulate         -> 编辑球队, 重新预测
  GET  /api/teams            -> 所有球队列表 (供编辑下拉用)
"""

import sys, os, json, pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, date as Date
from dataclasses import dataclass

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.prediction import trainable_elo as elo_mod
from src.prediction.trainable_elo import (
    TournamentPredictor, WorldCupPredictor, EloConfig,
    HyperparameterSearch,
)
from src.data_collection.worldcup_skill import WorldCupDataSkill
from src.data_collection.team_advanced_stats import (
    get_team_stats, get_sot_per_game, get_possession,
    get_pressing_intensity, get_build_up_score, get_chances_created_pg,
    star_goals_power, get_team_stamina_by_players,
)

# ============================================================
#  Model persistence path
# ============================================================
MODEL_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_cache.pkl")

# Global prediction cache: key=date_string, value=DataFrame
_date_prediction_cache: Dict[str, pd.DataFrame] = {}

# ============================================================
#  FLAG EMOJI MAP (48 teams)
# ============================================================

FLAG_MAP = {
    "Algeria": "\U0001F1E9\U0001F1FF",
    "Argentina": "\U0001F1E6\U0001F1F7",
    "Australia": "\U0001F1E6\U0001F1FA",
    "Austria": "\U0001F1E6\U0001F1F9",
    "Belgium": "\U0001F1E7\U0001F1EA",
    "Bosnia and Herzegovina": "\U0001F1E7\U0001F1E6",
    "Brazil": "\U0001F1E7\U0001F1F7",
    "Canada": "\U0001F1E8\U0001F1E6",
    "Cape Verde": "\U0001F1E8\U0001F1FB",
    "Colombia": "\U0001F1E8\U0001F1F4",
    "Croatia": "\U0001F1ED\U0001F1F7",
    "Curacao": "\U0001F1E8\U0001F1FC",
    "Curaçao": "\U0001F1E8\U0001F1FC",
    "Czech Republic": "\U0001F1E8\U0001F1FF",
    "Democratic Republic of the Congo": "\U0001F1E8\U0001F1E9",
    "Ecuador": "\U0001F1EA\U0001F1E8",
    "Egypt": "\U0001F1EA\U0001F1EC",
    "England": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
    "France": "\U0001F1EB\U0001F1F7",
    "Germany": "\U0001F1E9\U0001F1EA",
    "Ghana": "\U0001F1EC\U0001F1ED",
    "Haiti": "\U0001F1ED\U0001F1F9",
    "Iran": "\U0001F1EE\U0001F1F7",
    "Iraq": "\U0001F1EE\U0001F1F6",
    "Ivory Coast": "\U0001F1E8\U0001F1EE",
    "Japan": "\U0001F1EF\U0001F1F5",
    "Jordan": "\U0001F1EF\U0001F1F4",
    "Mexico": "\U0001F1F2\U0001F1FD",
    "Morocco": "\U0001F1F2\U0001F1E6",
    "Netherlands": "\U0001F1F3\U0001F1F1",
    "New Zealand": "\U0001F1F3\U0001F1FF",
    "Norway": "\U0001F1F3\U0001F1F4",
    "Panama": "\U0001F1F5\U0001F1E6",
    "Paraguay": "\U0001F1F5\U0001F1FE",
    "Portugal": "\U0001F1F5\U0001F1F9",
    "Qatar": "\U0001F1F6\U0001F1E6",
    "Saudi Arabia": "\U0001F1F8\U0001F1E6",
    "Scotland": "\U0001F1EC\U0001F1E7",
    "Senegal": "\U0001F1F8\U0001F1F3",
    "South Africa": "\U0001F1FF\U0001F1E6",
    "South Korea": "\U0001F1F0\U0001F1F7",
    "Spain": "\U0001F1EA\U0001F1F8",
    "Sweden": "\U0001F1F8\U0001F1EA",
    "Switzerland": "\U0001F1E8\U0001F1ED",
    "Tunisia": "\U0001F1F9\U0001F1F3",
    "Turkey": "\U0001F1F9\U0001F1F7",
    "United States": "\U0001F1FA\U0001F1F8",
    "Uruguay": "\U0001F1FA\U0001F1FE",
    "Uzbekistan": "\U0001F1FA\U0001F1FF",
}

# ============================================================
#  GLOBAL STATE
# ============================================================

predictor: Optional[TournamentPredictor] = None
matches_df: Optional[pd.DataFrame] = None
team_stats_df: Optional[pd.DataFrame] = None
skill: Optional[WorldCupDataSkill] = None
calibrated_config: Optional[EloConfig] = None
market_values: Dict[str, int] = {}
all_predictions: Optional[pd.DataFrame] = None
calibrated_accuracy: float = 0.0
calibrated_total: int = 0
calibrated_correct: int = 0

# ============================================================
#  PYDANTIC MODELS
# ============================================================

class TeamEdit(BaseModel):
    match_id: int
    home: str
    away: str
    injury_home: Optional[float] = 0.0
    injury_away: Optional[float] = 0.0

class SimulateRequest(BaseModel):
    mode: str = "day"
    date: Optional[str] = None
    edits: List[TeamEdit] = []

# ============================================================
#  FASTAPI APP
# ============================================================

app = FastAPI(title="World Cup 2026 Prediction API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
#  HELPERS
# ============================================================

def _parse_date(d: str) -> str:
    """Normalize date string to YYYY-MM-DD format."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return d


def _match_date(match_row: pd.Series) -> str:
    """Extract date from match row regardless of format."""
    raw = match_row.get("datetime", "")
    if isinstance(raw, datetime):
        return raw.strftime("%Y-%m-%d")
    dt = str(raw) if raw else ""
    if not dt or dt == "nan":
        return ""
    clean = dt.strip().replace("T", " ")[:16]
    for fmt in ("%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M",
                "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return clean[:10]


def _filter_matches_by_date(selected_date: str) -> pd.DataFrame:
    """Filter matches_df to simulate knowledge state at a specific date.

    Only completed matches BEFORE selected_date remain as "completed" (for training).
    All other matches become "scheduled" (to be predicted).
    """
    global matches_df
    if matches_df is None or matches_df.empty:
        return pd.DataFrame()
    df = matches_df.copy()
    dates = df.apply(_match_date, axis=1)
    historical = (
        df["status"].str.lower().isin(["completed", "finished", "ft", "final"]) &
        (dates < selected_date) & (dates != "")
    )
    df.loc[~historical, "status"] = "scheduled"
    return df


def _get_team_features(team: str) -> Dict[str, Any]:
    """Compute the 11 features for a single team (absolute values)."""
    if team == "TBD":
        return {k: 0 for k in ["points","elo","goals_against_per_game","market_value",
                "stamina","chances_created_pg","possession","pressing_intensity",
                "build_up_score","sot_per_game","star_goals"]}
    global team_stats_df, predictor

    stats = get_team_stats(team)
    ts = team_stats_df[team_stats_df["team"] == team]
    if ts.empty:
        mp, ga, pts = 1, 0, 0
        mv = market_values.get(team, 0)
    else:
        ts = ts.iloc[0]
        mp = max(int(ts["matches_played"]), 1)
        ga = int(ts.get("goals_against", 0))
        pts = int(ts.get("points", 0))
        mv = market_values.get(team, 0)

    elo_rating = 1500.0
    if predictor and predictor.predictor and predictor.predictor.elo:
        elo_rating = predictor.predictor.elo.get_rating(team)

    return {
        "points": pts,
        "elo": round(elo_rating, 1),
        "goals_against_per_game": round(ga / mp, 2),
        "market_value": round(mv / 1e8, 2),
        "stamina": get_team_stamina_by_players(team),
        "chances_created_pg": get_chances_created_pg(team),
        "possession": get_possession(team),
        "pressing_intensity": get_pressing_intensity(team),
        "build_up_score": get_build_up_score(team),
        "sot_per_game": get_sot_per_game(team),
        "star_goals": star_goals_power(team),
    }


def _team_node(name: str) -> Dict:
    """Build a team node with flag, features, name_cn."""
    return {
        "name": name,
        "name_cn": CN_NAME_MAP.get(name, name),
        "flag": FLAG_MAP.get(name, "\U0001F3F3"),
        "features": _get_team_features(name),
    }


def _build_match_response(
    match_id: int, stage: str, datetime_str: str,
    home_name: str, away_name: str,
    pred: Optional[Dict] = None,
    is_today: bool = False,
    is_future: bool = False,
    actual_score: Optional[str] = None,
) -> Dict:
    """Build a single match response dict."""
    home_node = _team_node(home_name)
    away_node = _team_node(away_name)

    result = {
        "match_id": match_id,
        "stage": stage,
        "datetime": datetime_str,
        "home": home_node,
        "away": away_node,
        "is_today": is_today,
        "is_future": is_future,
        "feeds_from": _compute_feeds_from(home_name, away_name, stage),
    }

    # Actual score from data takes priority over prediction
    if actual_score:
        result["score"] = actual_score
        # Compute winner from actual score
        parts = actual_score.split("-")
        hs, aw = int(parts[0]), int(parts[1])
        if hs > aw:
            result["winner"] = home_name
        elif aw > hs:
            result["winner"] = away_name
        else:
            result["winner"] = ""
        result["probabilities"] = {"home_win": 1, "draw": 0, "away_win": 0}
        result["home_win_prob"] = 1 if hs > aw else (0 if aw > hs else 0)
        result["away_win_prob"] = 1 if aw > hs else (0 if hs > aw else 0)
        result["penalty_winner"] = ""
    elif pred is not None:
        result["score"] = pred.get("predicted_score", "?-?")
        result["probabilities"] = {
            "home_win": round(pred["home_win_prob"], 4),
            "draw": round(pred.get("draw_prob", 0), 4),
            "away_win": round(pred["away_win_prob"], 4),
        }
        result["winner"] = pred.get("predicted_winner", "TBD")
        result["home_win_prob"] = round(pred["home_win_prob"], 4)
        result["away_win_prob"] = round(pred["away_win_prob"], 4)
        # penalty_winner only for predicted draws that go to penalties
        penalty_prob = pred.get("penalty_probability", 0)
        pred_score = result.get("score", "")
        is_draw_score = pred_score and "-" in pred_score and pred_score.split("-")[0] == pred_score.split("-")[1]
        if penalty_prob > 0 and is_draw_score and result["winner"] != "TBD":
            result["penalty_winner"] = result["winner"]
        else:
            result["penalty_winner"] = ""
    else:
        result["score"] = "?-?"
        result["probabilities"] = {"home_win": 0, "draw": 0, "away_win": 0}
        result["winner"] = "TBD"
        result["penalty_winner"] = ""

    return result



def _compute_feeds_from(home_name: str, away_name: str, stage: str = "") -> list:
    """Determine which earlier match_ids fed the home and away teams into this match.

    Checks both completed matches and predictions. Only returns matches
    from the immediately preceding round.
    """
    global matches_df, all_predictions
    if matches_df is None or matches_df.empty:
        return []

    stage_previous = {
        "Round of 16": "Round of 32",
        "Quarter-finals": "Round of 16",
        "Semi-finals": "Quarter-finals",
        "Final": "Semi-finals",
        "Third Place": "Semi-finals",
    }
    prev_stage = stage_previous.get(stage, "")

    # R32 and Group Stage have no meaningful knockout feeds
    if not prev_stage:
        return []

    feeds = []

    # Helper: check if a team is the winner of a row (completed match)
    def get_winner(row):
        hs = row.get("home_score", 0)
        as_ = row.get("away_score", 0)
        try:
            hs = int(hs) if pd.notna(hs) else 0
            as_ = int(as_) if pd.notna(as_) else 0
        except (ValueError, TypeError):
            return ""
        home = str(row.get("home_team", ""))
        away = str(row.get("away_team", ""))
        if hs > as_:
            return home
        elif as_ > hs:
            return away
        return _resolve_draw_winner(row)

    # Check completed matches
    for _, row in matches_df.iterrows():
        status = str(row.get("status", "")).lower()
        if status not in ("completed", "finished", "ft", "final"):
            continue
        row_stage = str(row.get("stage", ""))
        if prev_stage and row_stage != prev_stage:
            continue
        winner = get_winner(row)
        if not winner:
            continue
        # Match if current team is winner OR a participant (for Third Place = losers)
        chome = str(row.get("home_team", ""))
        caway = str(row.get("away_team", ""))
        if winner in (home_name, away_name) or chome in (home_name, away_name) or caway in (home_name, away_name):
            try:
                feeds.append(int(row["match_id"]))
            except (ValueError, TypeError):
                continue

    # Check predicted matches if not found enough
    if len(feeds) < 2 and all_predictions is not None and not all_predictions.empty:
        for _, prow in all_predictions.iterrows():
            row_stage = str(prow.get("stage", ""))
            if prev_stage and row_stage != prev_stage:
                continue
            predicted_winner = str(prow.get("predicted_winner", ""))
            if not predicted_winner or predicted_winner == "TBD" or predicted_winner == "draw":
                continue
            # Check if current match's team is the winner OR a participant
            phome = str(prow.get("home_team", ""))
            paway = str(prow.get("away_team", ""))
            if predicted_winner in (home_name, away_name) or phome in (home_name, away_name) or paway in (home_name, away_name):
                try:
                    feeds.append(int(prow["match_id"]))
                except (ValueError, TypeError):
                    continue
                if len(feeds) >= 2:
                    break

    return feeds[:2]  # max 2 feeder matches


def _resolve_draw_winner(match_row) -> str:
    """For knockout matches ending in draw, determine winner by who advanced to next round."""
    global matches_df
    if matches_df is None:
        return ""
    mid = match_row.get("match_id", 0)
    home = str(match_row.get("home_team", ""))
    away = str(match_row.get("away_team", ""))
    stage = str(match_row.get("stage", ""))
    try:
        mid = int(mid)
    except (ValueError, TypeError):
        return ""
    # Look at ALL subsequent matches to see which team appears
    for _, r2 in matches_df.iterrows():
        h2 = str(r2.get("home_team", ""))
        a2 = str(r2.get("away_team", ""))
        if h2 == home or h2 == away or a2 == home or a2 == away:
            if str(r2.get("match_id", "")) != str(mid):
                if h2 == home or a2 == home:
                    return home
                if h2 == away or a2 == away:
                    return away
    return ""


CN_NAME_MAP = {
    "Algeria": "阿尔及利亚",
    "Argentina": "阿根廷",
    "Australia": "澳大利亚",
    "Austria": "奥地利",
    "Belgium": "比利时",
    "Bosnia and Herzegovina": "波黑",
    "Brazil": "巴西",
    "Canada": "加拿大",
    "Cape Verde": "佛得角",
    "Colombia": "哥伦比亚",
    "Croatia": "克罗地亚",
    "Curacao": "库拉索",
    "Curaçao": "库拉索",
    "Czech Republic": "捷克",
    "Democratic Republic of the Congo": "刚果(金)",
    "Ecuador": "厄瓜多尔",
    "Egypt": "埃及",
    "England": "英格兰",
    "France": "法国",
    "Germany": "德国",
    "Ghana": "加纳",
    "Haiti": "海地",
    "Iran": "伊朗",
    "Iraq": "伊拉克",
    "Ivory Coast": "科特迪瓦",
    "Japan": "日本",
    "Jordan": "约旦",
    "Mexico": "墨西哥",
    "Morocco": "摩洛哥",
    "Netherlands": "荷兰",
    "New Zealand": "新西兰",
    "Norway": "挪威",
    "Panama": "巴拿马",
    "Paraguay": "巴拉圭",
    "Portugal": "葡萄牙",
    "Qatar": "卡塔尔",
    "Saudi Arabia": "沙特",
    "Scotland": "苏格兰",
    "Senegal": "塞内加尔",
    "South Africa": "南非",
    "South Korea": "韩国",
    "Spain": "西班牙",
    "Sweden": "瑞典",
    "Switzerland": "瑞士",
    "Tunisia": "突尼斯",
    "Turkey": "土耳其",
    "United States": "美国",
    "Uruguay": "乌拉圭",
    "Uzbekistan": "乌兹别克斯坦",
}


def _save_model_state():
    """Save calibrated model state to disk for fast cold-start."""
    global calibrated_config, market_values
    try:
        state = {
            "calibrated_config": {
                "elo_spread": calibrated_config.elo_spread,
                "draw_intercept": calibrated_config.draw_intercept,
                "attack_k": calibrated_config.attack_k,
                "defense_k": calibrated_config.defense_k,
                "feature_shots_weight": calibrated_config.feature_shots_weight,
                "feature_possession_weight": calibrated_config.feature_possession_weight,
                "feature_star_weight": calibrated_config.feature_star_weight,
                "feature_stamina_weight": calibrated_config.feature_stamina_weight,
                "feature_tactical_weight": calibrated_config.feature_tactical_weight,
                "feature_cohesion_weight": calibrated_config.feature_cohesion_weight,
                "market_value_weight": calibrated_config.market_value_weight,
            },
            "market_values": market_values,
            "elo_k": calibrated_config.K,
            "home_adv": calibrated_config.home_advantage,
        }
        with open(MODEL_CACHE, "wb") as f:
            pickle.dump(state, f)
        print(f"    Model state saved to {MODEL_CACHE}")
    except Exception as e:
        print(f"    [WARN] Failed to save model state: {e}")


def _load_model_state() -> bool:
    """Try to load saved model state. Returns True if successful."""
    global calibrated_config, market_values
    if not os.path.exists(MODEL_CACHE):
        return False
    try:
        with open(MODEL_CACHE, "rb") as f:
            state = pickle.load(f)
        cfg = state["calibrated_config"]
        calibrated_config = EloConfig(
            K=state.get("elo_k", 30),
            home_advantage=state.get("home_adv", 0),
            elo_spread=cfg["elo_spread"],
            draw_intercept=cfg["draw_intercept"],
            attack_k=cfg["attack_k"],
            defense_k=cfg["defense_k"],
            feature_shots_weight=cfg["feature_shots_weight"],
            feature_possession_weight=cfg["feature_possession_weight"],
            feature_star_weight=cfg["feature_star_weight"],
            feature_stamina_weight=cfg["feature_stamina_weight"],
            feature_tactical_weight=cfg["feature_tactical_weight"],
            feature_cohesion_weight=cfg["feature_cohesion_weight"],
            market_value_weight=cfg["market_value_weight"],
        )
        market_values = state["market_values"]
        print(f"    Loaded saved model state from {MODEL_CACHE}")
        return True
    except Exception as e:
        print(f"    [WARN] Failed to load model state: {e}")
        return False


def _build_group_standings() -> List[Dict]:
    """Build group standings directly from matches_df (no external API needed)."""
    global matches_df
    if matches_df is None or matches_df.empty:
        return []

    # Find completed group stage matches
    completed = matches_df[
        matches_df["status"].str.lower().isin(["completed","finished","ft","final"])
    ].copy()
    if completed.empty:
        return []

    group_matches = completed[completed["stage"] == "Group Stage"].copy()
    if group_matches.empty:
        # Fallback: try with any match that has a group
        group_matches = completed[completed["group"].notna() & (completed["group"] != "")].copy()
    if group_matches.empty:
        return []

    # Compute standings per team
    from collections import defaultdict
    teams_data = {}
    for _, row in group_matches.iterrows():
        grp = str(row.get("group", ""))
        home = str(row.get("home_team", ""))
        away = str(row.get("away_team", ""))
        hs = row.get("home_score", 0)
        as_ = row.get("away_score", 0)
        try:
            hs = int(hs) if pd.notna(hs) else 0
            as_ = int(as_) if pd.notna(as_) else 0
        except (ValueError, TypeError):
            continue

        for team, gf, ga in [(home, hs, as_), (away, as_, hs)]:
            if not team or team == "TBD":
                continue
            key = (grp, team)
            if key not in teams_data:
                teams_data[key] = {"group": grp, "team": team,
                                   "mp": 0, "w": 0, "d": 0, "l": 0,
                                   "gf": 0, "ga": 0}
            teams_data[key]["mp"] += 1
            teams_data[key]["gf"] += gf
            teams_data[key]["ga"] += ga
            if gf > ga:
                teams_data[key]["w"] += 1
            elif gf < ga:
                teams_data[key]["l"] += 1
            else:
                teams_data[key]["d"] += 1

    # Build ranked groups
    from itertools import groupby
    sorted_all = sorted(teams_data.values(),
                        key=lambda x: (x["group"], -(x["w"]*3+x["d"]), -(x["gf"]-x["ga"]), -x["gf"]))

    groups = []
    for grp_name, grp_iter in groupby(sorted_all, key=lambda x: x["group"]):
        team_list = list(grp_iter)
        entries = []
        for rank, td in enumerate(team_list, 1):
            gd = td["gf"] - td["ga"]
            pts = td["w"]*3 + td["d"]
            entries.append({
                "name": td["team"],
                "name_cn": CN_NAME_MAP.get(td["team"], td["team"]),
                "flag": FLAG_MAP.get(td["team"], "\U0001F3F3"),
                "rank": rank,
                "points": pts,
                "mp": td["mp"],
                "wins": td["w"],
                "draws": td["d"],
                "losses": td["l"],
                "goals_for": td["gf"],
                "goals_against": td["ga"],
                "goal_diff": gd,
                "qualified": rank <= 2,
            })
        groups.append({"name": grp_name, "teams": entries})
    return groups


def _build_tree(selected_date: Optional[str] = None) -> Dict:
    """
    Build the complete tournament bracket tree from all match stages.
    For date view: shows all matches on that date across all stages.
    For panorama: shows full bracket from current stage through final.
    Includes:
      - Group Stage (all dates, completed)
      - Round of 32 (completed)
      - Round of 16 (completed)
      - Quarter-finals (completed + predicted)
      - Semi-finals (predicted)
      - Third Place / Final (predicted)
    """
    global matches_df, all_predictions, calibrated_config, market_values, _date_prediction_cache

    if all_predictions is None or all_predictions.empty:
        return {"date": selected_date or "all", "groups": [], "rounds": []}

    # 1) Build group standings
    groups = _build_group_standings()

    # 2) Identify today's matches (all matches on selected_date)
    today_mids = set()
    if selected_date and matches_df is not None:
        for _, row in matches_df.iterrows():
            if _match_date(row) == selected_date:
                try:
                    today_mids.add(int(row["match_id"]))
                except (ValueError, TypeError):
                    pass

    # 3) Build bracket rounds from completed + predicted knockout matches
    # Use date-specific predictions if a date is selected
    if selected_date is not None:
        cache_key = f"date_{selected_date}"
        if cache_key not in _date_prediction_cache:
            try:
                filtered = _filter_matches_by_date(selected_date)
                date_pred = TournamentPredictor(calibrated_config, market_values=market_values)
                date_pred.train(filtered)
                _date_prediction_cache[cache_key] = date_pred.predict_all()
                print(f"  [DATE] Generated {len(_date_prediction_cache[cache_key])} predictions for {selected_date}")
            except Exception as e:
                print(f"  [DATE] Failed for {selected_date}: {e}")
                _date_prediction_cache[cache_key] = all_predictions.copy()
        preds = _date_prediction_cache[cache_key].sort_values("match_id")
    else:
        preds = all_predictions.sort_values("match_id") if all_predictions is not None else pd.DataFrame()

    # Standard stage ordering for display
    stage_order = [
        "Round of 16",
        "Quarter-finals", "Semi-finals", "Third Place", "Final",
    ]
    # Alternate names that may appear in the data
    stage_aliases = {
        "r16": "Round of 16",
        "round_of_16": "Round of 16",
        "round 16": "Round of 16",
        "qf": "Quarter-finals",
        "quarterfinal": "Quarter-finals",
        "quarter-final": "Quarter-finals",
        "sf": "Semi-finals",
        "semifinal": "Semi-finals",
        "semi-final": "Semi-finals",
        "third": "Third Place",
        "third place match": "Third Place",
        "3rd": "Third Place",
        "3rd place": "Third Place",
        "final": "Final",
        "championship": "Final",
        "group stage": "Group Stage",
        "groups": "Group Stage",
        "group": "Group Stage",
        "round_of_32": "Round of 32",
        "round 32": "Round of 32",
        "r32": "Round of 32",
    }

    def normalize_stage(s: str) -> str:
        s_lower = s.strip().lower()
        if s_lower in stage_aliases:
            return stage_aliases[s_lower]
        # Try direct match
        if s in stage_order:
            return s
        # Try case-insensitive
        for std in stage_order:
            if s_lower == std.lower():
                return std
        return s

    # Collect completed matches for all stages (not just KO)
    completed_all = pd.DataFrame()
    if matches_df is not None and not matches_df.empty:
        # Filter for completed matches
        ALL_STAGES = ["Group Stage", "Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "Third Place", "Final"]
        ALL_LOWER = [s.lower() for s in ALL_STAGES]
        completed_mask = matches_df["status"].str.lower().isin(["completed","finished","ft","final"])
        
        # Match by standard stage names or aliases
        all_stages = matches_df["stage"].dropna().unique()
        matched_ko = []
        for s in all_stages:
            s_lower = str(s).strip().lower()
            if s_lower in ALL_LOWER or s_lower in stage_aliases:
                norm = normalize_stage(s)
                if norm in ALL_STAGES:
                    matched_ko.append(s)
        
        if matched_ko:
            completed_all = matches_df[completed_mask & matches_df["stage"].isin(matched_ko)].copy()
            # Normalize stage names
            completed_all["stage"] = completed_all["stage"].apply(normalize_stage)
        else:
            # Fallback: include all completed matches
            completed_all = matches_df[completed_mask].copy()
            if not completed_all.empty:
                completed_all["stage"] = completed_all["stage"].apply(normalize_stage)

    # For date-specific views, filter out completed matches on/after selected_date
    # (these should come from predictions instead)
    if selected_date is not None and not completed_all.empty:
        ko_dates = completed_all.apply(_match_date, axis=1)
        completed_all = completed_all[(ko_dates < selected_date) | (ko_dates == "")]

    # Print debug info about stages available
    if matches_df is not None:
        completed = matches_df[
            matches_df["status"].str.lower().isin(["completed","finished","ft","final"])
        ]
        if not completed.empty:
            ko_completed = completed[
                ~completed["stage"].str.lower().isin(["group stage","group","groups"])
            ]
            print(f"    [DEBUG] Completed matches: {len(completed)} total, {len(ko_completed)} KO")
            if not ko_completed.empty:
                print(f"    [DEBUG] KO stages: {ko_completed['stage'].unique()}")

    # For date views: stages that have completed or predicted-past matches BEFORE the date.
    # Today's matches go in "Today" section; future matches are hidden.
    stage_order_all = ["Group Stage", "Round of 32"] + stage_order
    _order = stage_order_all if selected_date is not None else stage_order
    
    if selected_date is not None:
        reached_stages = set()
        if not completed_all.empty:
            reached_stages.update(completed_all["stage"].unique())
        # Also include stages where predicted matches have dates < selected_date
        if not preds.empty and matches_df is not None:
            for stg in preds["stage"].unique():
                if stg not in _order or stg in reached_stages:
                    continue
                sp = preds[preds["stage"] == stg]
                for _, p in sp.iterrows():
                    try:
                        mid = int(p["match_id"])
                    except:
                        continue
                    mr = matches_df[matches_df["match_id"].astype(str) == str(mid)]
                    if not mr.empty:
                        dt = _match_date(mr.iloc[0])
                        if dt and dt != "" and dt < selected_date:
                            reached_stages.add(stg)
                            break
        active_stages = [s for s in _order if s in reached_stages and s != "Group Stage"]
    else:
        active_stages = _order

    rounds = []
    
    # Date view: add today matches section at the start
    # EVERY match on the selected date uses the model prediction
    # (trained on data BEFORE selected_date, predicting the current day)
    if selected_date is not None and matches_df is not None:
        today_mask = matches_df.apply(lambda r: _match_date(r) == selected_date, axis=1)
        today_rows = matches_df[today_mask]
        if not today_rows.empty:
            today_items = []
            for _, row in today_rows.iterrows():
                try:
                    mid = int(row["match_id"])
                except (ValueError, TypeError):
                    continue
                home = str(row.get("home_team", "TBD"))
                away = str(row.get("away_team", "TBD"))
                dt = str(row.get("datetime", ""))
                stag = str(row.get("stage", ""))
                
                # Always try to get the model's prediction for today's match
                pr = None
                if not preds.empty:
                    pm = preds[preds["match_id"].astype(str) == str(mid)]
                    if not pm.empty:
                        pr = pm.iloc[0]

                # Use actual score from data (takes priority over prediction)
                row_hs = str(row.get("home_score", ""))
                row_as = str(row.get("away_score", ""))
                actual_score = None
                if row_hs and row_as and row_hs.isdigit() and row_as.isdigit():
                    actual_score = f"{int(row_hs)}-{int(row_as)}"

                # Use resolved team names from prediction (handles Winner/Loser Match placeholders)
                today_home = str(pr["home_team"]) if pr is not None else home
                today_away = str(pr["away_team"]) if pr is not None else away

                today_items.append(_build_match_response(
                    match_id=mid, stage=stag, datetime_str=dt,
                    home_name=today_home, away_name=today_away,
                    pred=pr.to_dict() if pr is not None else None,
                    is_today=True, is_future=pr is None,
                    actual_score=actual_score,
                ))
            if today_items:
                rounds.append({"name": f"Today ({selected_date[5:]})", "today": True, "matches": today_items})
    
    # Bracket progression stages
    for stage in active_stages:
        stage_matches = []

        # a) Completed matches for this stage
        if not completed_all.empty:
            stage_completed = completed_all[completed_all["stage"] == stage]
            for _, row in stage_completed.iterrows():
                try:
                    mid = int(row["match_id"])
                except (ValueError, TypeError):
                    continue

                # Safety: skip completed matches on/after selected_date
                if selected_date is not None:
                    mdt = _match_date(row)
                    if mdt and mdt != "" and mdt >= selected_date:  # will be in Today section
                        continue

                home_name = str(row.get("home_team", "TBD"))
                away_name = str(row.get("away_team", "TBD"))
                dt_str = str(row.get("datetime", ""))

                hs = row.get("home_score", 0)
                as_ = row.get("away_score", 0)
                score_str = f"{int(hs)}-{int(as_)}" if pd.notna(hs) and pd.notna(as_) else "?-?"

                winner = _resolve_draw_winner(row) if stage != "Group Stage" and str(row.get("home_score","")) == str(row.get("away_score","")) else ""
                try:
                    if int(hs) > int(as_):
                        winner = home_name
                    elif int(as_) > int(hs):
                        winner = away_name
                except (ValueError, TypeError):
                    pass

                stage_matches.append({
                    "match_id": mid,
                    "stage": stage,
                    "datetime": dt_str,
                    "home": {
                        "name": home_name,
                        "name_cn": CN_NAME_MAP.get(home_name, home_name),
                        "flag": FLAG_MAP.get(home_name, "\U0001F3F3"),
                        "features": _get_team_features(home_name),
                    },
                    "away": {
                        "name": away_name,
                        "name_cn": CN_NAME_MAP.get(away_name, away_name),
                        "flag": FLAG_MAP.get(away_name, "\U0001F3F3"),
                        "features": _get_team_features(away_name),
                    },
                    "is_today": False,
                    "is_future": False,
                    "score": score_str,
                    "probabilities": {"home_win": 1, "draw": 0, "away_win": 0},
                    "winner": winner,
                    "penalty_winner": winner if winner and stage != "Group Stage" and str(row.get("home_score","")) == str(row.get("away_score","")) else "",
                    "home_win_prob": 1,
                    "away_win_prob": 0,
                    "feeds_from": _compute_feeds_from(home_name, away_name, stage),
                })

        # b) Predicted matches for this stage
        # Panorama: include ALL predictions
        # Date view: ONLY include predictions for today's matches (on selected_date)
        if not preds.empty:
            stage_preds = preds[preds["stage"] == stage]
            for _, p in stage_preds.iterrows():
                try:
                    mid = int(p["match_id"])
                except (ValueError, TypeError):
                    continue

                # Date view: skip ALL predicted matches except today's
                if selected_date is not None and matches_df is not None:
                    m_row = matches_df[matches_df["match_id"].astype(str) == str(mid)]
                    if not m_row.empty:
                        dt = _match_date(m_row.iloc[0])
                        if not dt or dt == "" or dt != selected_date:
                            continue
                    else:
                        continue

                # Skip this match if already shown in Today section
                if mid in today_mids:
                    continue

                # Skip this match if it was already added as completed
                if any(m["match_id"] == mid for m in stage_matches):
                    continue

                is_today = mid in today_mids
                is_future = not is_today

                home = str(p.get("home_team", "TBD"))
                away = str(p.get("away_team", "TBD"))

                if "Winner Match" in home or "Loser Match" in home or home == "TBD":
                    home = "TBD"
                if "Winner Match" in away or "Loser Match" in away or away == "TBD":
                    away = "TBD"

                dt_str = ""
                if matches_df is not None:
                    m_row = matches_df[matches_df["match_id"].astype(str) == str(mid)]
                    if not m_row.empty:
                        dt_str = str(m_row.iloc[0].get("datetime", ""))

                match_resp = _build_match_response(
                    match_id=mid,
                    stage=stage,
                    datetime_str=dt_str,
                    home_name=home,
                    away_name=away,
                    pred=p.to_dict(),
                    is_today=is_today,
                    is_future=is_future,
                )
                stage_matches.append(match_resp)

        if stage_matches:
            rounds.append({
                "name": stage,
                "today": any(m["is_today"] for m in stage_matches),
                "matches": stage_matches,
            })

    has_today = any(r["today"] for r in rounds)

    return {
        "date": selected_date or "all",
        "has_today": has_today,
        "groups": groups,
        "rounds": rounds,
        "accuracy": calibrated_accuracy,
        "accuracy_correct": calibrated_correct,
        "accuracy_total": calibrated_total,
    }


def _run_simulation(edits: List[TeamEdit], selected_date: Optional[str] = None) -> pd.DataFrame:
    """Run a simulation with modified bracket teams.
    
    If selected_date is provided, only matches completed BEFORE that
    date are used for training — simulating knowledge state at that date.
    """
    global matches_df, calibrated_config, market_values

    if calibrated_config is None:
        raise HTTPException(status_code=503, detail="Model not initialized")

    # Clone match data
    sim_matches = matches_df.copy()

    # Apply edits
    for edit in edits:
        mask = sim_matches["match_id"].astype(str) == str(edit.match_id)
        if not mask.any():
            continue
        sim_matches.loc[mask, "home_team"] = edit.home
        sim_matches.loc[mask, "away_team"] = edit.away

    # Filter by date: simulate knowledge state at selected_date
    if selected_date is not None:
        dates = sim_matches.apply(_match_date, axis=1)
        historical = (
            sim_matches["status"].str.lower().isin(["completed", "finished", "ft", "final"]) &
            (dates < selected_date) & (dates != "")
        )
        sim_matches.loc[~historical, "status"] = "scheduled"

    # Create fresh predictor with same calibrated config
    sim_predictor = TournamentPredictor(calibrated_config, market_values=market_values)
    sim_predictor.train(sim_matches)

    # Apply injury effects: reduce Elo rating of injured teams
    if sim_predictor.predictor and sim_predictor.predictor.elo:
        for edit in edits:
            home_injury = getattr(edit, 'injury_home', 0) or 0
            away_injury = getattr(edit, 'injury_away', 0) or 0
            if home_injury > 0 and edit.home in sim_predictor.predictor.elo.ratings:
                reduction = sim_predictor.predictor.elo.ratings[edit.home] * (home_injury / 100)
                sim_predictor.predictor.elo.ratings[edit.home] -= reduction
                print(f"    [INJURY] {edit.home} Elo reduced by {home_injury}% ({reduction:.0f} pts)")
            if away_injury > 0 and edit.away in sim_predictor.predictor.elo.ratings:
                reduction = sim_predictor.predictor.elo.ratings[edit.away] * (away_injury / 100)
                sim_predictor.predictor.elo.ratings[edit.away] -= reduction
                print(f"    [INJURY] {edit.away} Elo reduced by {away_injury}% ({reduction:.0f} pts)")

    # Get predictions
    sim_preds = sim_predictor.predict_all()
    return sim_preds


# ============================================================
#  BETTING ODDS CALIBRATION
# ============================================================

ODDS_ALPHA = 0.7  # Higher = more weight on Elo, lower = more weight on odds


def _load_betting_odds() -> Optional[pd.DataFrame]:
    """Load bet365 odds from the World Cup 2026 XLSX."""
    xlsx_path = os.path.join(os.path.dirname(__file__), "..", "FIFA-MODEL", "data", "historical", "wc2026_odds.csv")
    if not os.path.exists(xlsx_path):
        return None
    try:
        odds = pd.read_csv(xlsx_path)
        odds["date_str"] = pd.to_datetime(odds["Date"]).dt.strftime("%Y-%m-%d")
        print(f"    [ODDS] Loaded {len(odds)} matches with betting odds")
        return odds
    except Exception as e:
        print(f"    [WARN] Failed to load odds: {e}")
        return None


def _calibrate_with_odds(pred_df: pd.DataFrame, odds_df: Optional[pd.DataFrame], matches_df: pd.DataFrame) -> pd.DataFrame:
    """Blend model predictions with betting odds for remaining matches."""
    if odds_df is None or odds_df.empty:
        return pred_df

    calibrated = pred_df.copy()
    n_calibrated = 0

    for idx, row in calibrated.iterrows():
        mid = row["match_id"]
        mrow = matches_df[matches_df["match_id"].astype(str) == str(mid)]
        if mrow.empty:
            continue

        dt = str(mrow.iloc[0].get("datetime", ""))[:10]
        home = row["home_team"]
        away = row["away_team"]

        # Find matching odds
        odd_row = odds_df[(odds_df["date_str"] == dt) &
                          (odds_df["Home"].str.strip() == home) &
                          (odds_df["Away"].str.strip() == away)]
        if odd_row.empty:
            # Try reversed
            odd_row = odds_df[(odds_df["date_str"] == dt) &
                              (odds_df["Home"].str.strip() == away) &
                              (odds_df["Away"].str.strip() == home)]
        if odd_row.empty:
            continue

        o = odd_row.iloc[0]
        # bet365 odds → implied probabilities (remove margin)
        b365h = float(o.get("bet365-H", 0))
        b365d = float(o.get("bet365-D", 0))
        b365a = float(o.get("bet365-A", 0))
        if not (b365h and b365d and b365a):
            continue

        imp_h = 1.0 / b365h
        imp_d = 1.0 / b365d
        imp_a = 1.0 / b365a
        total_imp = imp_h + imp_d + imp_a
        imp_h /= total_imp
        imp_d /= total_imp
        imp_a /= total_imp

        # Blend with Elo probabilities
        elo_h = float(row.get("home_win_prob", 0.33))
        elo_d = float(row.get("draw_prob", 0.33))
        elo_a = float(row.get("away_win_prob", 0.33))

        blended_h = ODDS_ALPHA * elo_h + (1 - ODDS_ALPHA) * imp_h
        blended_d = ODDS_ALPHA * elo_d + (1 - ODDS_ALPHA) * imp_d
        blended_a = ODDS_ALPHA * elo_a + (1 - ODDS_ALPHA) * imp_a

        calibrated.at[idx, "home_win_prob"] = round(blended_h, 4)
        calibrated.at[idx, "draw_prob"] = round(blended_d, 4)
        calibrated.at[idx, "away_win_prob"] = round(blended_a, 4)

        # Recompute winner
        if blended_h > blended_d and blended_h > blended_a:
            calibrated.at[idx, "predicted_winner"] = row["home_team"]
        elif blended_a > blended_h and blended_a > blended_d:
            calibrated.at[idx, "predicted_winner"] = row["away_team"]
        else:
            calibrated.at[idx, "predicted_winner"] = "draw"

        n_calibrated += 1

    if n_calibrated:
        print(f"    [ODDS] Calibrated {n_calibrated} match predictions with bet365 odds (α={ODDS_ALPHA})")
    return calibrated


# ============================================================
#  MATCH RESULT PATCH (correct known API mismatches)
# ============================================================

def _patch_match_results(matches_df: pd.DataFrame) -> pd.DataFrame:
    """Apply manual corrections to match results when the API data is stale.

    Add entries here when a match completes but the API hasn't been updated.
    """
    patches = [
        # Semi-final 2026-07-14: France vs Spain -> Spain won 2-0
        {"match_id": 101, "home_score": 0, "away_score": 2},
    ]
    for p in patches:
        mask = matches_df["match_id"].astype(str) == str(p["match_id"])
        if mask.any():
            idx = matches_df[mask].index[0]
            old_h = int(matches_df.at[idx, "home_score"])
            old_a = int(matches_df.at[idx, "away_score"])
            matches_df.at[idx, "home_score"] = p["home_score"]
            matches_df.at[idx, "away_score"] = p["away_score"]
            print(f"    [PATCH] Match {p['match_id']}: {old_h}-{old_a} -> {p['home_score']}-{p['away_score']}")
        else:
            print(f"    [PATCH] Match {p['match_id']} not found, skipping")
    return matches_df


# ============================================================
#  HISTORICAL DATA LOADING
# ============================================================

HISTORICAL_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "historical", "worldcup_matches_full.csv")
ODDS_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "historical", "wc2026_odds.csv")

HISTORICAL_TEAM_NAMES = {
    "United States": "USA",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "Democratic Republic of the Congo": "D.R. Congo",
}


def _merge_historical_data(matches_df: pd.DataFrame) -> pd.DataFrame:
    """Load historical World Cup matches and merge into training data.

    This adds 964 matches from 1930-2022 to the 2026 data, giving the Elo
    model much richer historical context for each team's rating.
    All historical matches are marked as 'completed' for training.
    """
    global team_stats_df

    if not os.path.exists(HISTORICAL_DATA_PATH):
        print(f"    [WARN] Historical data not found at {HISTORICAL_DATA_PATH}")
        return matches_df

    try:
        hist = pd.read_csv(HISTORICAL_DATA_PATH, parse_dates=["date"])
        hist = hist.sort_values("date").reset_index(drop=True)

        # Create match_id (negative to avoid collision with 2026 positive ids)
        hist["match_id"] = range(-1, -len(hist) - 1, -1)
        hist["status"] = "completed"
        hist["group"] = ""
        hist["datetime"] = hist["date"].astype(str)
        # Map stage names to our format
        stage_map = {
            "group stage": "Group Stage", "final round": "Group Stage",
            "second group stage": "Group Stage",
            "round of 16": "Round of 16",
            "quarter-finals": "Quarter-finals", "quarter-final": "Quarter-finals",
            "semi-finals": "Semi-finals", "semi-final": "Semi-finals",
            "final": "Final", "third-place match": "Third Place",
        }
        hist["stage"] = hist["stage"].str.lower().map(stage_map).fillna(hist["stage"])

        # Normalize team names
        hist["home_team"] = hist["home_team"].map(lambda x: HISTORICAL_TEAM_NAMES.get(x, x))
        hist["away_team"] = hist["away_team"].map(lambda x: HISTORICAL_TEAM_NAMES.get(x, x))

        # Ensure match_id is string to avoid type mismatches with 2026 data
        hist["match_id"] = hist["match_id"].astype(str)

        # Keep only columns that match matches_df
        common_cols = [c for c in ["match_id", "group", "stage", "home_team", "away_team",
                                    "home_score", "away_score", "status", "datetime"]
                       if c in matches_df.columns]

        hist_out = hist[common_cols].copy()

        # Log stats
        teams_in_hist = set(hist_out["home_team"].unique()) | set(hist_out["away_team"].unique())
        print(f"\n    [HISTORY] Loaded {len(hist_out)} matches ({hist['date'].min().year}-{hist['date'].max().year})")
        print(f"    [HISTORY] Teams: {len(teams_in_hist)}, overlapping with 2026: {len(teams_in_hist & set(matches_df['home_team'].unique()))}")

        # Ensure all match_ids are strings to avoid type mismatch in sorting
        if "match_id" in matches_df.columns:
            matches_df["match_id"] = matches_df["match_id"].astype(str)
        if "match_id" in hist_out.columns:
            hist_out["match_id"] = hist_out["match_id"].astype(str)

        # Merge: historical first (older), then 2026 data
        merged = pd.concat([hist_out, matches_df], ignore_index=True)
        merged = merged.drop_duplicates(subset=["home_team", "away_team", "datetime"], keep="last")
        print(f"    [HISTORY] Merged: {len(merged)} total matches ({len(matches_df)} original + {len(hist_out)} historical)")

        return merged

    except Exception as e:
        print(f"    [WARN] Failed to load historical data: {e}")
        import traceback
        traceback.print_exc()
        return matches_df


# ============================================================
#  DATA SNAPSHOT (for migration / API-free deployment)
# ============================================================

SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "snapshot.pkl")


def _save_snapshot(data: dict):
    """Save full data snapshot (matches, team_stats, cards, players) for migration."""
    try:
        os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
        save_data = {k: v for k, v in data.items() if isinstance(v, (pd.DataFrame, dict, list))}
        # Convert DataFrames to dicts for pickle compatibility
        for k, v in save_data.items():
            if isinstance(v, pd.DataFrame):
                save_data[k] = v.to_dict(orient="records")
        with open(SNAPSHOT_PATH, "wb") as f:
            pickle.dump(save_data, f)
        print(f"    [SNAPSHOT] Saved full data snapshot to {SNAPSHOT_PATH}")
    except Exception as e:
        print(f"    [WARN] Failed to save snapshot: {e}")


def _load_snapshot() -> Optional[dict]:
    """Load snapshot if API is unavailable."""
    if not os.path.exists(SNAPSHOT_PATH):
        return None
    try:
        with open(SNAPSHOT_PATH, "rb") as f:
            raw = pickle.load(f)
        # Convert back to DataFrames
        for k in ["matches", "team_stats", "cards", "players"]:
            if k in raw and isinstance(raw[k], list):
                raw[k] = pd.DataFrame(raw[k])
        print(f"    [SNAPSHOT] Loaded data snapshot ({list(raw.keys())})")
        return raw
    except Exception as e:
        print(f"    [WARN] Failed to load snapshot: {e}")
        return None


# ============================================================
#  STARTUP EVENT
# ============================================================

@app.on_event("startup")
def startup():
    """Initialize the model once at server startup."""
    global predictor, matches_df, team_stats_df, skill
    global calibrated_config, market_values, all_predictions

    print("=" * 60)
    print("  WORLD CUP 2026 - PREDICTION API STARTUP")
    print("=" * 60)

    # 1. Try loading cached model state first
    if _load_model_state():
        # Apply Bayesian-optimized parameters BEFORE training
        calibrated_config.K = 7.9
        calibrated_config.home_advantage = 7.0
        calibrated_config.elo_spread = 0.008
        calibrated_config.draw_intercept = 0.956

        print("\n[1] Loading data (fast path)...")
        skill = WorldCupDataSkill()
        try:
            data = skill.collect_all()
            matches_df = data["matches"]
            team_stats_df = data["team_stats"]
        except Exception as e:
            print(f"    [WARN] API unavailable ({e}), trying snapshot...")
            snapshot_data = _load_snapshot()
            if snapshot_data is None:
                raise
            matches_df = snapshot_data.get('matches', pd.DataFrame())
            team_stats_df = snapshot_data.get('team_stats', pd.DataFrame())

        # Patch known incorrect API results
        matches_df = _patch_match_results(matches_df)
        if 'data' in dir():
            _save_snapshot(data)

        # Save original 2026 data for bracket display; use merged data for training
        matches_df_2026 = matches_df.copy()
        training_df = _merge_historical_data(matches_df)

        print("\n[2] Training (fast path) with historical data...")
        predictor = TournamentPredictor(calibrated_config, market_values=market_values)
        predictor.train(training_df)

        print("\n[3] Generating predictions (on 2026 data only)...")
        # Restore original 2026 matches for bracket display
        matches_df = matches_df_2026
        all_predictions = predictor.predict_all()
        if not all_predictions.empty:
            print(f"    {len(all_predictions)} matches predicted")
        odds_df = _load_betting_odds()
        if odds_df is not None:
            all_predictions = _calibrate_with_odds(all_predictions, odds_df, matches_df)

        print(f"\n[4] Model ready from cache:")
        print(f"    ak={calibrated_config.attack_k:.1f}, dk={calibrated_config.defense_k:.1f}")
        print(f"    shots_w={calibrated_config.feature_shots_weight:.2f}, poss_w={calibrated_config.feature_possession_weight:.2f}")
        print(f"    star_w={calibrated_config.feature_star_weight:.2f}, stam_w={calibrated_config.feature_stamina_weight:.2f}")
        print(f"    tact_w={calibrated_config.feature_tactical_weight:.2f}, coh_w={calibrated_config.feature_cohesion_weight:.2f}")
        print(f"    mv_w={calibrated_config.market_value_weight:.2f}")
        print("=" * 60)
        return

    # 2. Full training path (first run)
    print("\n[1] Collecting data...")
    skill = WorldCupDataSkill()
    try:
        data = skill.collect_all()
        matches_df = data["matches"]
        team_stats_df = data["team_stats"]
        market_values = skill.fetch_market_values()
    except Exception as e:
        print(f"    [WARN] API unavailable ({e}), trying snapshot...")
        matches_df = _load_snapshot()
        if matches_df is None:
            raise
        team_stats_df = skill._compute_team_stats(matches_df)
        market_values = {}
    matches_df = _patch_match_results(matches_df)
    matches_df_2026 = matches_df.copy()
    # Save snapshot for future migration
    if 'data' in dir():
        _save_snapshot(data)

    # Merge historical data for training only
    training_df = _merge_historical_data(matches_df)

    print(f"    Completed matches: "
          f"{len(matches_df[matches_df['status']=='completed'])}")
    print(f"    Scheduled matches: "
          f"{len(matches_df[matches_df['status']=='scheduled'])}")

    # Skip hyperparameter search with historical data (too slow: 112×calibration)
    # Use Bayesian-optimized defaults from FIFA-MODEL directly
    print("\n[2] Using Bayesian-optimized config (skip slow hyperparameter search)...")
    best_config = EloConfig(
        K=7.9, home_advantage=7.0,
        elo_spread=0.008, draw_intercept=0.956,
        avg_total_goals=2.908,
    )

    # 3. Train and calibrate
    print("\n[3] Training & calibrating final model...")
    elo_mod._DC_CALIBRATED_FLAG = False

    predictor = TournamentPredictor(best_config, market_values=market_values)
    predictor.train(training_df)

    # Run evaluation to calibrate softmax + DC parameters
    calibrator = WorldCupPredictor(best_config, market_values=market_values)
    calibrator.train_elo(training_df)
    elo_mod._DC_CALIBRATED_FLAG = False
    calibrator.evaluate(training_df)

    # Restore 2026 data for bracket display
    matches_df = matches_df_2026

    # Re-train with calibrated config
    calibrated_config = calibrator.config
    # Ensure Bayesian-optimized params survive calibration
    calibrated_config.K = 7.9
    calibrated_config.home_advantage = 7.0
    calibrated_config.elo_spread = 0.008
    calibrated_config.draw_intercept = 0.956
    predictor = TournamentPredictor(calibrated_config, market_values=market_values)
    predictor.train(training_df)

    # 4. Generate all predictions (on 2026 data only)
    print("\n[4] Generating predictions...")
    all_predictions = predictor.predict_all()
    if not all_predictions.empty:
        print(f"    {len(all_predictions)} matches predicted")
    odds_df = _load_betting_odds()
    if odds_df is not None:
        all_predictions = _calibrate_with_odds(all_predictions, odds_df, matches_df)

    # 5. Print config summary
    print(f"\n[5] Model ready:")
    print(f"    spread={calibrated_config.elo_spread:.3f}, "
          f"draw_int={calibrated_config.draw_intercept:.2f}")
    print(f"    ak={calibrated_config.attack_k:.1f}, "
          f"dk={calibrated_config.defense_k:.1f}")
    print(f"    shots_w={calibrated_config.feature_shots_weight:.2f}, "
          f"poss_w={calibrated_config.feature_possession_weight:.2f}")
    print(f"    star_w={calibrated_config.feature_star_weight:.2f}, "
          f"stam_w={calibrated_config.feature_stamina_weight:.2f}")
    print(f"    tact_w={calibrated_config.feature_tactical_weight:.2f}, "
          f"coh_w={calibrated_config.feature_cohesion_weight:.2f}")
    print(f"    mv_w={calibrated_config.market_value_weight:.2f}")

    # 6. Save model state for future starts
    _save_model_state()
    print("=" * 60)


# ============================================================
#  ENDPOINTS
# ============================================================

@app.get("/api/debug")
def get_debug():
    """Debug endpoint: show available stages and match counts."""
    global matches_df, all_predictions
    info = {
        "matches_df_loaded": matches_df is not None and not matches_df.empty,
        "all_predictions_loaded": all_predictions is not None and not all_predictions.empty,
        "predictions_count": len(all_predictions) if all_predictions is not None else 0,
        "stages_in_data": [],
    }
    if matches_df is not None and not matches_df.empty:
        stages = matches_df["stage"].dropna().unique().tolist()
        info["stages_in_data"] = stages
        for s in stages:
            cnt = len(matches_df[matches_df["stage"] == s])
            completed_cnt = len(matches_df[
                (matches_df["stage"] == s) &
                (matches_df["status"].str.lower().isin(["completed","finished","ft","final"]))
            ])
            info["stages_in_data"].append(f"{s}: {cnt} total, {completed_cnt} completed")
        info["match_count"] = len(matches_df)
        unique_groups = matches_df["group"].dropna().unique().tolist()
        info["groups_in_data"] = [g for g in unique_groups if g]
        # Show a sample scheduled match
        scheduled = matches_df[matches_df["status"] == "scheduled"]
        if not scheduled.empty:
            info["sample_scheduled"] = [
                {"match_id": str(s["match_id"]), "home": s["home_team"],
                 "away": s["away_team"], "stage": s["stage"],
                 "datetime": s["datetime"]}
                for _, s in scheduled.head(10).iterrows()
            ]
        completed = matches_df[matches_df["status"].str.lower() == "completed"]
        if not completed.empty:
            info["sample_completed_ko"] = [
                {"match_id": str(s["match_id"]), "home": s["home_team"],
                 "away": s["away_team"], "stage": s["stage"],
                 "score": f"{s['home_score']}-{s['away_score']}"}
                for _, s in completed[~completed["stage"].str.lower().isin(["group stage","group"])].head(20).iterrows()
            ]
    return info


@app.get("/api/today")
def get_today(
    date: str = Query("2026-07-10", description="Date in YYYY-MM-DD format"),
):
    """Return day-view bracket tree + team features."""
    global all_predictions
    if all_predictions is None:
        raise HTTPException(status_code=503, detail="Model not ready yet")
    normalized = _parse_date(date)
    tree = _build_tree(selected_date=normalized)
    return tree


@app.get("/api/panorama")
def get_panorama():
    """Return full remaining bracket (panorama mode)."""
    global all_predictions
    if all_predictions is None:
        raise HTTPException(status_code=503, detail="Model not ready yet")
    tree = _build_tree(selected_date=None)
    tree["mode"] = "panorama"
    return tree


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    """
    Edit simulation: accept team replacements, re-predict, return updated tree.
    """
    global all_predictions, matches_df, _date_prediction_cache

    try:
        date_param = _parse_date(req.date) if req.date and req.mode != "panorama" else None
        sim_preds = _run_simulation(req.edits, selected_date=date_param)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

    # Save originals, swap with simulated versions
    saved_preds = all_predictions
    saved_matches = matches_df
    all_predictions = sim_preds

    # Also modify matches_df so _build_tree reads new team names
    if matches_df is not None:
        sim_matches = matches_df.copy()
        for edit in req.edits:
            mask = sim_matches["match_id"].astype(str) == str(edit.match_id)
            if mask.any():
                sim_matches.loc[mask, "home_team"] = edit.home
                sim_matches.loc[mask, "away_team"] = edit.away
        matches_df = sim_matches

    # Clear date cache so _build_tree uses the new predictions + modified matches
    _date_prediction_cache.clear()

    try:
        if req.mode == "panorama":
            result = _build_tree(selected_date=None)
            result["mode"] = "panorama"
        else:
            date_str = req.date or "2026-07-10"
            result = _build_tree(selected_date=_parse_date(date_str))

        # Add comparison data
        if saved_preds is not None and not saved_preds.empty and not sim_preds.empty:
            changes = _compute_changes(saved_preds, sim_preds)
            result["changes"] = changes

        return result
    finally:
        # Restore original predictions and matches
        all_predictions = saved_preds
        matches_df = saved_matches


@app.get("/api/teams")
def list_teams():
    """Return all tournament teams (for edit dropdown)."""
    global team_stats_df
    if team_stats_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded yet")

    teams = []
    for _, row in team_stats_df.sort_values("team").iterrows():
        name = row["team"]
        teams.append({
            "name": name,
            "name_cn": CN_NAME_MAP.get(name, name),
            "flag": FLAG_MAP.get(name, "\U0001F3F3"),
            "points": int(row.get("points", 0)),
            "market_value": round(market_values.get(name, 0) / 1e8, 2),
        })
    return {"teams": teams, "total": len(teams)}


@app.get("/api/schedule")
def get_schedule():
    """Return ALL tournament match dates (past + future) for date picker."""
    global matches_df
    if matches_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded yet")

    all_matches = matches_df.copy()
    schedule = []
    for _, row in all_matches.iterrows():
        dt = _match_date(row)
        if not dt:
            continue
        status = "completed" if row.get("status", "").lower() in ["completed","finished","ft","final"] else "scheduled"
        score = ""
        if status == "completed":
            hs = row.get("home_score", "")
            as_ = row.get("away_score", "")
            if pd.notna(hs) and pd.notna(as_):
                score = f"{int(hs)}-{int(as_)}"
        schedule.append({
            "date": dt,
            "match_id": int(row["match_id"]) if pd.notna(row.get("match_id")) else 0,
            "stage": row.get("stage", ""),
            "home": row.get("home_team", ""),
            "away": row.get("away_team", ""),
            "status": status,
            "score": score,
        })

    from itertools import groupby
    schedule.sort(key=lambda x: x["date"])
    by_date = []
    for dt, group in groupby(schedule, key=lambda x: x["date"]):
        matches_list = list(group)
        completed_ct = sum(1 for m in matches_list if m["status"] == "completed")
        by_date.append({
            "date": dt,
            "match_count": len(matches_list),
            "completed_count": completed_ct,
            "all_completed": completed_ct == len(matches_list),
            "matches": matches_list,
        })
    return {"schedule": by_date, "total_matches": len(schedule), "total_dates": len(by_date)}


@app.get("/api/health")
def health():
    """Server health check."""
    global calibrated_accuracy, calibrated_total, calibrated_correct
    # Lazy accuracy evaluation (once, using already-trained model)
    if calibrated_accuracy == 0.0 and calibrated_total == 0 and predictor is not None and predictor.predictor is not None and predictor.matches_df is not None:
        try:
            result = predictor.predictor.evaluate(predictor.matches_df)
            calibrated_accuracy = float(result.get("accuracy", 0.0))
            calibrated_total = int(result.get("total", 0))
            calibrated_correct = int(result.get("correct", 0))
        except Exception as e:
            print(f"    [WARN] Lazy accuracy eval failed: {e}")
    return {
        "status": "ok" if all_predictions is not None else "loading",
        "matches_trained": len(matches_df) if matches_df is not None else 0,
        "predictions_ready": len(all_predictions) if all_predictions is not None else 0,
        "accuracy": calibrated_accuracy,
        "accuracy_correct": calibrated_correct,
        "accuracy_total": calibrated_total,
    }


def _compute_changes(original: pd.DataFrame, simulated: pd.DataFrame) -> List[Dict]:
    """Compare original vs simulated predictions, return changed matches."""
    changes = []
    for _, sim_row in simulated.iterrows():
        mid = sim_row["match_id"]
        orig = original[original["match_id"] == mid]
        if orig.empty:
            continue
        orig_row = orig.iloc[0]

        diff_fields = {}
        for field in ["home_team", "away_team", "predicted_score", "predicted_winner"]:
            if str(orig_row.get(field, "")) != str(sim_row.get(field, "")):
                diff_fields[field] = {
                    "original": str(orig_row.get(field, "")),
                    "simulated": str(sim_row.get(field, "")),
                }

        if diff_fields:
            changes.append({
                "match_id": int(mid),
                "stage": str(sim_row.get("stage", "")),
                "differences": diff_fields,
            })
    return changes


# ── Serve frontend static files (Vercel bundles frontend/dist into function) ──
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dir):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
