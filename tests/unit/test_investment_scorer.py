"""Unit tests for ml/investment_scoring/scorer.py."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.investment_scoring.scorer import (
    InvestmentResult,
    InvestmentScorer,
    ScoreComponents,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def scorer() -> InvestmentScorer:
    return InvestmentScorer()


@pytest.fixture
def trending_up() -> pd.Series:
    """Smooth 1-year uptrend: 50 → 80."""
    dates = pd.bdate_range("2025-01-01", periods=252)
    return pd.Series(np.linspace(50.0, 80.0, 252), index=dates)


@pytest.fixture
def trending_down() -> pd.Series:
    """Smooth 1-year downtrend: 80 → 50."""
    dates = pd.bdate_range("2025-01-01", periods=252)
    return pd.Series(np.linspace(80.0, 50.0, 252), index=dates)


@pytest.fixture
def flat() -> pd.Series:
    dates = pd.bdate_range("2025-01-01", periods=252)
    return pd.Series([100.0] * 252, index=dates)


@pytest.fixture
def high_vol() -> pd.Series:
    """Prices with ~60% annual volatility (4% daily)."""
    np.random.seed(0)
    n = 252
    dates = pd.bdate_range("2025-01-01", periods=n)
    rets = np.random.normal(0, 0.04, n)
    prices = 100 * np.cumprod(1 + rets)
    return pd.Series(prices, index=dates)


@pytest.fixture
def volumes(trending_up: pd.Series) -> pd.Series:
    np.random.seed(1)
    return pd.Series(
        np.random.randint(1_000_000, 5_000_000, len(trending_up)),
        index=trending_up.index,
    )


# ── ScoreComponents ───────────────────────────────────────────────────────────

class TestScoreComponents:
    def test_all_hundred_composite_is_hundred(self):
        comp = ScoreComponents(100, 100, 100, 100, 100)
        assert comp.composite == pytest.approx(100.0, abs=0.01)

    def test_all_zero_composite_is_zero(self):
        comp = ScoreComponents(0, 0, 0, 0, 0)
        assert comp.composite == pytest.approx(0.0, abs=0.01)

    def test_composite_matches_manual_weights(self):
        comp = ScoreComponents(momentum=80, trend=60, risk=70, rsi=50, volume=40)
        expected = 80 * 0.30 + 60 * 0.30 + 70 * 0.20 + 50 * 0.15 + 40 * 0.05
        assert comp.composite == pytest.approx(expected, abs=0.01)


# ── InvestmentScorer.score — basic contract ───────────────────────────────────

class TestScorerBasic:
    def test_returns_investment_result(self, scorer, trending_up):
        result = scorer.score(trending_up)
        assert isinstance(result, InvestmentResult)

    def test_score_is_between_0_and_100(self, scorer, trending_up):
        result = scorer.score(trending_up)
        assert 0.0 <= result.score <= 100.0

    def test_signal_is_valid_string(self, scorer, trending_up):
        valid = {"Strong Buy", "Buy", "Neutral", "Sell", "Strong Sell"}
        assert scorer.score(trending_up).signal in valid

    def test_components_present(self, scorer, trending_up):
        comp = scorer.score(trending_up).components
        assert isinstance(comp, ScoreComponents)
        for attr in ("momentum", "trend", "risk", "rsi", "volume"):
            assert isinstance(getattr(comp, attr), float)

    def test_financial_fields_are_floats(self, scorer, trending_up):
        r = scorer.score(trending_up)
        assert isinstance(r.total_return_1y, float)
        assert isinstance(r.volatility_annual, float)
        assert isinstance(r.sharpe_ratio, float)
        assert isinstance(r.max_drawdown, float)

    def test_insufficient_data_returns_neutral_fifty(self, scorer):
        """Fewer than 20 data points → default neutral result."""
        prices = pd.Series([100.0] * 10)
        result = scorer.score(prices)
        assert result.score == 50.0
        assert result.signal == "Neutral"

    def test_without_volumes_volume_component_is_fifty(self, scorer, trending_up):
        assert scorer.score(trending_up, volumes=None).components.volume == 50.0

    def test_with_volumes_volume_component_changes(self, scorer, trending_up, volumes):
        result = scorer.score(trending_up, volumes=volumes)
        assert result.components.volume != 50.0


# ── Return calculations ───────────────────────────────────────────────────────

class TestReturnCalculations:
    def test_uptrend_positive_total_return(self, scorer, trending_up):
        assert scorer.score(trending_up).total_return_1y > 0

    def test_downtrend_negative_total_return(self, scorer, trending_down):
        assert scorer.score(trending_down).total_return_1y < 0

    def test_max_drawdown_non_positive(self, scorer, trending_up):
        assert scorer.score(trending_up).max_drawdown <= 0

    def test_max_drawdown_more_negative_on_downtrend(self, scorer, trending_up, trending_down):
        dd_up = scorer.score(trending_up).max_drawdown
        dd_down = scorer.score(trending_down).max_drawdown
        assert dd_down < dd_up

    def test_volatility_higher_on_noisy_prices(self, scorer, flat, high_vol):
        vol_flat = scorer.score(flat).volatility_annual
        vol_noisy = scorer.score(high_vol).volatility_annual
        assert vol_noisy > vol_flat


# ── Signal mapping ────────────────────────────────────────────────────────────

class TestSignalMapping:
    @pytest.mark.parametrize("score,expected", [
        (80.0, "Strong Buy"),
        (75.0, "Strong Buy"),
        (74.9, "Buy"),
        (60.0, "Buy"),
        (59.9, "Neutral"),
        (40.0, "Neutral"),
        (39.9, "Sell"),
        (25.0, "Sell"),
        (24.9, "Strong Sell"),
        (0.0,  "Strong Sell"),
    ])
    def test_boundary_signals(self, score, expected):
        assert InvestmentScorer._to_signal(score) == expected


# ── Relative score ordering ───────────────────────────────────────────────────

class TestRelativeScores:
    def test_uptrend_scores_higher_than_downtrend(self, scorer, trending_up, trending_down):
        assert scorer.score(trending_up).score > scorer.score(trending_down).score

    def test_trend_component_higher_for_uptrend(self, scorer, trending_up, trending_down):
        trend_up = scorer.score(trending_up).components.trend
        trend_dn = scorer.score(trending_down).components.trend
        assert trend_up > trend_dn

    def test_high_vol_lower_risk_component(self, scorer, flat, high_vol):
        risk_flat = scorer.score(flat).components.risk
        risk_noisy = scorer.score(high_vol).components.risk
        assert risk_noisy < risk_flat


# ── score_multiple ────────────────────────────────────────────────────────────

class TestScoreMultiple:
    def test_sorted_descending_by_score(self, scorer, trending_up, trending_down):
        results = scorer.score_multiple({"UP": trending_up, "DOWN": trending_down})
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_ticker_assigned_correctly(self, scorer, trending_up):
        results = scorer.score_multiple({"PETR4": trending_up})
        assert results[0].ticker == "PETR4"

    def test_empty_dict_returns_empty_list(self, scorer):
        assert scorer.score_multiple({}) == []

    def test_all_tickers_present(self, scorer, trending_up, trending_down):
        results = scorer.score_multiple({"A": trending_up, "B": trending_down})
        tickers = {r.ticker for r in results}
        assert tickers == {"A", "B"}


# ── Custom weight normalisation ───────────────────────────────────────────────

class TestCustomWeights:
    def test_weights_normalised_to_one(self):
        s = InvestmentScorer(momentum_weight=2, trend_weight=1, risk_weight=1, rsi_weight=1, volume_weight=0)
        total = s._w_momentum + s._w_trend + s._w_risk + s._w_rsi + s._w_volume
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_high_momentum_weight_rewards_uptrend_more(self):
        s_default = InvestmentScorer()
        s_momentum = InvestmentScorer(momentum_weight=0.90, trend_weight=0.025,
                                      risk_weight=0.025, rsi_weight=0.025, volume_weight=0.025)
        dates = pd.bdate_range("2025-01-01", periods=252)
        strong_uptrend = pd.Series(np.linspace(20.0, 100.0, 252), index=dates)

        momentum_score = s_momentum.score(strong_uptrend).components.momentum
        assert momentum_score > 60  # strong uptrend should score well on momentum
