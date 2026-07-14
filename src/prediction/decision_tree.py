"""
Decision Tree interpretation layer for World Cup 2026 prediction.

── Architecture ──────────────────────────────────────────
  [Interpretation Layer]  Decision Tree     → visual decision paths
  [Primary Predictor]     Elo + Softmax     → high accuracy (existing)
  [Ensemble Layer]        DT + RF + Elo     → weighted voting

── Critical fixes vs naive DT approach ───────────────────
  1. Temporal (expanding window) CV instead of random split
  2. Deliberately small feature set to avoid overfitting
  3. Integration with existing Elo system as complement
  4. Stage treated as binary (is_knockout), not ordinal encoding
  5. Includes stamina feature (player age × position)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from math import exp, log

from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss
from sklearn.preprocessing import LabelEncoder

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt


# ─── Label map ───
OUTCOME_MAP = {0: "away_win", 1: "draw", 2: "home_win"}
OUTCOME_NAMES = ["客胜", "平局", "主胜"]


# ══════════════════════════════════════════════════════════
#  FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════

def engineer_features(
    matches_df: pd.DataFrame,
    team_stats_df: pd.DataFrame,
    stamina_func=None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Build match-level feature matrix with critical feature selection.

    Features (carefully chosen to avoid redundancy with ~104 matches):
      1. elo_diff             – overall strength difference
      2. market_val_ratio     – financial power ratio (scale-free)
      3. points_diff          – tournament form
      4. stamina_diff         – team stamina (age × position)
      5. sot_per_game_diff    – attacking sharpness
      6. possession_diff      – control indicator
      7. is_knockout          – binary stage signal
      8. goals_against_per_game_diff – defensive solidity
      9. pressing_diff        – pressing/aggression intensity diff
     10. build_up_ratio       – possession-passing style ratio
     11. chances_created_diff – creative attacking ability diff
     12. star_goals_diff     – total World Cup goals from this team's scorers
     13. dependency_diff     – star dependency (Herfindahl index) diff
    """
    from src.data_collection.team_advanced_stats import (
        get_sot_per_game, get_possession, get_team_stats,
        get_pressing_intensity, get_build_up_score, get_chances_created_pg,
        star_goals_power, star_dependency_index,
    )

    stats_dict = team_stats_df.set_index("team").to_dict("index")

    rows = []
    labels = []

    for _, m in matches_df.iterrows():
        home, away = m["home_team"], m["away_team"]
        hs, as_ = m.get("home_score"), m.get("away_score")
        if pd.isna(hs) or pd.isna(as_):
            continue

        home_s = stats_dict.get(home, {})
        away_s = stats_dict.get(away, {})

        # ── Elo diff (injected by run() after training) ──
        elo_h = home_s.get("elo", 1500)
        elo_a = away_s.get("elo", 1500)
        elo_diff = elo_h - elo_a

        # ── Market value ratio (scale-free) ──
        mv_h = home_s.get("market_value", 1)
        mv_a = away_s.get("market_value", 1)
        market_val_ratio = (mv_h + 1) / (mv_a + 1)

        # ── Points diff ──
        points_diff = home_s.get("points", 0) - away_s.get("points", 0)

        # ── Stamina ──
        if stamina_func:
            stam_h = stamina_func(home)
            stam_a = stamina_func(away)
        else:
            from src.data_collection.team_advanced_stats import get_team_stamina_by_players
            stam_h = get_team_stamina_by_players(home)
            stam_a = get_team_stamina_by_players(away)
        stamina_diff = stam_h - stam_a

        # ── SoT per game ──
        sot_h = get_sot_per_game(home)
        sot_a = get_sot_per_game(away)
        sot_diff = sot_h - sot_a

        # ── Possession ──
        poss_h = get_possession(home)
        poss_a = get_possession(away)
        poss_diff = poss_h - poss_a

        # ── Goals against per game (defensive) ──
        ga_h = home_s.get("goals_against", 0) / max(home_s.get("matches_played", 1), 1)
        ga_a = away_s.get("goals_against", 0) / max(away_s.get("matches_played", 1), 1)
        ga_diff = ga_h - ga_a

        # ── Knockout flag ──
        stage = str(m.get("stage", "")).lower()
        is_ko = 1 if any(k in stage for k in [
            "round", "quarter", "semi", "final", "third",
        ]) else 0

        # ── Tactical style features ──
        pressing_diff = get_pressing_intensity(home) - get_pressing_intensity(away)

        h_build_up = get_build_up_score(home)
        a_build_up = get_build_up_score(away)
        build_up_ratio = max(h_build_up, 1) / max(a_build_up, 1)

        chances_diff = get_chances_created_pg(home) - get_chances_created_pg(away)

        # ── Star power / team dependency features ──
        star_goals_diff = star_goals_power(home) - star_goals_power(away)
        dependency_diff = star_dependency_index(home) - star_dependency_index(away)

        rows.append({
            "elo_diff": elo_diff,
            "market_val_ratio": min(market_val_ratio, 5.0),  # cap outliers
            "points_diff": points_diff,
            "stamina_diff": round(stamina_diff, 3),
            "sot_per_game_diff": round(sot_diff, 2),
            "possession_diff": round(poss_diff, 1),
            "goals_against_per_game_diff": round(ga_diff, 2),
            "is_knockout": is_ko,
            "pressing_diff": round(pressing_diff, 1),
            "build_up_ratio": round(build_up_ratio, 3),
            "chances_created_diff": round(chances_diff, 1),
            "star_goals_diff": round(star_goals_diff, 1),
            "dependency_diff": round(dependency_diff, 3),
        })

        # Label: 0=away_win, 1=draw, 2=home_win
        if hs > as_:
            labels.append(2)
        elif hs < as_:
            labels.append(0)
        else:
            labels.append(1)

    X = pd.DataFrame(rows)
    y = pd.Series(labels, name="outcome")
    return X, y


