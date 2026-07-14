"""
Advanced team statistics from Fox Sports & FotMob.
All stats are tournament totals (as of Quarter-finals).
"""
from dataclasses import dataclass
from typing import Dict, Optional
import math


def mv_star_count(market_values: Optional[Dict[str, float]] = None,
                  team: str = "",
                  threshold: float = 50_000_000) -> int:
    """Estimate star player count from market value."""
    mv = market_values.get(team, 0) if market_values else 0
    return max(0, int(mv / threshold))


@dataclass
class TeamAdvancedStats:
    """Per-team advanced statistics."""
    # Identity
    team: str
    gp: int = 0  # Games played

    # --- Offensive ---
    shots: int = 0            # S - Total shots
    shots_on_target: int = 0  # SOG - Shots on goal
    shots_off_target: int = 0  # SOFF
    blocked_shots: int = 0    # SAB
    chances_created: int = 0  # CC
    possession_pct: float = 50.0  # POSS - Avg possession %
    passes: int = 0           # P
    passing_accuracy: float = 0.80  # PA
    crosses: int = 0          # C
    corner_kicks: int = 0     # CK

    # --- Defensive ---
    interceptions: int = 0    # INT
    tackles: int = 0          # TKL
    tackles_attempted: int = 0  # TA
    fouls: int = 0            # F
    goal_kicks: int = 0       # GK

    # Derived per-game
    @property
    def shots_pg(self) -> float:
        return round(self.shots / max(self.gp, 1), 1)

    @property
    def sot_pg(self) -> float:
        return round(self.shots_on_target / max(self.gp, 1), 1)

    @property
    def possession(self) -> float:
        return self.possession_pct

    @property
    def pass_acc(self) -> float:
        return self.passing_accuracy

    @property
    def tackles_pg(self) -> float:
        return round(self.tackles / max(self.gp, 1), 1)


# Complete dataset from Fox Sports + FotMob
ALL_TEAM_STATS: Dict[str, TeamAdvancedStats] = {}

def _s(team, gp, s, sog, soff, sab, cc, poss, p, pa, c, ck,
       interceptions, tackles, ta, fouls, gk):
    """Helper to add a team."""
    ALL_TEAM_STATS[team] = TeamAdvancedStats(
        team=team, gp=gp,
        shots=s, shots_on_target=sog, shots_off_target=soff,
        blocked_shots=sab, chances_created=cc,
        possession_pct=poss, passes=p, passing_accuracy=pa,
        crosses=c, corner_kicks=ck,
        interceptions=interceptions, tackles=tackles,
        tackles_attempted=ta, fouls=fouls, goal_kicks=gk,
    )

