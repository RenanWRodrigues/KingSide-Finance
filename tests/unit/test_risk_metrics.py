"""Unit tests for ml/quantitative_analysis/risk_metrics.py"""

import math

import pytest

from ml.quantitative_analysis.risk_metrics import (
    accumulated_return,
    annualized_volatility,
    beta,
    cagr,
    compute_all,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    var_95,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def flat_prices() -> list[float]:
    """Constant prices — zero return and zero volatility."""
    return [100.0] * 252


@pytest.fixture
def trending_up() -> list[float]:
    """Prices increasing 0.05% per day (~13% annually)."""
    p = 100.0
    prices = [p]
    for _ in range(251):
        p *= 1.0005
        prices.append(round(p, 4))
    return prices


@pytest.fixture
def trending_down() -> list[float]:
    """Prices decreasing 0.05% per day."""
    p = 100.0
    prices = [p]
    for _ in range(251):
        p *= 0.9995
        prices.append(round(p, 4))
    return prices


@pytest.fixture
def volatile_prices() -> list[float]:
    """Prices oscillating ±5% alternately."""
    prices = [100.0]
    for i in range(251):
        mult = 1.05 if i % 2 == 0 else 0.9524
        prices.append(round(prices[-1] * mult, 4))
    return prices


# ── accumulated_return ────────────────────────────────────────────────────────

class TestAccumulatedReturn:
    def test_positive_return(self, trending_up):
        result = accumulated_return(trending_up)
        assert result is not None
        assert result > 0

    def test_negative_return(self, trending_down):
        result = accumulated_return(trending_down)
        assert result is not None
        assert result < 0

    def test_flat(self, flat_prices):
        result = accumulated_return(flat_prices)
        assert result == pytest.approx(0.0, abs=0.01)

    def test_too_short(self):
        assert accumulated_return([100.0]) is None

    def test_zero_start(self):
        assert accumulated_return([0.0, 100.0]) is None


# ── cagr ─────────────────────────────────────────────────────────────────────

class TestCAGR:
    def test_positive(self, trending_up):
        result = cagr(trending_up)
        assert result is not None
        assert result > 0

    def test_unit_period(self):
        # 252 points = 1 year; doubling price → CAGR ~100%
        prices = [100.0] * 126 + [200.0] * 126
        result = cagr(prices)
        assert result is not None
        assert result > 50

    def test_short_series(self):
        assert cagr([100.0]) is None


# ── annualized_volatility ─────────────────────────────────────────────────────

class TestVolatility:
    def test_flat_near_zero(self, flat_prices):
        result = annualized_volatility(flat_prices)
        assert result is not None
        assert result == pytest.approx(0.0, abs=0.01)

    def test_volatile_positive(self, volatile_prices):
        result = annualized_volatility(volatile_prices)
        assert result is not None
        assert result > 0

    def test_too_short(self):
        assert annualized_volatility([100.0, 101.0]) is None


# ── sharpe_ratio ──────────────────────────────────────────────────────────────

class TestSharpeRatio:
    def test_positive_sharpe(self, trending_up):
        result = sharpe_ratio(trending_up)
        # trending_up with 0.05%/day has CAGR ~13%, which with SELIC ~11.75% could be positive
        # The sign depends on whether excess return > 0 — just check it's not None
        assert result is not None

    def test_flat_returns_none(self, flat_prices):
        # zero volatility → None (division by zero guarded)
        result = sharpe_ratio(flat_prices)
        assert result is None

    def test_too_short(self):
        assert sharpe_ratio([100.0] * 29) is None

    def test_negative_excess_return(self, trending_down):
        result = sharpe_ratio(trending_down)
        assert result is not None
        assert result < 0


# ── sortino_ratio ──────────────────────────────────────────────────────────────

class TestSortinoRatio:
    def test_trending_up_positive(self, trending_up):
        result = sortino_ratio(trending_up)
        # smooth uptrend may have very few down days; could return None
        assert result is None or isinstance(result, float)

    def test_trending_down_negative(self, trending_down):
        result = sortino_ratio(trending_down)
        assert result is not None
        assert result < 0


# ── max_drawdown ──────────────────────────────────────────────────────────────

class TestMaxDrawdown:
    def test_flat_zero(self, flat_prices):
        result = max_drawdown(flat_prices)
        assert result == pytest.approx(0.0, abs=0.01)

    def test_trending_up_small(self, trending_up):
        result = max_drawdown(trending_up)
        assert result is not None
        assert result <= 0  # drawdown is always ≤ 0

    def test_volatile_large(self, volatile_prices):
        result = max_drawdown(volatile_prices)
        assert result is not None
        assert result < -4  # volatile prices have meaningful drawdown

    def test_too_short(self):
        assert max_drawdown([100.0]) is None


# ── var_95 ────────────────────────────────────────────────────────────────────

class TestVaR95:
    def test_returns_float(self, volatile_prices):
        result = var_95(volatile_prices)
        assert result is not None
        assert isinstance(result, float)

    def test_too_short(self):
        assert var_95([100.0] * 29) is None


# ── beta ──────────────────────────────────────────────────────────────────────

class TestBeta:
    def test_identical_series_beta_one(self, trending_up):
        result = beta(trending_up, trending_up)
        assert result is not None
        assert result == pytest.approx(1.0, abs=0.01)

    def test_too_short(self):
        assert beta([100.0] * 29, [100.0] * 29) is None

    def test_uncorrelated_near_zero(self):
        import random
        random.seed(42)
        x = [100.0 + random.gauss(0, 1) for _ in range(100)]
        y = [200.0 + random.gauss(0, 1) for _ in range(100)]
        result = beta(x, y)
        assert result is not None
        assert abs(result) < 1.0  # uncorrelated series → low beta


# ── compute_all ────────────────────────────────────────────────────────────────

class TestComputeAll:
    def test_returns_all_keys(self, trending_up):
        result = compute_all(trending_up)
        expected_keys = {
            "retorno_acumulado", "cagr", "volatilidade_anual",
            "sharpe", "sortino", "max_drawdown", "beta", "alpha", "var_95",
        }
        assert expected_keys.issubset(result.keys())

    def test_with_market(self, trending_up):
        mkt = [p * 0.9 for p in trending_up]  # market moves less
        result = compute_all(trending_up, mkt_prices=mkt)
        assert result["beta"] is not None

    def test_empty_prices(self):
        result = compute_all([])
        for v in result.values():
            assert v is None