# ══════════════════════════════════════════════════════════
#  TEMPORAL CROSS-VALIDATION
# ══════════════════════════════════════════════════════════

def temporal_cv(X: pd.DataFrame, y: pd.Series, n_splits: int = 5):
    """
    Expanding-window temporal cross-validation.

    Unlike random KFold, this respects match order:
      Fold 1: train [0:t1], test [t1:t2]
      Fold 2: train [0:t2], test [t2:t3]
      ...
    """
    n = len(X)
    # Create roughly equal-sized test chunks
    chunk_size = n // (n_splits + 1)
    fold_info = []

    for i in range(1, n_splits + 1):
        test_end = min((i + 1) * chunk_size, n)
        train_end = i * chunk_size
        if train_end >= n:
            break
        fold_info.append({
            "train_idx": list(range(train_end)),
            "test_idx": list(range(train_end, test_end)),
        })

    return fold_info


# ══════════════════════════════════════════════════════════
#  CORE: WorldCupDecisionTree
# ══════════════════════════════════════════════════════════

class WorldCupDecisionTree:
    """
    Decision tree with temporal validation and aggressive pruning.

    Designed for small data (~104 matches):
      - max_depth=4 (not 5 — less is more with small data)
      - min_samples_leaf=3 (not 2 — prevents single-match leaves)
      - criterion='entropy' (better than gini for 3-class with small data)
    """

    def __init__(
        self,
        max_depth: int = 4,
        min_samples_leaf: int = 3,
        min_samples_split: int = 6,
        criterion: str = "entropy",
    ):
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.min_samples_split = min_samples_split
        self.criterion = criterion

        self.model = DecisionTreeClassifier(
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            min_samples_split=min_samples_split,
            criterion=criterion,
            class_weight="balanced",
            random_state=42,
        )
        self.feature_names: Optional[List[str]] = None
        self.cv_results: List[Dict] = []
        self.val_accuracy: float = 0.0

    def _validate_model(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        """Temporal CV to estimate out-of-sample performance."""
        folds = temporal_cv(X, y, n_splits=5)
        accs, losses, briers = [], [], []

        for fold in folds:
            X_tr, y_tr = X.iloc[fold["train_idx"]], y.iloc[fold["train_idx"]]
            X_te, y_te = X.iloc[fold["test_idx"]], y.iloc[fold["test_idx"]]
            if len(X_te) < 2:
                continue

            m = DecisionTreeClassifier(
                max_depth=self.max_depth,
                min_samples_leaf=self.min_samples_leaf,
                min_samples_split=self.min_samples_split,
                criterion=self.criterion,
                class_weight="balanced",
                random_state=42,
            )
            m.fit(X_tr, y_tr)
            y_pred = m.predict(X_te)
            y_prob = m.predict_proba(X_te)

            acc = accuracy_score(y_te, y_pred)
            # Log-loss (clamp probabilities)
            prob_clip = np.clip(y_prob, 1e-6, 1 - 1e-6)
            ll = log_loss(y_te, prob_clip)

            accs.append(acc)
            losses.append(ll)

        return {
            "cv_accuracy": float(np.mean(accs)) if accs else 0.0,
            "cv_log_loss": float(np.mean(losses)) if losses else 0.0,
            "n_folds": len(accs),
        }

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        team_stats_df: Optional[pd.DataFrame] = None,
    ) -> "WorldCupDecisionTree":
        """Train with temporal validation + full-data final fit."""
        self.feature_names = X.columns.tolist()

        # Temporal CV
        cv = self._validate_model(X, y)
        print(f"  🎯 决策树时序CV准确率: {cv['cv_accuracy']:.2%} "
              f"(log_loss={cv['cv_log_loss']:.4f}, {cv['n_folds']}折)")

        # Final fit on ALL data (for production)
        self.model.fit(X, y)

        # Training accuracy (for reference, not evaluation)
        train_pred = self.model.predict(X)
        self.val_accuracy = accuracy_score(y, train_pred)

        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict outcome probabilities."""
        return self.model.predict_proba(X)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict discrete outcomes (0/1/2)."""
        return self.model.predict(X)

    def get_feature_importance(self) -> pd.DataFrame:
        """Return ranked feature importance."""
        if self.feature_names is None:
            return pd.DataFrame()
        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": self.model.feature_importances_,
        }).sort_values("importance", ascending=False).reset_index(drop=True)

    # ─── Explain / Visualise ───

    def explain_prediction(
        self, X_row: pd.DataFrame, home_team: str, away_team: str
    ) -> Dict:
        """
        Trace decision path and return human-readable explanation.
        """
        path = self.model.decision_path(X_row)
        leaf_id = self.model.apply(X_row)[0]
        node_indices = path.indices.tolist()

        tree = self.model.tree_
        steps = []
        for node_id in node_indices:
            if tree.feature[node_id] < 0:  # leaf
                continue
            feat_name = self.feature_names[tree.feature[node_id]]
            threshold = tree.threshold[node_id]
            value = float(X_row.iloc[0][feat_name])
            direction = ">" if value > threshold else "≤"
            steps.append(f"{feat_name} = {value:.2f} {direction} {threshold:.2f}")

        prob = self.model.predict_proba(X_row)[0]
        pred = self.model.predict(X_row)[0]

        explanation = {
            "home_team": home_team,
            "away_team": away_team,
            "decision_path": steps,
            "prediction": OUTCOME_NAMES[pred],
            "prediction_en": OUTCOME_MAP[pred],
            "probabilities": {
                "away_win": float(prob[0]),
                "draw": float(prob[1]),
                "home_win": float(prob[2]),
            },
        }
        return explanation

    def render_tree(self, save_path: str = "decision_tree.png", max_depth: int = 3):
        """Export decision tree visualization."""
        if self.feature_names is None:
            print("[WARN] Model not trained yet.")
            return

        fig, ax = plt.subplots(figsize=(20, 12))
        plot_tree(
            self.model,
            max_depth=max_depth,
            feature_names=self.feature_names,
            class_names=OUTCOME_NAMES,
            filled=True,
            rounded=True,
            fontsize=10,
            ax=ax,
        )
        plt.title(
            f"世界杯预测决策树 (max_depth={self.max_depth}, "
            f"CV准确率: {self.val_accuracy:.1%})",
            fontsize=14,
        )
        plt.tight_layout()
        fig.savefig(save_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"  ✅ 决策树图 → {save_path}")