_s("Algeria", 4, 42, 15, 13, 14, 32, 61, 2432, 0.92, 57, 14, 67, 26, 41, 48, 29)
_s("Argentina", 5, 72, 31, 24, 16, 38, 59, 3294, 0.92, 73, 23, 68, 37, 63, 73, 58)
_s("Australia", 4, 40, 14, 15, 11, 28, 43, 1546, 0.81, 78, 16, 82, 19, 39, 48, 46)
_s("Austria", 4, 31, 8, 16, 7, 17, 46, 1739, 0.87, 65, 10, 60, 26, 38, 51, 46)
_s("Belgium", 5, 106, 32, 40, 33, 65, 54, 2561, 0.88, 122, 23, 99, 36, 48, 54, 60)
_s("Bosnia and Herzegovina", 4, 38, 16, 13, 9, 23, 46, 1450, 0.84, 62, 15, 68, 25, 40, 44, 59)
_s("Brazil", 5, 70, 29, 17, 24, 50, 52, 2626, 0.91, 106, 27, 75, 43, 56, 78, 51)
_s("Canada", 5, 80, 30, 25, 26, 55, 54, 2031, 0.84, 174, 50, 125, 31, 50, 56, 70)
_s("Cape Verde", 4, 47, 13, 18, 16, 30, 37, 1429, 0.83, 58, 17, 73, 30, 36, 42, 27)
_s("Colombia", 5, 96, 32, 34, 30, 63, 59, 2617, 0.89, 93, 24, 80, 23, 37, 41, 70)
_s("Croatia", 4, 38, 19, 11, 8, 28, 49, 1833, 0.87, 79, 12, 57, 18, 33, 44, 43)
_s("Curaçao", 3, 27, 9, 13, 5, 19, 33, 846, 0.81, 28, 5, 42, 29, 34, 42, 31)
_s("Czech Republic", 3, 32, 8, 16, 8, 15, 43, 1016, 0.80, 56, 15, 51, 16, 20, 22, 36)
_s("Democratic Republic of the Congo", 4, 41, 10, 22, 9, 28, 39, 1322, 0.83, 80, 13, 85, 15, 36, 48, 44)
_s("Ecuador", 4, 51, 19, 23, 9, 39, 56, 1830, 0.88, 99, 25, 71, 25, 52, 61, 49)
_s("Egypt", 5, 65, 20, 19, 26, 45, 53, 2395, 0.88, 92, 26, 100, 34, 49, 61, 58)
_s("England", 5, 78, 37, 23, 18, 57, 59, 2383, 0.91, 130, 31, 84, 27, 45, 49, 53)
_s("France", 6, 111, 50, 37, 24, 81, 59, 3226, 0.91, 104, 41, 80, 43, 72, 84, 57)
_s("Germany", 4, 74, 28, 18, 28, 53, 64, 2526, 0.91, 121, 34, 75, 15, 44, 54, 49)
_s("Ghana", 4, 24, 5, 10, 9, 14, 36, 1302, 0.84, 53, 8, 58, 22, 45, 51, 56)
_s("Haiti", 3, 27, 9, 11, 7, 15, 41, 1013, 0.86, 47, 9, 38, 18, 28, 33, 56)
_s("Iran", 3, 36, 10, 15, 11, 22, 39, 929, 0.78, 42, 8, 49, 23, 37, 41, 35)
_s("Iraq", 3, 21, 2, 11, 8, 10, 37, 1026, 0.81, 32, 7, 46, 15, 40, 45, 27)
_s("Ivory Coast", 4, 47, 14, 19, 14, 32, 52, 1783, 0.87, 79, 26, 73, 28, 48, 53, 29)
_s("Japan", 4, 31, 13, 11, 7, 27, 47, 1611, 0.89, 70, 13, 69, 21, 40, 49, 55)
_s("Jordan", 3, 24, 9, 10, 5, 14, 31, 860, 0.78, 35, 6, 51, 26, 30, 40, 29)
_s("Mexico", 5, 73, 22, 30, 21, 50, 52, 2126, 0.88, 102, 19, 99, 26, 33, 38, 57)
_s("Morocco", 6, 66, 30, 19, 17, 43, 59, 3343, 0.90, 109, 30, 105, 39, 68, 79, 73)
_s("Netherlands", 4, 49, 23, 13, 13, 37, 53, 1884, 0.89, 86, 18, 75, 20, 28, 34, 44)
_s("New Zealand", 3, 29, 15, 6, 8, 20, 47, 1190, 0.85, 47, 10, 53, 15, 20, 26, 32)
_s("Norway", 5, 52, 25, 14, 13, 36, 53, 2410, 0.88, 70, 22, 99, 30, 42, 49, 46)
_s("Panama", 3, 28, 9, 15, 4, 18, 46, 1139, 0.84, 65, 12, 61, 14, 25, 30, 46)
_s("Paraguay", 5, 34, 11, 12, 11, 18, 30, 1268, 0.72, 53, 10, 92, 47, 86, 104, 65)
_s("Portugal", 5, 63, 20, 27, 16, 39, 58, 2774, 0.92, 105, 22, 75, 35, 44, 57, 44)
_s("Qatar", 3, 16, 6, 9, 1, 11, 32, 803, 0.80, 27, 9, 41, 14, 21, 28, 35)
_s("Saudi Arabia", 3, 16, 7, 4, 5, 9, 40, 972, 0.78, 28, 7, 58, 16, 39, 47, 29)
_s("Scotland", 3, 25, 8, 8, 9, 18, 45, 1262, 0.86, 58, 12, 49, 14, 19, 21, 42)
_s("Senegal", 4, 72, 25, 31, 16, 48, 55, 2069, 0.88, 95, 22, 82, 23, 32, 40, 35)
_s("South Africa", 4, 40, 13, 13, 14, 25, 47, 1749, 0.86, 43, 11, 50, 40, 44, 51, 38)
_s("South Korea", 3, 30, 11, 11, 8, 24, 63, 1681, 0.89, 71, 12, 70, 14, 19, 22, 25)
_s("Spain", 5, 86, 34, 33, 19, 55, 66, 3129, 0.92, 135, 39, 79, 38, 44, 49, 55)
_s("Sweden", 4, 52, 26, 18, 8, 31, 46, 1414, 0.83, 70, 18, 67, 15, 34, 38, 42)
_s("Switzerland", 5, 63, 29, 19, 15, 44, 57, 2536, 0.89, 113, 26, 97, 22, 46, 55, 70)
_s("Tunisia", 3, 18, 7, 8, 3, 11, 41, 892, 0.82, 36, 9, 59, 25, 38, 45, 27)
_s("Turkey", 3, 71, 17, 27, 27, 53, 63, 1729, 0.89, 86, 22, 85, 12, 41, 43, 32)
_s("United States", 5, 59, 19, 20, 20, 34, 57, 2435, 0.89, 102, 26, 115, 37, 45, 55, 55)
_s("Uruguay", 3, 49, 14, 18, 17, 29, 54, 1348, 0.88, 108, 26, 69, 26, 31, 40, 31)
_s("Uzbekistan", 3, 17, 6, 6, 5, 11, 36, 962, 0.78, 36, 9, 59, 21, 30, 38, 44)


