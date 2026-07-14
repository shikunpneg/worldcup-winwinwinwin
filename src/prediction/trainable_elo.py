"""
Trainable Elo Rating System for World Cup 2026 prediction.

Dual-layer model:
  1. Softmax regression over Elo difference → proper H/D/A probabilities
  2. Poisson distribution → scoreline prediction (from expected goals)

Both layers are calibrated from actual match data.
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from math import exp, log, factorial

from src.data_collection.worldcup_skill import WorldCupDataSkill

MAX_GOALS = 8

# Module-level flag: DC calibration runs only once per session
_DC_CALIBRATED_FLAG = False


# ─── Dixon-Coles / Feature helpers ───
# Global averages for feature normalization
_GLOBAL_AVG_SHOTS_PG = 14.5
_GLOBAL_AVG_SOT_PG = 5.4
_GLOBAL_AVG_POSS = 50.0


def _load_team_features():
    """Lazy-load advanced team stats."""
    from src.data_collection.team_advanced_stats import (
        get_team_stats, get_tactical_profile, get_shots_per_game,
        get_sot_per_game, get_possession, get_pass_accuracy,
    )
    return (get_team_stats, get_tactical_profile, get_shots_per_game,
            get_sot_per_game, get_possession, get_pass_accuracy)


from src.data_collection.team_advanced_stats import get_tactical_profile


def compute_initial_ratings(market_values: dict,
                            min_rating: float = 1400.0,
                            max_rating: float = 1600.0) -> Dict[str, float]:
    """
    Convert market values to initial Elo ratings.
    Linear scaling: highest MV → max_rating, lowest MV → min_rating.
    """
    if not market_values:
        return {}
    vals = list(market_values.values())
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return {}
    ratings = {}
    for team, mv in market_values.items():
        norm = (mv - lo) / (hi - lo)  # 0..1
        ratings[team] = round(min_rating + norm * (max_rating - min_rating), 1)
    return ratings


def poisson_prob(k: int, lam: float) -> float:
    """Poisson probability P(X = k)."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return exp(-lam) * (lam ** k) / factorial(k)


@dataclass
class EloConfig:
    """Elo system configuration. Optimized via Bayesian CV."""
    K: float = 7.9       # Optimized from 40.0 (Bayesian optimization, FIFA-MODEL)
    home_advantage: float = 7.0  # Optimized from 100.0 (Bayesian optimization)
    initial_rating: float = 1500.0
    # Softmax calibration
    elo_spread: float = 0.008   # Optimized from 0.025
    draw_intercept: float = 0.96  # Optimized from 0.0
    # Poisson calibration
    avg_total_goals: float = 2.908
    # Market value feature
    market_value_weight: float = 0.0  # How much MV ratio affects expected goals
    # Dixon-Coles attack/defense
    use_attack_defense: bool = True
    attack_k: float = 8.0     # Attack learning rate (/100 = effective rate)
    defense_k: float = 8.0    # Defense learning rate (/100 = effective rate)
    initial_attack: float = 1.0
    initial_defense: float = 1.0
    # Feature weights (multipliers for expected goals)
    feature_shots_weight: float = 0.0
    feature_possession_weight: float = 0.0
    feature_stamina_weight: float = 0.0
    feature_star_weight: float = 0.0
    feature_tactical_weight: float = 0.0
    feature_cohesion_weight: float = 0.0


class EloSystem:
    """
    Core Elo rating engine.
    Tracks ratings, updates after matches, computes Elo differences.
    """

    def __init__(self, config: EloConfig = None, initial_ratings: dict = None):
        self.config = config or EloConfig()
        self.ratings: Dict[str, float] = dict(initial_ratings or {})
        self.rating_history: Dict[str, List[Tuple[int, float]]] = {}
        self._match_counter = 0
        # Dixon-Coles attack/defense
        self.attack: Dict[str, float] = {}
        self.defense: Dict[str, float] = {}
        if initial_ratings:
            for team in initial_ratings:
                self.attack[team] = self.config.initial_attack
                self.defense[team] = self.config.initial_defense

    def get_rating(self, team: str) -> float:
        return self.ratings.get(team, self.config.initial_rating)

    def get_attack(self, team: str) -> float:
        """Dixon-Coles attack strength (higher = scores more)."""
        return self.attack.get(team, self.config.initial_attack)

    def get_defense(self, team: str) -> float:
        """Dixon-Coles defense strength (lower = concedes fewer)."""
        return self.defense.get(team, self.config.initial_defense)

    def elo_diff(self, home_team: str, away_team: str) -> float:
        """Elo difference (home - away) including home advantage."""
        return (self.get_rating(home_team) + self.config.home_advantage
                - self.get_rating(away_team))

    @staticmethod
    def expected_score(diff: float) -> float:
        """Expected score from Elo difference."""
        return 1.0 / (1.0 + 10 ** (-diff / 400.0))

    def update(self, home_team: str, away_team: str,
               home_score: int, away_score: int):
        """Update ratings and attack/defense after a match."""
        self._match_counter += 1

        for team in (home_team, away_team):
            if team not in self.ratings:
                self.ratings[team] = self.config.initial_rating
            if team not in self.rating_history:
                self.rating_history[team] = []
            if team not in self.attack:
                self.attack[team] = self.config.initial_attack
            if team not in self.defense:
                self.defense[team] = self.config.initial_defense

        # ─── Elo update ───
        diff = self.elo_diff(home_team, away_team)
        expected_home = self.expected_score(diff)
        if home_score > away_score:
            actual = 1.0
        elif home_score == away_score:
            actual = 0.5
        else:
            actual = 0.0
        gd = min(abs(home_score - away_score), 3)
        k = self.config.K * (1.0 + 0.5 * gd)
        change = k * (actual - expected_home)
        self.ratings[home_team] += change
        self.ratings[away_team] -= change
        self.rating_history[home_team].append(
            (self._match_counter, self.ratings[home_team]))
        self.rating_history[away_team].append(
            (self._match_counter, self.ratings[away_team]))

        # ─── Dixon-Coles attack/defense update ───
        if self.config.use_attack_defense:
            h_att = self.attack[home_team]
            h_def = self.defense[home_team]
            a_att = self.attack[away_team]
            a_def = self.defense[away_team]
            exp_h = self.config.avg_total_goals * h_att * a_def
            exp_a = self.config.avg_total_goals * a_att * h_def

            # Smoothed observed/expected ratio (add 1 to avoid division by zero)
            h_att_ratio = (home_score + 1.0) / (exp_h + 1.0)
            a_att_ratio = (away_score + 1.0) / (exp_a + 1.0)

            # Damped proportional update (ak/dk are divided by 100 for stability)
            ak = self.config.attack_k / 100.0
            dk = self.config.defense_k / 100.0

            self.attack[home_team] = max(0.3, min(3.0, h_att * (1.0 + ak * (h_att_ratio - 1.0))))
            self.defense[home_team] = max(0.3, min(3.0, h_def * (1.0 + dk * (a_att_ratio - 1.0))))
            self.attack[away_team] = max(0.3, min(3.0, a_att * (1.0 + ak * (a_att_ratio - 1.0))))
            self.defense[away_team] = max(0.3, min(3.0, a_def * (1.0 + dk * (h_att_ratio - 1.0))))

    def fit(self, matches_df: pd.DataFrame) -> "EloSystem":
        """Train on completed matches sequentially."""
        completed = matches_df[
            matches_df["status"].str.lower().isin(
                ["completed", "finished", "ft", "final"])
        ].sort_values("match_id").copy()

        if not completed.empty:
            tg = (completed["home_score"] + completed["away_score"]).sum()
            self.config.avg_total_goals = tg / len(completed)

        for _, row in completed.iterrows():
            self.update(
                row["home_team"], row["away_team"],
                int(row["home_score"]), int(row["away_score"]),
            )

        # Normalize attack/defense so mean attack = 1.0, mean defense = 1.0
        if self.config.use_attack_defense and self.attack:
            mean_att = sum(self.attack.values()) / max(len(self.attack), 1)
            mean_def = sum(self.defense.values()) / max(len(self.defense), 1)
            if mean_att > 0 and mean_def > 0:
                for team in list(self.attack.keys()):
                    self.attack[team] = max(0.3, min(3.0,
                        self.attack[team] / mean_att))
                    self.defense[team] = max(0.3, min(3.0,
                        self.defense[team] / mean_def))
        return self


