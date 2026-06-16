from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


@dataclass
class AnomalyResult:
    ticker: str
    total_points: int
    anomaly_count: int
    anomaly_rate: float
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    severity_distribution: dict[str, int] = field(default_factory=dict)


class MarketAnomalyDetector:
    """
    Isolation Forest-based anomaly detection for market data.
    Detects unusual price movements, volume spikes, and volatility regimes.
    """

    def __init__(
        self,
        contamination: float = 0.02,
        n_estimators: int = 200,
        random_state: int = 42,
    ) -> None:
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1,
        )
        self.scaler = StandardScaler()

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame(index=df.index)
        close = df["close"] if "close" in df.columns else df["fechamento"]
        volume = df["volume"] if "volume" in df.columns else df.get("volume", pd.Series(1, index=df.index))

        features["ret_1d"] = close.pct_change(1)
        features["ret_5d"] = close.pct_change(5)
        features["vol_5d"] = features["ret_1d"].rolling(5).std()
        features["vol_21d"] = features["ret_1d"].rolling(21).std()
        features["vol_ratio"] = features["vol_5d"] / features["vol_21d"].replace(0, np.nan)
        features["volume_zscore"] = (volume - volume.rolling(21).mean()) / volume.rolling(21).std()
        features["price_range"] = (df.get("high", close) - df.get("low", close)) / close
        features["gap"] = close / close.shift(1).replace(0, np.nan) - 1

        return features.dropna()

    def fit_detect(self, ticker: str, df: pd.DataFrame) -> AnomalyResult:
        features = self.build_features(df)
        if len(features) < 50:
            raise ValueError(f"Insufficient data for anomaly detection on {ticker}")

        X = self.scaler.fit_transform(features)
        predictions = self.model.fit_predict(X)
        scores = self.model.score_samples(X)

        anomaly_mask = predictions == -1
        anomaly_indices = features.index[anomaly_mask]
        anomaly_scores = scores[anomaly_mask]

        anomalies = []
        for idx, score in zip(anomaly_indices, anomaly_scores):
            severity = "critical" if score < -0.2 else "high" if score < -0.1 else "medium"
            anomalies.append({
                "data": idx.date() if hasattr(idx, "date") else str(idx),
                "score": round(float(score), 4),
                "severity": severity,
                "features": {
                    col: round(float(features.loc[idx, col]), 4)
                    for col in features.columns
                },
            })

        anomalies.sort(key=lambda x: x["score"])
        severity_dist = {
            "critical": sum(1 for a in anomalies if a["severity"] == "critical"),
            "high": sum(1 for a in anomalies if a["severity"] == "high"),
            "medium": sum(1 for a in anomalies if a["severity"] == "medium"),
        }

        logger.info(
            f"Anomaly detection for {ticker}: {len(anomalies)}/{len(features)} anomalies "
            f"({len(anomalies)/len(features)*100:.1f}%)"
        )
        return AnomalyResult(
            ticker=ticker,
            total_points=len(features),
            anomaly_count=len(anomalies),
            anomaly_rate=round(len(anomalies) / len(features), 4),
            anomalies=anomalies,
            severity_distribution=severity_dist,
        )