def get_team_stats(team: str) -> TeamAdvancedStats:
    """Get advanced stats for a team."""
    return ALL_TEAM_STATS.get(team, TeamAdvancedStats(team=team))


def get_shots_per_game(team: str) -> float:
    """Shots per game."""
    return get_team_stats(team).shots_pg


def get_sot_per_game(team: str) -> float:
    """Shots on target per game."""
    return get_team_stats(team).sot_pg


def get_possession(team: str) -> float:
    """Average possession percentage."""
    return get_team_stats(team).possession


def get_pass_accuracy(team: str) -> float:
    """Passing accuracy (0-1)."""
    return get_team_stats(team).pass_acc


def get_tactical_profile(team: str) -> Dict:
    """
    Tactical profile classification.
    Returns dict with 'style' (possession/direct/balanced) and metrics.
    """
    stats = get_team_stats(team)
    poss = stats.possession
    
    if poss >= 60:
        style = "possession"
    elif poss <= 42:
        style = "direct"
    else:
        style = "balanced"
    
    # Defensive solidity: tackles_pg + interceptions_pg
    def_solidity = (stats.tackles / max(stats.gp, 1) +
                    stats.interceptions / max(stats.gp, 1))
    
    # Attacking intensity: shots_pg
    att_intensity = stats.shots_pg
    
    return {
        "style": style,
        "possession": poss,
        "defensive_solidity": round(def_solidity, 1),
        "attacking_intensity": round(att_intensity, 1),
        "passing_accuracy": stats.pass_acc,
    }


def get_team_stamina(team: str) -> float:
    """
    Compute stamina factor from team average age.
    Core principle: peak endurance age ≈ 25, quadratic decay.
    
    Age → Stamina mapping:
      22 → 0.93  (young, high recovery)
      25 → 1.00  (peak)
      28 → 0.93
      30 → 0.80
      33 → 0.60  (declining)
      35 → 0.50  (min)
    """
    avg_age = TEAM_AVERAGE_AGE.get(team, 27.0)
    deviation = avg_age - 25.0
    stamina = 1.0 - 0.008 * deviation ** 2
    return max(0.50, min(1.0, stamina))


def player_stamina(age: float, position: str) -> float:
    """
    Compute individual player stamina from their age and position.
    
    Formula: stamina = age_factor × position_factor
      - age_factor: quadratic decay centered at peak age 25
      - position_factor: how much distance a position typically covers
    """
    # Age factor (same quadratic decay as team-level)
    deviation = age - 25.0
    age_factor = 1.0 - 0.008 * deviation ** 2
    age_factor = max(0.50, min(1.0, age_factor))

    # Position factor
    pos_factor = POSITION_STAMINA_FACTOR.get(position, 0.85)

    return round(age_factor * pos_factor, 3)