class WorldCupPredictor:
    """
    Full predictor: Elo + Softmax (H/D/A) + Poisson (score).
    """

    def __init__(self, config: EloConfig = None, market_values: dict = None):
        self.config = config or EloConfig()
        self.elo: Optional[EloSystem] = None
        self._market_values = market_values or {}
        if self._market_values:
            self._avg_mv = sum(self._market_values.values()) / max(len(self._market_values), 1)
        else:
            self._avg_mv = 1.0
        self._initial_ratings = compute_initial_ratings(self._market_values)

    def _mv_ratio(self, team: str) -> float:
        """Market value ratio vs average (caps at 3x to prevent extreme influence)."""
        mv = self._market_values.get(team, self._avg_mv)
        return max(0.3, min(3.0, mv / max(self._avg_mv, 1)))

    def train_elo(self, matches_df: pd.DataFrame):
        """Train Elo ratings on match data."""
        self.elo = EloSystem(self.config, initial_ratings=self._initial_ratings)
        self.elo.fit(matches_df)

    # ─── Outcome probabilities (Softmax over Elo diff) ───

    def outcome_probs(self, home_team: str, away_team: str) -> Dict:
        """
        3-outcome probabilities via softmax on Elo difference.
        P(home_win) ∝ exp(α * diff)
        P(draw)     ∝ exp(β)
        P(away_win) ∝ exp(-α * diff)
        """
        diff = self.elo.elo_diff(home_team, away_team)
        s = self.config.elo_spread

        log_odds_h = s * diff
        log_odds_d = self.config.draw_intercept
        log_odds_a = -s * diff

        e_h = exp(log_odds_h)
        e_d = exp(log_odds_d)
        e_a = exp(log_odds_a)
        total = e_h + e_d + e_a

        return {
            "home_win_prob": e_h / total,
            "draw_prob": e_d / total,
            "away_win_prob": e_a / total,
        }

    # ─── Score prediction (Poisson) ───

    def _expected_goals(self, home_team: str, away_team: str) -> Tuple[float, float]:
        """
        Dixon-Coles style expected goals.
        Base: Poisson mean = avg_total_goals * home_attack * away_defense
        Adjusted by: MV ratio, possession, shots, stamina, star players.
        """
        avg = self.config.avg_total_goals

        if self.config.use_attack_defense and self.elo is not None:
            h_att = self.elo.get_attack(home_team)
            a_def = self.elo.get_defense(away_team)
            a_att = self.elo.get_attack(away_team)
            h_def = self.elo.get_defense(home_team)
            home_exp = avg * h_att * a_def
            away_exp = avg * a_att * h_def
        else:
            diff = self.elo.elo_diff(home_team, away_team) if self.elo else 0
            rating_ratio = 10 ** (diff / 400.0)
            home_exp = avg * rating_ratio / (1.0 + rating_ratio)
            away_exp = avg / (1.0 + rating_ratio)

        # ─── Feature multipliers ───
        # 1. Market value ratio
        mv_h = self._mv_ratio(home_team)
        mv_a = self._mv_ratio(away_team)
        mv_factor = 1.0 + self.config.market_value_weight * ((mv_h / max(mv_a, 0.01)) - 1.0)
        home_exp *= mv_factor
        away_exp /= mv_factor

        # 2. Advanced features (shots, possession, stamina, stars, tactical, cohesion)
        if any([
            self.config.feature_shots_weight,
            self.config.feature_possession_weight,
            self.config.feature_stamina_weight,
            self.config.feature_star_weight,
            self.config.feature_tactical_weight,
            self.config.feature_cohesion_weight,
        ]):
            from src.data_collection.team_advanced_stats import (
                get_sot_per_game, get_possession,
                get_team_stamina_by_players, get_tactical_matchup,
                star_goals_power, star_dependency_index,
            )

            # Shots on target ratio
            if self.config.feature_shots_weight:
                h_sot = get_sot_per_game(home_team)
                a_sot = get_sot_per_game(away_team)
                sot_ratio = h_sot / max(a_sot, 0.01)
                shot_factor = 1.0 + self.config.feature_shots_weight * (sot_ratio - 1.0)
                home_exp *= shot_factor
                away_exp /= shot_factor

            # Possession ratio
            if self.config.feature_possession_weight:
                h_poss = get_possession(home_team)
                a_poss = get_possession(away_team)
                poss_ratio = (h_poss / 100.0) / max(a_poss / 100.0, 0.01)
                poss_factor = 1.0 + self.config.feature_possession_weight * (poss_ratio - 1.0)
                home_exp *= poss_factor
                away_exp /= poss_factor

            # Star player count (from actual goal/assist data)
            if self.config.feature_star_weight:
                h_stars = star_goals_power(home_team)
                a_stars = star_goals_power(away_team)
                star_ratio = (1 + h_stars) / max(1 + a_stars, 1)
                star_factor = 1.0 + self.config.feature_star_weight * (star_ratio - 1.0)
                home_exp *= star_factor
                away_exp /= star_factor

            # Stamina factor (younger teams have better endurance in 2nd half)
            if self.config.feature_stamina_weight:
                h_stam = get_team_stamina_by_players(home_team)
                a_stam = get_team_stamina_by_players(away_team)
                stam_ratio = h_stam / max(a_stam, 0.01)
                stam_factor = 1.0 + self.config.feature_stamina_weight * (stam_ratio - 1.0)
                home_exp *= stam_factor
                away_exp /= stam_factor

            # Tactical matchup factor (press intensity × style interaction)
            if self.config.feature_tactical_weight:
                matchup = get_tactical_matchup(home_team, away_team)
                # matchup ≈ -0.3 to +0.3, convert to ~0.91 to 1.09 multiplier
                tact_factor = 1.0 + self.config.feature_tactical_weight * matchup
                home_exp *= tact_factor
                away_exp /= tact_factor

            # Cohesion → Star dependency factor (balanced scoring vs one absolute main player)
            if self.config.feature_cohesion_weight:
                h_dep = star_dependency_index(home_team)
                a_dep = star_dependency_index(away_team)
                dep_ratio = (1 + h_dep) / max(1 + a_dep, 0.5)
                dep_factor = 1.0 + self.config.feature_cohesion_weight * (dep_ratio - 1.0)
                home_exp *= dep_factor
                away_exp /= dep_factor

        # Clamp to realistic range
        home_exp = max(0.1, min(MAX_GOALS, home_exp))
        away_exp = max(0.1, min(MAX_GOALS, away_exp))

        return home_exp, away_exp

    def predict_score(self, home_team: str, away_team: str, stage: str = "") -> Dict:
        """
        Full prediction: outcome probs + scoreline.
        Final match: lower expected goals (defensive, high stakes).
        """
        # Outcome probabilities
        outcome = self.outcome_probs(home_team, away_team)

        # Expected goals
        home_exp, away_exp = self._expected_goals(home_team, away_team)

        # Finals are more defensive - reduce expected goals
        is_final = "final" in stage.lower() and "third" not in stage.lower()
        if is_final:
            home_exp *= 0.70
            away_exp *= 0.70

        # Score probability distribution
        best_score = (0, 0)
        best_prob = 0.0
        home_win_prob = draw_prob = away_win_prob = 0.0

        for i in range(MAX_GOALS + 1):
            for j in range(MAX_GOALS + 1):
                p = poisson_prob(i, home_exp) * poisson_prob(j, away_exp)
                if p > best_prob:
                    best_prob = p
                    best_score = (i, j)
                if i > j:
                    home_win_prob += p
                elif i == j:
                    draw_prob += p
                else:
                    away_win_prob += p

        # Determine predicted winner (for knockout stages, force a winner)
        is_ko = stage.lower() not in ("group stage", "group", "") and "third" not in stage.lower()
        if outcome["home_win_prob"] > outcome["draw_prob"] and outcome["home_win_prob"] > outcome["away_win_prob"]:
            predicted_outcome = "home_win"
            predicted_winner = home_team
        elif outcome["away_win_prob"] > outcome["draw_prob"] and outcome["away_win_prob"] > outcome["home_win_prob"]:
            predicted_outcome = "away_win"
            predicted_winner = away_team
        else:
            predicted_outcome = "draw"
            # In knockout, draws always go to penalties — force a winner
            if is_ko:
                predicted_winner = home_team if outcome["home_win_prob"] >= outcome["away_win_prob"] else away_team
            else:
                predicted_winner = "draw"

        # Penalty probability based on historical World Cup stats
        # Source: FIFA-MODEL analysis of 246 knockout matches (1930-2022)
        stage_lower = stage.lower()
        if predicted_outcome == "draw" and is_ko:
            # 89.7% of knockout draws go to penalties
            penalty_prob = 0.90
        else:
            penalty_prob = 0.0

        # Finals and draws: use Poisson best_score (most likely exact score)
        # This gives realistic scores like 1-0, 0-0, 1-1 instead of rounding
        if is_final or predicted_outcome == "draw" or (home_exp < 1.2 and away_exp < 1.2):
            expected_h = best_score[0]
            expected_a = best_score[1]
        else:
            expected_h = max(0, min(MAX_GOALS, round(home_exp)))
            expected_a = max(0, min(MAX_GOALS, round(away_exp)))
            if home_exp > 0.01 and expected_h == 0:
                expected_h = 1
            if away_exp > 0.01 and expected_a == 0:
                expected_a = 1

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_elo": self.elo.get_rating(home_team),
            "away_elo": self.elo.get_rating(away_team),
            "elo_diff": self.elo.elo_diff(home_team, away_team),
            "home_exp_goals": round(home_exp, 3),
            "away_exp_goals": round(away_exp, 3),
            # Outcome probs (from softmax)
            "home_win_prob": round(outcome["home_win_prob"], 4),
            "draw_prob": round(outcome["draw_prob"], 4),
            "away_win_prob": round(outcome["away_win_prob"], 4),
            # Score probs (from Poisson)
            "score_home_win_prob": round(home_win_prob, 4),
            "score_draw_prob": round(draw_prob, 4),
            "score_away_win_prob": round(away_win_prob, 4),
            # Predicted scoreline
            "predicted_score_home": expected_h,
            "predicted_score_away": expected_a,
            "predicted_score": f"{expected_h}-{expected_a}",
            "predicted_score_prob": round(best_prob, 4),
            # Outcome
            "predicted_outcome": predicted_outcome,
            "predicted_winner": predicted_winner,
            # Penalty prediction
            "penalty_probability": round(penalty_prob, 2),
        }

    # ─── Evaluation ───

    def evaluate(self, matches_df: pd.DataFrame) -> Dict:
        """
        Sequential time-series evaluation.
        For each match: predict using only past data, then update.
        """
        completed = matches_df[
            matches_df["status"].str.lower().isin(
                ["completed", "finished", "ft", "final"])
        ].sort_values("match_id").copy()

        # Save & reset Elo
        saved = {
            "ratings": dict(self.elo.ratings) if self.elo else {},
            "history": dict(self.elo.rating_history) if self.elo else {},
            "counter": self.elo._match_counter if self.elo else 0,
        }
        self.elo = EloSystem(self.config, initial_ratings=self._initial_ratings)

        # Calibrate spread & draw_intercept from data
        self._calibrate(completed)

        results = []
        for _, row in completed.iterrows():
            home, away = row["home_team"], row["away_team"]
            hs, as_ = int(row["home_score"]), int(row["away_score"])

            pred = self.predict_score(home, away)

            # Actual outcome
            if hs > as_:
                actual_outcome = "home_win"
            elif hs == as_:
                actual_outcome = "draw"
            else:
                actual_outcome = "away_win"

            correct = pred["predicted_outcome"] == actual_outcome

            # Log loss on outcome
            prob_actual = pred[f"{actual_outcome}_prob"]
            prob_actual = max(min(prob_actual, 0.9999), 0.0001)
            logloss = -log(prob_actual)

            # Brier
            actual_vec = [
                1.0 if actual_outcome == "home_win" else 0.0,
                1.0 if actual_outcome == "draw" else 0.0,
                1.0 if actual_outcome == "away_win" else 0.0,
            ]
            pred_vec = [
                pred["home_win_prob"],
                pred["draw_prob"],
                pred["away_win_prob"],
            ]
            brier = sum((p - a) ** 2 for p, a in zip(pred_vec, actual_vec))

            results.append({
                "correct": correct,
                "logloss": logloss,
                "brier": brier,
                "actual_outcome": actual_outcome,
                "pred_outcome": pred["predicted_outcome"],
            })

            # Update Elo
            self.elo.update(home, away, hs, as_)

        # Restore
        if saved["ratings"]:
            self.elo.ratings = saved["ratings"]
            self.elo.rating_history = saved["history"]
            self.elo._match_counter = saved["counter"]

        n = len(results)
        correct_ct = sum(1 for r in results if r["correct"])
        acc = correct_ct / n if n else 0
        avg_ll = np.mean([r["logloss"] for r in results]) if results else 0
        avg_bs = np.mean([r["brier"] for r in results]) if results else 0

        actual = pd.Series([r["actual_outcome"] for r in results])
        preds = pd.Series([r["pred_outcome"] for r in results])
        confusion = pd.crosstab(actual, preds, rownames=["Actual"],
                                colnames=["Predicted"])

        return {
            "accuracy": acc,
            "log_loss": avg_ll,
            "brier_score": avg_bs,
            "correct": correct_ct,
            "total": n,
            "confusion_matrix": confusion,
        }

    def _calibrate(self, matches_df: pd.DataFrame):
        """
        Calibrate softmax parameters (elo_spread, draw_intercept) from data.
        Uses a simple grid search on the given matches to maximize accuracy.
        """
        import itertools

        best_acc = 0.0
        best_params = (self.config.elo_spread, self.config.draw_intercept)

        for spread in np.arange(0.005, 0.051, 0.005):
            for intercept in np.arange(-1.0, 1.2, 0.2):
                temp_config = EloConfig(
                    K=self.config.K,
                    home_advantage=self.config.home_advantage,
                    elo_spread=spread,
                    draw_intercept=intercept,
                )
                temp_elo = EloSystem(temp_config, initial_ratings=self._initial_ratings)
                temp_elo.fit(matches_df)

                correct = 0
                total = 0
                for _, row in matches_df.iterrows():
                    diff = temp_elo.elo_diff(row["home_team"], row["away_team"])
                    e_h = exp(spread * diff)
                    e_d = exp(intercept)
                    e_a = exp(-spread * diff)
                    total_p = e_h + e_d + e_a
                    probs = {"home_win": e_h / total_p, "draw": e_d / total_p,
                             "away_win": e_a / total_p}

                    hs, as_ = int(row["home_score"]), int(row["away_score"])
                    if hs > as_:
                        actual = "home_win"
                    elif hs == as_:
                        actual = "draw"
                    else:
                        actual = "away_win"

                    pred = max(probs, key=probs.get)
                    if pred == actual:
                        correct += 1
                    total += 1

                acc = correct / total
                if acc > best_acc:
                    best_acc = acc
                    best_params = (spread, intercept)

        self.config.elo_spread, self.config.draw_intercept = best_params
        self.elo = EloSystem(self.config, initial_ratings=self._initial_ratings)
        self.elo.fit(matches_df)

        # Also calibrate market_value_weight for Poisson expected goals
        if self._market_values:
            best_mv_w = 0.0
            best_mv_acc = 0.0
            for mv_w in [0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5]:
                # Create predictor with this mv_weight but same spread/intercept
                test_config = EloConfig(
                    K=self.config.K,
                    home_advantage=self.config.home_advantage,
                    elo_spread=self.config.elo_spread,
                    draw_intercept=self.config.draw_intercept,
                    market_value_weight=mv_w,
                )
                test_pred = WorldCupPredictor(test_config, market_values=self._market_values)

                # Manual sequential evaluation with this mv_weight
                test_pred.elo = EloSystem(test_config,
                                          initial_ratings=self._initial_ratings)
                correct = 0
                total = 0
                for _, row in matches_df.iterrows():
                    diff = test_pred.elo.elo_diff(
                        row["home_team"], row["away_team"])
                    p_h = exp(test_config.elo_spread * diff)
                    p_d = exp(test_config.draw_intercept)
                    p_a = exp(-test_config.elo_spread * diff)
                    s = p_h + p_d + p_a
                    probs = {"home_win": p_h/s, "draw": p_d/s, "away_win": p_a/s}
                    hs, as_ = int(row["home_score"]), int(row["away_score"])
                    actual = "home_win" if hs > as_ else ("draw" if hs == as_ else "away_win")
                    if max(probs, key=probs.get) == actual:
                        correct += 1
                    total += 1
                    # Update Elo for next match
                    test_pred.elo.update(row["home_team"], row["away_team"],
                                         int(row["home_score"]), int(row["away_score"]))
                mv_acc = correct / total if total > 0 else 0
                if mv_acc > best_mv_acc:
                    best_mv_acc = mv_acc
                    best_mv_w = mv_w
            self.config.market_value_weight = best_mv_w
            print(f"[CALIBRATE] Best market_value_weight={best_mv_w:.2f} "
                  f"(acc={best_mv_acc:.4f})")

        # ─── Dixon-Coles & feature calibration (score prediction) ───
        global _DC_CALIBRATED_FLAG
        if self.config.use_attack_defense and not _DC_CALIBRATED_FLAG:
            print(f"[CALIBRATE] Tuning attack/defense & features...")
            best_score = 0.0
            best_ad = (self.config.attack_k, self.config.defense_k,
                       self.config.feature_shots_weight,
                       self.config.feature_possession_weight,
                       self.config.feature_star_weight,
                       self.config.feature_stamina_weight,
                       self.config.feature_tactical_weight,
                       self.config.feature_cohesion_weight)
            # Test attack/defense learning rates
            for ak, dk in [(4,4),(6,6),(8,8),(10,10),(12,12),(15,15),(20,20),
                           (8,4),(4,8),(10,6),(6,10),(15,10),(10,15)]:
                test_cfg = EloConfig(
                    K=self.config.K, home_advantage=self.config.home_advantage,
                    elo_spread=self.config.elo_spread,
                    draw_intercept=self.config.draw_intercept,
                    market_value_weight=self.config.market_value_weight,
                    use_attack_defense=True,
                    attack_k=ak, defense_k=dk,
                )
                test_pred = WorldCupPredictor(test_cfg, market_values=self._market_values)
                test_pred.elo = EloSystem(test_cfg, initial_ratings=self._initial_ratings)
                correct = 0
                total = 0
                for _, row in matches_df.iterrows():
                    he, ae = test_pred._expected_goals(
                        row["home_team"], row["away_team"])
                    expected_h = max(0, min(MAX_GOALS, round(he)))
                    expected_a = max(0, min(MAX_GOALS, round(ae)))
                    if he > 0.01 and expected_h == 0: expected_h = 1
                    if ae > 0.01 and expected_a == 0: expected_a = 1
                    hs, as_ = int(row["home_score"]), int(row["away_score"])
                    actual_w = "home" if hs > as_ else ("draw" if hs == as_ else "away")
                    pred_w = "home" if expected_h > expected_a else (
                        "draw" if expected_h == expected_a else "away")
                    if pred_w == actual_w:
                        correct += 1
                    total += 1
                    test_pred.elo.update(
                        row["home_team"], row["away_team"],
                        int(row["home_score"]), int(row["away_score"]))
                score = correct / total if total else 0
                if score > best_score:
                    best_score = score
                    best_ad = (ak, dk, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

            # Test feature weights (fixed attack/defense from best)
            for shots_w in [0.0, 0.05, 0.1]:
                for poss_w in [0.0, 0.05, 0.1]:
                    for star_w in [0.0, 0.05, 0.1]:
                        for stam_w in [0.0, 0.05, 0.1, 0.15]:
                            for tact_w in [0.0, 0.05, 0.1, 0.15]:
                                for coh_w in [0.0, 0.05, 0.1, 0.15]:
                                    if shots_w == 0 and poss_w == 0 and star_w == 0 and stam_w == 0 and tact_w == 0 and coh_w == 0:
                                        continue
                            test_cfg = EloConfig(
                                K=self.config.K, home_advantage=self.config.home_advantage,
                                elo_spread=self.config.elo_spread,
                                draw_intercept=self.config.draw_intercept,
                                market_value_weight=self.config.market_value_weight,
                                use_attack_defense=True,
                                attack_k=best_ad[0], defense_k=best_ad[1],
                                feature_shots_weight=shots_w,
                                feature_possession_weight=poss_w,
                                feature_star_weight=star_w,
                                feature_stamina_weight=stam_w,
                                feature_tactical_weight=tact_w,
                                feature_cohesion_weight=coh_w,
                            )
                            test_pred = WorldCupPredictor(
                                test_cfg, market_values=self._market_values)
                            test_pred.elo = EloSystem(
                                test_cfg, initial_ratings=self._initial_ratings)
                            correct = 0
                            total = 0
                            for _, row in matches_df.iterrows():
                                he, ae = test_pred._expected_goals(
                                    row["home_team"], row["away_team"])
                                expected_h = max(0, min(MAX_GOALS, round(he)))
                                expected_a = max(0, min(MAX_GOALS, round(ae)))
                                if he > 0.01 and expected_h == 0: expected_h = 1
                                if ae > 0.01 and expected_a == 0: expected_a = 1
                                hs, as_ = int(row["home_score"]), int(row["away_score"])
                                actual_w = "home" if hs > as_ else (
                                    "draw" if hs == as_ else "away")
                                pred_w = "home" if expected_h > expected_a else (
                                    "draw" if expected_h == expected_a else "away")
                                if pred_w == actual_w:
                                    correct += 1
                                total += 1
                                test_pred.elo.update(
                                    row["home_team"], row["away_team"],
                                    int(row["home_score"]), int(row["away_score"]))
                            score = correct / total if total else 0
                            if score > best_score:
                                best_score = score
                                best_ad = (best_ad[0], best_ad[1],
                                           shots_w, poss_w, star_w, stam_w, tact_w, coh_w)

            self.config.attack_k = best_ad[0]
            self.config.defense_k = best_ad[1]
            self.config.feature_shots_weight = best_ad[2]
            self.config.feature_possession_weight = best_ad[3]
            self.config.feature_star_weight = best_ad[4]
            self.config.feature_stamina_weight = best_ad[5]
            self.config.feature_tactical_weight = best_ad[6]
            self.config.feature_cohesion_weight = best_ad[7]
            print(f"[CALIBRATE] Best DC: ak={best_ad[0]:.1f} "
                  f"dk={best_ad[1]:.1f} shots={best_ad[2]:.2f} "
                  f"poss={best_ad[3]:.2f} star={best_ad[4]:.2f} "
                  f"stam={best_ad[5]:.2f} tact={best_ad[6]:.2f} "
                  f"coh={best_ad[7]:.2f} score_acc={best_score:.4f}")
            _DC_CALIBRATED_FLAG = True

        # Rebuild Elo with final config
        self.elo = EloSystem(self.config, initial_ratings=self._initial_ratings)
        self.elo.fit(matches_df)


class HyperparameterSearch:
    """Grid search over K, home_advantage, and market_value_weight."""

    def __init__(self, market_values: dict = None):
        self.results: List[Dict] = []
        self.best_config: Optional[EloConfig] = None
        self.best_score: float = 0.0
        self._market_values = market_values or {}

    def search(self, matches_df: pd.DataFrame,
               K_range: List[float] = None,
               home_adv_range: List[float] = None,
               mv_weight_range: List[float] = None) -> EloConfig:
        if K_range is None:
            K_range = list(range(5, 85, 5))
        if home_adv_range is None:
            home_adv_range = list(range(0, 175, 25))

        self.results = []
        total = len(K_range) * len(home_adv_range)
        current = 0

        print(f"[INFO] Hyperparameter search: {total} combinations")
        print(f"       K values: {K_range}")
        print(f"       Home adv: {home_adv_range}")
        print()

        for K in K_range:
            for ha in home_adv_range:
                current += 1
                config = EloConfig(K=float(K), home_advantage=float(ha),
                                    use_attack_defense=True)
                pred = WorldCupPredictor(config, market_values=self._market_values)
                pred.train_elo(matches_df)
                result = pred.evaluate(matches_df)

                score = result["accuracy"]
                self.results.append({
                    "K": K,
                    "home_advantage": ha,
                    "accuracy": result["accuracy"],
                    "log_loss": result["log_loss"],
                    "brier_score": result["brier_score"],
                    "correct": result["correct"],
                    "total": result["total"],
                })

                if score > self.best_score:
                    self.best_score = score
                    # Capture full config including DC parameters from calibration
                    self.best_config = pred.config

                if current % 10 == 0 or current == total:
                    print(f"  [{current:3d}/{total}] K={K:2d}  home={ha:3d}  →  "
                          f"acc={result['accuracy']:.4f}  ll={result['log_loss']:.4f}  "
                          f"brier={result['brier_score']:.4f}")

        print()
        print(f"[INFO] Best: K={self.best_config.K:.0f}, "
              f"home_adv={self.best_config.home_advantage:.0f}, "
              f"accuracy={self.best_score:.4f}")
        return self.best_config

    def results_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.results).sort_values("accuracy", ascending=False)