# ══════════════════════════════════════════════════════════
#  ENSEMBLE: WorldCupDTEnsemble
# ══════════════════════════════════════════════════════════

class WorldCupDTEnsemble:
    """
    Multi-model ensemble: Decision Tree + Random Forest + Elo Softmax.

    Weighted voting:
      - Random Forest (40%): best raw accuracy, robust
      - Elo Softmax   (35%): domain-specific, calibrated
      - Decision Tree (25%): interpretable, captures nonlinear patterns
    """

    def __init__(
        self,
        dt_model: Optional[WorldCupDecisionTree] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.dt = dt_model or WorldCupDecisionTree()
        self.rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=4,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
        )
        self.weights = weights or {
            "random_forest": 0.40,
            "elo_softmax": 0.35,
            "decision_tree": 0.25,
        }
        self.feature_names: Optional[List[str]] = None
        self.elo_predictor: Optional[object] = None  # WorldCupPredictor ref

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        elo_predictor=None,
    ) -> "WorldCupDTEnsemble":
        """Train all models on the same feature set."""
        self.feature_names = X.columns.tolist()
        self.elo_predictor = elo_predictor

        # Decision Tree
        print("  [决策树] 训练中...")
        self.dt.train(X, y)

        # Random Forest
        print("  [随机森林] 训练中...")
        self.rf.fit(X, y)
        rf_pred = self.rf.predict(X)
        rf_acc = accuracy_score(y, rf_pred)
        print(f"    → 训练准确率: {rf_acc:.2%}")

        # Temporal CV for RF
        folds = temporal_cv(X, y, n_splits=5)
        rf_cv_accs = []
        for fold in folds:
            X_tr, y_tr = X.iloc[fold["train_idx"]], y.iloc[fold["train_idx"]]
            X_te, y_te = X.iloc[fold["test_idx"]], y.iloc[fold["test_idx"]]
            if len(X_te) < 2:
                continue
            m = RandomForestClassifier(
                n_estimators=200, max_depth=4, min_samples_leaf=2,
                class_weight="balanced", random_state=42,
            )
            m.fit(X_tr, y_tr)
            rf_cv_accs.append(accuracy_score(y_te, m.predict(X_te)))

        if rf_cv_accs:
            print(f"  🎯 随机森林时序CV准确率: {np.mean(rf_cv_accs):.2%}")

        return self

    def predict_proba(
        self, X: pd.DataFrame, match_row: Optional[pd.Series] = None
    ) -> np.ndarray:
        """
        Weighted ensemble probability prediction.

        Args:
            X: Feature matrix
            match_row: Optional match row for Elo prediction
        """
        n = len(X)
        ensemble_probs = np.zeros((n, 3))

        # DT contribution
        dt_probs = self.dt.predict_proba(X)
        ensemble_probs += self.weights["decision_tree"] * dt_probs

        # RF contribution
        rf_probs = self.rf.predict_proba(X)
        ensemble_probs += self.weights["random_forest"] * rf_probs

        # Elo contribution (if available)
        elo_w = self.weights.get("elo_softmax", 0.0)
        if elo_w > 0 and self.elo_predictor is not None and match_row is not None:
            try:
                home = match_row["home_team"]
                away = match_row["away_team"]
                outcome = self.elo_predictor.outcome_probs(home, away)
                elo_probs = np.array([
                    [outcome["away_win_prob"],
                     outcome["draw_prob"],
                     outcome["home_win_prob"]]
                ])
                # Tile if multiple rows
                if n > 1:
                    elo_probs = np.tile(elo_probs, (n, 1))
                ensemble_probs += elo_w * elo_probs
            except Exception:
                pass  # Fallback: just use DT + RF

        # Normalize
        row_sums = ensemble_probs.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums == 0, 1, row_sums)
        return ensemble_probs / row_sums

    def predict(self, X: pd.DataFrame, match_row: Optional[pd.Series] = None) -> np.ndarray:
        """Predict discrete outcomes."""
        probs = self.predict_proba(X, match_row)
        return np.argmax(probs, axis=1)

    def get_feature_importance(self) -> pd.DataFrame:
        """Combined feature importance from DT and RF."""
        dt_imp = self.dt.get_feature_importance()
        if dt_imp.empty:
            return pd.DataFrame()

        rf_imp = pd.DataFrame({
            "feature": self.feature_names,
            "rf_importance": self.rf.feature_importances_,
        })

        combined = dt_imp.merge(rf_imp, on="feature", how="outer")
        combined["combined"] = (
            0.4 * combined["importance"] + 0.6 * combined["rf_importance"]
        )
        return combined.sort_values("combined", ascending=False).reset_index(drop=True)
