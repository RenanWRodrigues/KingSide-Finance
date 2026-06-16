"""Finance — Proprietary Investment Scoring Engine."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class ScoreComponents:
    momentum: float = 0.0
    trend: float = 0.0
    risk: float = 0.0
    rsi: float = 0.0
    volume: float = 0.0

    @property
    def composite(self) -> float:
        return (
            self.momentum * 0.30
            + self.trend * 0.30
            + self.risk * 0.20
            + self.rsi * 0.15
            + self.volume * 0.05
        )


@dataclass
class InvestmentResult:
    ticker: str
    score: float
    signal: str
    components: ScoreComponents
    total_return_1y: float = 0.0
    volatility_annual: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    beta: float = 1.0
    metadata: dict = field(default_factory=dict)


_SIGNAL_MAP = [
    (75, "Strong Buy"),
    (60, "Buy"),
    (40, "Neutral"),
    (25, "Sell"),
    (0, "Strong Sell"),
]

RISK_FREE_ANNUAL = 0.1475  # SELIC ~14,75% a.a.


class InvestmentScorer:
    """Multi-factor quantitative scoring engine for B3 equities.

    Combines momentum, trend, risk, and technical signals into a
    proprietary 0–100 score using walk-forward compatible calculations.
    """

    def __init__(
        self,
        momentum_weight: float = 0.30,
        trend_weight: float = 0.30,
        risk_weight: float = 0.20,
        rsi_weight: float = 0.15,
        volume_weight: float = 0.05,
    ) -> None:
        total = momentum_weight + trend_weight + \
            risk_weight + rsi_weight + volume_weight
        self._w_momentum = momentum_weight / total
        self._w_trend = trend_weight / total
        self._w_risk = risk_weight / total
        self._w_rsi = rsi_weight / total
        self._w_volume = volume_weight / total

    def score(self, prices: pd.Series, volumes: pd.Series | None = None) -> InvestmentResult:
        """Compute investment score for a price series.

        Args:
            prices: Daily close price series, chronologically ordered.
            volumes: Optional daily volume series.

        Returns:
            InvestmentResult with score, signal, and components.
        """
        closes = prices.dropna().values.astype(float)
        if len(closes) < 20:
            return InvestmentResult(
                ticker="",
                score=50.0,
                signal="Neutral",
                components=ScoreComponents(50, 50, 50, 50, 50),
            )

        returns = np.diff(closes) / closes[:-1]
        components = ScoreComponents(
            momentum=self._momentum_score(closes),
            trend=self._trend_score(closes),
            risk=self._risk_score(returns),
            rsi=self._rsi_score(closes),
            volume=self._volume_score(
                volumes) if volumes is not None else 50.0,
        )

        composite = (
            components.momentum * self._w_momentum
            + components.trend * self._w_trend
            + components.risk * self._w_risk
            + components.rsi * self._w_rsi
            + components.volume * self._w_volume
        )
        composite = float(np.clip(composite, 0, 100))

        total_return = (closes[-1] / closes[0] - 1) * 100
        vol_annual = float(np.std(returns, ddof=1) * math.sqrt(252) * 100)
        rf_daily = RISK_FREE_ANNUAL / 252
        sharpe = float((np.mean(returns) - rf_daily) /
                       np.std(returns, ddof=1) * math.sqrt(252))

        # Max drawdown
        peak = np.maximum.accumulate(closes)
        drawdowns = (closes - peak) / peak
        max_dd = float(np.min(drawdowns) * 100)

        return InvestmentResult(
            ticker="",
            score=round(composite, 2),
            signal=self._to_signal(composite),
            components=components,
            total_return_1y=round(total_return, 2),
            volatility_annual=round(vol_annual, 2),
            sharpe_ratio=round(sharpe, 3),
            max_drawdown=round(max_dd, 2),
        )

    def score_multiple(
        self, price_dict: dict[str, pd.Series]
    ) -> list[InvestmentResult]:
        """Score multiple tickers and return sorted by score descending."""
        results = []
        for ticker, prices in price_dict.items():
            result = self.score(prices)
            result.ticker = ticker
            results.append(result)
        return sorted(results, key=lambda r: r.score, reverse=True)

    # ── Internal factor computations ─────────────────────────────

    def _momentum_score(self, closes: np.ndarray) -> float:
        n = len(closes)
        ret_1m = (closes[-1] / closes[max(0, n-21)] - 1) * \
            100 if n >= 21 else 0
        ret_3m = (closes[-1] / closes[max(0, n-63)] - 1) * \
            100 if n >= 63 else 0
        ret_6m = (closes[-1] / closes[max(0, n-126)] - 1) * \
            100 if n >= 126 else 0
        ret_1y = (closes[-1] / closes[0] - 1) * 100
        momentum_raw = ret_1m * 0.15 + ret_3m * 0.25 + ret_6m * 0.25 + ret_1y * 0.35
        return float(np.clip(50 + momentum_raw * 0.8, 0, 100))

    def _trend_score(self, closes: np.ndarray) -> float:
        n = len(closes)
        price = closes[-1]
        score = 50.0
        if n >= 20:
            ma20 = np.mean(closes[-20:])
            score += 15 if price > ma20 else -15
        if n >= 50:
            ma50 = np.mean(closes[-50:])
            score += 20 if price > ma50 else -20
        if n >= 200:
            ma200 = np.mean(closes[-200:])
            score += 15 if price > ma200 else -15
        if n >= 50:
            ma20 = np.mean(closes[-20:])
            ma50 = np.mean(closes[-50:])
            score += 10 if ma20 > ma50 else -10
        return float(np.clip(score, 0, 100))

    def _risk_score(self, returns: np.ndarray) -> float:
        if len(returns) < 5:
            return 50.0
        vol = np.std(returns, ddof=1) * math.sqrt(252) * 100
        # Ideal vol zone is 15–30% annual; penalize extremes
        if vol < 10:
            score = 70.0
        elif vol <= 25:
            score = 100 - (vol - 10) * 2
        else:
            score = max(0, 70 - (vol - 25) * 2)
        return float(np.clip(score, 0, 100))

    def _rsi_score(self, closes: np.ndarray) -> float:
        if len(closes) < 15:
            return 50.0
        diffs = np.diff(closes)
        gains = np.where(diffs > 0, diffs, 0)
        losses = np.where(diffs < 0, -diffs, 0)
        avg_gain = np.mean(gains[-14:])
        avg_loss = np.mean(losses[-14:]) or 1e-9
        rs = avg_gain / avg_loss
        rsi = 100 - 100 / (1 + rs)
        # Best RSI zone: 40-65 (mild upward momentum, not overbought)
        if 40 <= rsi <= 65:
            score = 75 + (rsi - 40) * 1.0
        elif rsi > 65:
            score = 90 - (rsi - 65) * 2.5
        else:
            score = 75 - (40 - rsi) * 2.0
        return float(np.clip(score, 0, 100))

    def _volume_score(self, volumes: pd.Series) -> float:
        vols = volumes.dropna().values[-30:]
        if len(vols) < 10:
            return 50.0
        recent_avg = np.mean(vols[-5:])
        base_avg = np.mean(vols[:-5]) if len(vols) > 5 else recent_avg
        if base_avg == 0:
            return 50.0
        ratio = recent_avg / base_avg
        score = 50 + (ratio - 1) * 30
        return float(np.clip(score, 0, 100))

    @staticmethod
    def _to_signal(score: float) -> str:
        for threshold, label in _SIGNAL_MAP:
            if score >= threshold:
                return label
        return "Strong Sell"