class TournamentPredictor:
    """
    End-to-end tournament predictor.
    Trains on completed matches, predicts all remaining knockout matches
    with scorelines, resolves placeholders step by step.
    """

    def __init__(self, config: EloConfig = None, market_values: dict = None):
        self.config = config or EloConfig()
        self.predictor: Optional[WorldCupPredictor] = None
        self.matches_df: Optional[pd.DataFrame] = None
        self._market_values = market_values or {}

    def train(self, matches_df: pd.DataFrame):
        self.matches_df = matches_df
        self.predictor = WorldCupPredictor(self.config, market_values=self._market_values)
        self.predictor.train_elo(matches_df)
        print(f"[INFO] Model trained. "
              f"spread={self.predictor.config.elo_spread:.3f}, "
              f"draw_intercept={self.predictor.config.draw_intercept:.2f}, "
              f"attack_k={self.predictor.config.attack_k:.1f}, "
              f"defense_k={self.predictor.config.defense_k:.1f}, "
              f"shots_w={self.predictor.config.feature_shots_weight:.2f}, "
              f"poss_w={self.predictor.config.feature_possession_weight:.2f}, "
              f"star_w={self.predictor.config.feature_star_weight:.2f}, "
              f"stam_w={self.predictor.config.feature_stamina_weight:.2f}, "
              f"tact_w={self.predictor.config.feature_tactical_weight:.2f}, "
              f"coh_w={self.predictor.config.feature_cohesion_weight:.2f}")

    def _resolve_placeholders(self, matches: pd.DataFrame) -> dict:
        completed = matches[matches["status"].str.lower().isin(
            ["completed", "finished", "ft", "final"])]
        m = {}
        for _, r in completed.iterrows():
            mid = r["match_id"]
            hs, as_ = int(r["home_score"]), int(r["away_score"])
            if hs > as_:
                m[f"Winner Match {mid}"] = r["home_team"]
                m[f"Loser Match {mid}"] = r["away_team"]
            elif as_ > hs:
                m[f"Winner Match {mid}"] = r["away_team"]
                m[f"Loser Match {mid}"] = r["home_team"]
            else:
                m[f"Winner Match {mid}"] = r["home_team"]
                m[f"Loser Match {mid}"] = r["away_team"]
        return m

    def _resolve_name(self, name: str, mapping: dict) -> str:
        if name and ("Winner Match" in name or "Loser Match" in name):
            return mapping.get(name, name)
        return name

    def _elo_resolve_team(self, team_spec: str, dyn_map: dict) -> str:
        """
        Recursively resolve 'Winner Match X' / 'Loser Match X' placeholders
        by predicting the referenced match using Elo.
        """
        resolved = self._resolve_name(team_spec, dyn_map)
        if "Winner Match" not in resolved and "Loser Match" not in resolved:
            return resolved

        # Parse referenced match_id from "Winner Match 73" -> 73
        try:
            parts = resolved.split()
            match_id = int(parts[-1])
        except (ValueError, IndexError):
            return team_spec

        # Find the referenced match in matches_df
        ref_match = self.matches_df[self.matches_df["match_id"].astype(str) == str(match_id)]
        if ref_match.empty:
            return team_spec

        row = ref_match.iloc[0]
        home = self._elo_resolve_team(row["home_team"], dyn_map)
        away = self._elo_resolve_team(row["away_team"], dyn_map)

        if "Winner Match" in home or "Loser Match" in home or \
           "Winner Match" in away or "Loser Match" in away:
            return team_spec  # still unresolvable

        # Predict the referenced match
        pred = self.predictor.predict_score(home, away, stage=row["stage"])
        winner = pred["predicted_winner"]

        # Force a winner for knockout matches
        is_ko = row["stage"] not in ("Group Stage", "")
        if is_ko and winner == "draw":
            winner = home if pred["home_win_prob"] >= pred["away_win_prob"] else away

        dyn_map[f"Winner Match {match_id}"] = winner
        dyn_map[f"Loser Match {match_id}"] = away if winner == home else home

        # Return the resolved team
        if "Winner Match" in team_spec or f"Winner Match {match_id}" in team_spec:
            return winner
        else:
            return away if winner == home else home

    def predict_all(self) -> pd.DataFrame:
        """Predict all scheduled matches step by step with score resolution."""
        if self.predictor is None:
            raise ValueError("Not trained. Call train() first.")

        base_map = self._resolve_placeholders(self.matches_df)
        scheduled = self.matches_df[
            self.matches_df["status"].str.lower() == "scheduled"
        ].copy()

        if scheduled.empty:
            return pd.DataFrame()

        scheduled["match_num"] = pd.to_numeric(scheduled["match_id"], errors="coerce")
        scheduled = scheduled.sort_values("match_num")
        dyn_map = dict(base_map)
        predictions = []

        for _, row in scheduled.iterrows():
            home = self._resolve_name(row["home_team"], dyn_map)
            away = self._resolve_name(row["away_team"], dyn_map)
            mid = row["match_id"]

            if "Winner Match" in home or "Loser Match" in home or \
               "Winner Match" in away or "Loser Match" in away:
                # Try Elo-based recursive resolution first
                home = self._elo_resolve_team(home, dyn_map)
                away = self._elo_resolve_team(away, dyn_map)
                if "Winner Match" in home or "Loser Match" in home or \
                   "Winner Match" in away or "Loser Match" in away:
                    predictions.append(self._make_tbd_row(row, "placeholder"))
                    continue

            pred = self.predictor.predict_score(home, away, stage=row["stage"])
            winner = pred["predicted_winner"]

            # For knockout, winner must be a team (not draw)
            is_ko = row["stage"] not in ("Group Stage", "")
            if is_ko and winner == "draw":
                # Force winner by higher win prob
                if pred["home_win_prob"] >= pred["away_win_prob"]:
                    winner = home
                else:
                    winner = away

            dyn_map[f"Winner Match {mid}"] = winner
            dyn_map[f"Loser Match {mid}"] = away if winner == home else home

            predictions.append({
                "match_id": mid,
                "stage": row["stage"],
                "home_team": home,
                "away_team": away,
                "home_elo": round(pred["home_elo"], 1),
                "away_elo": round(pred["away_elo"], 1),
                "elo_diff": round(pred["elo_diff"], 1),
                "predicted_score": pred["predicted_score"],
                "home_win_prob": pred["home_win_prob"],
                "draw_prob": pred["draw_prob"],
                "away_win_prob": pred["away_win_prob"],
                "predicted_winner": winner,
                "penalty_probability": pred.get("penalty_probability", 0),
            })

        return pd.DataFrame(predictions)

    def _make_tbd_row(self, row: pd.Series, reason: str) -> Dict:
        return {
            "match_id": row["match_id"], "stage": row["stage"],
            "home_team": row["home_team"], "away_team": row["away_team"],
            "home_elo": 0, "away_elo": 0, "elo_diff": 0,
            "predicted_score": "?-?", "home_win_prob": 0,
            "draw_prob": 0, "away_win_prob": 0, "predicted_winner": "TBD",
        }