# ─── Team average ages (from RotoWire, official 26-man squads) ───
TEAM_AVERAGE_AGE = {
    "Ecuador": 23.76, "Morocco": 24.72, "Ivory Coast": 25.12,
    "Algeria": 25.48, "Canada": 25.81, "Iraq": 25.97,
    "Spain": 26.12, "Tunisia": 26.12, "Mexico": 26.29,
    "Norway": 26.31, "United States": 26.38, "Bosnia and Herzegovina": 26.38,
    "Senegal": 26.39, "Uruguay": 26.53, "France": 26.54,
    "England": 26.58, "Netherlands": 26.64, "Turkey": 26.69,
    "South Africa": 26.81, "Sweden": 26.85, "Czech Republic": 27.03,
    "Argentina": 27.04, "Belgium": 27.04, "Haiti": 27.08,
    "Australia": 27.28, "Jordan": 27.37, "Japan": 27.44,
    "Portugal": 27.44, "Curaçao": 27.46, "Germany": 27.46,
    "Uzbekistan": 27.47, "New Zealand": 27.58, "South Korea": 27.65,
    "Switzerland": 27.73, "Paraguay": 27.80, "Croatia": 27.88,
    "Saudi Arabia": 27.90, "Austria": 28.04, "Egypt": 28.41,
    "Democratic Republic of the Congo": 28.46, "Brazil": 28.62,
    "Qatar": 28.63, "Iran": 28.73, "Scotland": 28.81,
    "Cape Verde": 29.15, "Panama": 29.22, "Colombia": 29.54,
}

# Position-to-stamina multipliers (how much distance a position typically covers)
# GK=low, CB=moderate, FB/WB/CM=high, ST/wingers=moderate-high
POSITION_STAMINA_FACTOR = {
    "GK": 0.60,   # Goalkeeper
    "CB": 0.75,   # Center-back
    "FB": 0.90,   # Full-back
    "WB": 0.92,   # Wing-back
    "DM": 0.88,   # Defensive midfielder
    "CM": 0.95,   # Central midfielder (box-to-box)
    "AM": 0.85,   # Attacking midfielder
    "W": 0.90,    # Winger
    "FW": 0.78,   # Forward / striker
    "CF": 0.80,   # Center-forward
}


def get_team_stamina_by_players(team: str, top_scorers: dict = None,
                                top_assisters: dict = None) -> float:
    """
    Enhanced stamina estimate using individual player age + position.

    For each known player on the team, computes stamina from their specific
    age and position, then averages across all known players.
    Falls back to team average age if no player data is available.
    """
    from src.data_collection.players import TOP_SCORERS, TOP_ASSISTERS

    # Gather all players belonging to this team from the global data
    known_players = []
    for source_dict in (TOP_SCORERS, TOP_ASSISTERS):
        for name, data in source_dict.items():
            if data.get("team") == team:
                known_players.append(data)

    # Also include caller-provided data (top_scorers, top_assisters) for coverage
    for extra in (top_scorers, top_assisters):
        if extra:
            for name, data in extra.items():
                if data.get("team") == team:
                    known_players.append(data)

    if known_players:
        stamina_values = []
        for data in known_players:
            age = data.get("age", 27.0)
            pos = data.get("position", "")
            stamina_values.append(player_stamina(age, pos))

        # Use max of per-player average and team age baseline as conservative blend
        base = get_team_stamina(team)
        per_player_avg = sum(stamina_values) / len(stamina_values)
        return round(max(per_player_avg, base), 3)

    return round(get_team_stamina(team), 3)


# ══════════════════════════════════════════════════════════
#  TACTICAL STYLE FUNCTIONS
# ══════════════════════════════════════════════════════════

def get_pressing_intensity(team: str) -> float:
    """Return (tackles + interceptions) / game — pressing/aggression level."""
    s = get_team_stats(team)
    return round((s.tackles + s.interceptions) / max(s.gp, 1), 1)


