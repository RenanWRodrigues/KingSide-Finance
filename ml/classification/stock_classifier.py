from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import mlflow
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler


LABELS = {0: "underperform", 1: "neutral", 2: "outperform"}


@dataclass
class ClassifierConfig:
    n_estimators: int = 300
    max_depth: int = 8
    min_samples_leaf: int = 20
    n_jobs: int = -1
    random_state: int = 42
    cv_folds: int = 5
    threshold_outperform: float = 0.05
    threshold_underperform: float = -0.05
    horizon_days: int = 21


@dataclass
class ClassificationResult:
    ticker: str
    label: str
    probability: dict[str, float]
    feature_importance: dict[str, float]
    metricas: dict[str, float]
    mlflow_run_id: str | None = None


class StockClassifier:
    """
    Multi-class stock performance classifier.
    Labels: underperform / neutral / outperform over a N-day horizon.

    Features: technical indicators + fundamental ratios.
    Model: Random Forest with cross-validation.
    """

    def __init__(self, config: ClassifierConfig | None = None) -> None:
        self.config = config or ClassifierConfig()
        self.model = RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            min_samples_leaf=self.config.min_samples_leaf,
            n_jobs=self.config.n_jobs,
            random_state=self.config.random_state,
            class_weight="balanced",
        )
        self.scaler = StandardScaler()
        self._feature_names: list[str] = []

    def build_features(self, prices: pd.DataFrame) -> pd.DataFrame:
        df = prices.copy().sort_index()
        df["ret_1d"] = df["close"].pct_change(1)
        df["ret_5d"] = df["close"].pct_change(5)
        df["ret_21d"] = df["close"].pct_change(21)
        df["ret_63d"] = df["close"].pct_change(63)
        df["vol_21d"] = df["ret_1d"].rolling(21).std() * np.sqrt(252)
        df["vol_63d"] = df["ret_1d"].rolling(63).std() * np.sqrt(252)
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        df["price_to_sma20"] = df["close"] / df["sma_20"] - 1
        df["price_to_sma50"] = df["close"] / df["sma_50"] - 1
        df["rsi"] = self._compute_rsi(df["close"])
        df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()
        df["high_low_range"] = (df["high"] - df["low"]) / df["close"]
        df = df.dropna()
        return df

    def _compute_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(window).mean()
        loss = (-delta.clip(upper=0)).rolling(window).mean()
        rs = gain / loss.replace(0, float("inf"))
        return 100 - 100 / (1 + rs)

    def create_labels(self, df: pd.DataFrame) -> pd.Series:
        future_ret = df["close"].pct_change(self.config.horizon_days).shift(-self.config.horizon_days)
        labels = pd.cut(
            future_ret,
            bins=[-float("inf"), self.config.threshold_underperform, self.config.threshold_outperform, float("inf")],
            labels=[0, 1, 2],
        )
        return labels.astype(int)

    def train(self, tickers_data: dict[str, pd.DataFrame]) -> dict[str, Any]:
        all_X, all_y = [], []
        for ticker, df in tickers_data.items():
            features = self.build_features(df)
            feature_cols = [c for c in features.columns if c not in ["open", "high", "low", "close", "volume"]]
            labels = self.create_labels(features)
            mask = labels.notna()
            X = features.loc[mask, feature_cols]
            y = labels[mask]
            all_X.append(X)
            all_y.append(y)

        X_all = pd.concat(all_X)
        y_all = pd.concat(all_y)
        self._feature_names = list(X_all.columns)

        X_scaled = self.scaler.fit_transform(X_all)
        cv = StratifiedKFold(n_splits=self.config.cv_folds, shuffle=True, random_state=42)
        cv_scores = cross_val_score(self.model, X_scaled, y_all, cv=cv, scoring="f1_macro", n_jobs=-1)
        self.model.fit(X_scaled, y_all)

        metricas = {
            "cv_f1_macro_mean": round(float(cv_scores.mean()), 4),
            "cv_f1_macro_std": round(float(cv_scores.std()), 4),
        }
        logger.info(f"Classifier trained on {len(X_all)} samples. CV F1: {metricas}")
        return metricas

    def predict(self, prices: pd.DataFrame) -> ClassificationResult:
        features = self.build_features(prices)
        feature_cols = self._feature_names or [
            c for c in features.columns if c not in ["open", "high", "low", "close", "volume"]
        ]
        X = features.tail(1)[feature_cols]
        X_scaled = self.scaler.transform(X)
        pred = self.model.predict(X_scaled)[0]
        proba = self.model.predict_proba(X_scaled)[0]
        importance = dict(zip(self._feature_names, self.model.feature_importances_))
        top_importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10])

        return ClassificationResult(
            ticker="",
            label=LABELS[int(pred)],
            probability={LABELS[i]: round(float(p), 4) for i, p in enumerate(proba)},
            feature_importance=top_importance,
            metricas={},
        )