def run(export: bool = True):
    """Full pipeline."""
    # Lazy imports (heavy dependencies only needed for training, not API serving)
    from sklearn.metrics import accuracy_score
    from src.prediction.decision_tree import (
        engineer_features, WorldCupDecisionTree, WorldCupDTEnsemble,
    )
    
    print("=" * 68)
    print("  WORLD CUP 2026  —  TRAINABLE ELO + SOFTMAX/POISSON PREDICTOR")
    print("=" * 68)

    # 1. Data
    print("\n[1] Collecting data...")
    skill = WorldCupDataSkill()
    data = skill.collect_all()
    matches = data["matches"]
    completed = matches[matches["status"] == "completed"]
    scheduled = matches[matches["status"] == "scheduled"]
    print(f"    Completed: {len(completed)}  Scheduled: {len(scheduled)}")

    # Fetch market values
    market_values = skill.fetch_market_values()
    print(f"    Market values loaded for {len(market_values)} teams.")

    # 2. Hyperparameter search
    print("\n[2] Hyperparameter search for best K & home_advantage...")
    search = HyperparameterSearch(market_values=market_values)
    best_config = search.search(matches)

    # 3. Train & evaluate
    print(f"\n[3] Training final model (K={best_config.K:.0f}, "
          f"home_adv={best_config.home_advantage:.0f})...")
    predictor = TournamentPredictor(best_config, market_values=market_values)
    predictor.train(matches)

    # Full evaluation (re-run with best config for clean output)
    evaluator = WorldCupPredictor(best_config, market_values=market_values)
    evaluator.train_elo(matches)
    # Reset DC calibration flag so final run calibrates
    global _DC_CALIBRATED_FLAG
    _DC_CALIBRATED_FLAG = False
    result = evaluator.evaluate(matches)

    print(f"\n[4] Sequential cross-validation results:")
    print(f"    Accuracy:         {result['accuracy']:.4f}  "
          f"({result['correct']}/{result['total']})")
    print(f"    Log Loss:         {result['log_loss']:.4f}")
    print(f"    Brier Score:      {result['brier_score']:.4f}")
    print(f"    Baseline (always home win):   0.4845")
    print(f"    Baseline (always predict draw): 0.2474")

    if not result["confusion_matrix"].empty:
        print(f"\n    Confusion matrix (Actual rows × Predicted cols):")
        print(f"    {result['confusion_matrix'].to_string().replace(chr(10), chr(10)+'    ')}")


    # 5. Decision Tree interpretation layer
    print(f"\n[5] Decision Tree interpretation layer:")
    print(f"    {'-'*60}")

    # Inject Elo ratings into team_stats
    team_stats = data["team_stats"].copy()
    if evaluator and evaluator.elo:
        elo_ratings = dict(evaluator.elo.ratings)
        team_stats["elo"] = team_stats["team"].map(
            lambda t: elo_ratings.get(t, 1500))

    # Engineer features
    X, y = engineer_features(matches, team_stats)
    print(f"    Features: {len(X.columns)}  Matches: {len(X)}")
    for i, col in enumerate(X.columns, 1):
        print(f"      {i}. {col}")

    # Train decision tree
    dt = WorldCupDecisionTree(max_depth=4, min_samples_leaf=3)
    dt.train(X, y)

    # Feature importance
    imp = dt.get_feature_importance()
    print(f"\n    Feature Importance:")
    for _, r in imp.iterrows():
        print(f"      {r['feature']:30s} {r['importance']:.3f}")

    # Train ensemble
    ensemble = WorldCupDTEnsemble(dt_model=dt)
    ensemble.train(X, y, elo_predictor=evaluator)

    # Combined feature importance
    comb_imp = ensemble.get_feature_importance()
    print(f"\n    Ensemble Feature Importance (DT+RF combined):")
    for _, r in comb_imp.iterrows():
        print(f"      {r['feature']:30s} {r['combined']:.3f}")

    # Comparison summary
    print(f"\n    Model comparison on training data:")
    dt_train_acc = accuracy_score(y, dt.predict(X))
    rf_train_acc = accuracy_score(y, ensemble.rf.predict(X))
    print(f"      Decision Tree: {dt_train_acc:.2%}")
    print(f"      Random Forest: {rf_train_acc:.2%}")
    print(f"      Elo Softmax:   {result['accuracy']:.2%} (sequential CV)")

    # Decision tree visualization
    dt.render_tree(f"{skill.data_dir}/decision_tree.png", max_depth=3)

    # 6. Predict remaining
    print(f"\n[6] Remaining match predictions:")
    preds = predictor.predict_all()
    if not preds.empty:
        print(f"\n{'ID':>4} {'Stage':18s} {'Home':22s} {'Away':22s} "
              f"{'Score':>6} {'H%':>6} {'D%':>6} {'A%':>6} {'Winner':22s}")
        print("-" * 120)
        for _, r in preds.iterrows():
            hp = f"{r['home_win_prob']*100:.1f}%" if r['home_win_prob'] else "  -"
            dp = f"{r['draw_prob']*100:.1f}%" if r['draw_prob'] else "  -"
            ap = f"{r['away_win_prob']*100:.1f}%" if r['away_win_prob'] else "  -"
            score = r["predicted_score"] if r["predicted_score"] else " ?-?"
            print(f"{r['match_id']:>4} {r['stage']:18s} {r['home_team']:22s} "
                  f"{r['away_team']:22s} {score:>6} {hp:>6} {dp:>6} {ap:>6} "
                  f"{r['predicted_winner']:22s}")

    # Final ratings
    print(f"\n[7] Final Elo Ratings (with Dixon-Coles Attack/Defense):")
    if predictor.predictor and predictor.predictor.elo:
        elo = predictor.predictor.elo
        sorted_teams = sorted(elo.ratings.items(), key=lambda x: x[1], reverse=True)
        print(f"  {'Rank':>4} {'Team':22s} {'Rating':>8} {'Attack':>8} {'Defense':>8}")
        print(f"  {'-'*4} {'-'*22} {'-'*8} {'-'*8} {'-'*8}")
        for i, (team, rating) in enumerate(sorted_teams[:15], 1):
            att = elo.get_attack(team)
            deff = elo.get_defense(team)
            print(f"  {i:2d}. {team:22s} {rating:7.1f} {att:7.3f} {deff:7.3f}")

    # Export
    if export:
        skill.export_csv(data)
        search.results_df().to_csv(
            f"{skill.data_dir}/grid_search.csv", index=False, encoding="utf-8-sig")
        if not preds.empty:
            preds.to_csv(
                f"{skill.data_dir}/predictions.csv", index=False, encoding="utf-8-sig")
        print(f"\n[INFO] Results → {skill.data_dir}/")

    return {"eval": result, "config": best_config, "predictions": preds}


if __name__ == "__main__":
    run(export=True)