def get_cross_intensity(team: str) -> float:
    """Return crosses / game — how much a team relies on wing play."""
    s = get_team_stats(team)
    return round(s.crosses / max(s.gp, 1), 1)


def get_chances_created_pg(team: str) -> float:
    """Return chances created / game — creative attacking ability."""
    s = get_team_stats(team)
    return round(s.chances_created / max(s.gp, 1), 1)


def get_build_up_score(team: str) -> float:
    """
    Build-up style score: possession% × pass_accuracy.
    High ≈ short-pass/possession style (Spain ~60%×0.92=55.2)
    Low  ≈ direct/counter-attack style (Australia ~43%×0.81=34.8)
    """
    s = get_team_stats(team)
    return round(s.possession_pct * s.pass_acc, 1)


def get_tactical_matchup(home_team: str, away_team: str) -> float:
    """
    Tactical matchup advantage score (range ≈ -0.3 to +0.3).
    Positive = home team's style is favorable against away team's defense.

    Factors:
      1. Press mismatch: high-press team disrupts low-pass-accuracy opponent
      2. Cross vs interceptions: cross-heavy team struggles vs high-interception D
      3. Creative edge: high-chances team exploits low-tackle defense
    """
    h = get_team_stats(home_team)
    a = get_team_stats(away_team)
    gh, ga = max(h.gp, 1), max(a.gp, 1)

    # Pressing: if home presses harder and away passing is poor → home edge
    h_press = (h.tackles + h.interceptions) / gh
    a_press = (a.tackles + a.interceptions) / ga
    press_edge = (h_press - a_press) * (1.0 - a.pass_acc) * 0.03

    # Cross vs interception: cross-heavy less effective vs high-interception
    h_cross_pg = h.crosses / gh
    a_int_pg = a.interceptions / ga
    cross_edge = -(h_cross_pg - 12) * (a_int_pg - 12) * 0.003

    # Creative vs defensive: chances created vs opponent tackles
    h_cc_pg = h.chances_created / gh
    a_tkl_pg = a.tackles / ga
    creative_edge = (h_cc_pg - 7) * (12 - a_tkl_pg) * 0.005

    return round(max(-0.3, min(0.3, press_edge + cross_edge + creative_edge)), 3)


# ══════════════════════════════════════════════════════════
#  STAR GOALS POWER & STAR DEPENDENCY
#  (user definition: star = top goalscorer output;
#   team = how concentrated/balanced is the scoring)
# ══════════════════════════════════════════════════════════

def star_goals_power(team: str) -> float:
    """
    Total World Cup goals from this team's players in the top scorers chart.
    Directly captures "球队在射手榜上的进球产出".

    Examples:
      France (Mbappé 8, Dembélé 5)        → 13.0
      Norway (Haaland 7)                   →  7.0
      England (Kane 6, Bellingham 4)       → 10.0
    """
    from src.data_collection.players import TOP_SCORERS
    total = sum(
        data.get("goals", 0)
        for data in TOP_SCORERS.values()
        if data.get("team") == team
    )
    return float(total)


def star_dependency_index(team: str) -> float:
    """
    Measure how dependent a team is on its absolute main player(s).
    Range: 0.0 (perfectly balanced) → 1.0 (completely reliant on one star).
    Uses Herfindahl-Hirschman concentration index on goal distribution.

    "有没有人是绝对主力"：
      Norway  (Haaland 7/7 goals)          → ~1.00  ← 绝对主力
      France  (Mbappé 8, Dembélé 5, ...)   → ~0.32  ← 多点开花
      Switzerland (Manzambi 3)             →  0.50  ← 数据不足中性值
    """
    from src.data_collection.players import TOP_SCORERS

    goals = [
        data.get("goals", 0)
        for data in TOP_SCORERS.values()
        if data.get("team") == team
    ]
    if not goals:
        return 0.50
    total = sum(goals)
    if total == 0 or len(goals) == 1:
        return 1.0 if len(goals) == 1 else 0.50

    # Herfindahl index on goal shares, normalized to [0, 1]
    hhi = sum((g / total) ** 2 for g in goals)
    n = len(goals)
    return round((hhi - 1 / n) / (1 - 1 / n), 3)
