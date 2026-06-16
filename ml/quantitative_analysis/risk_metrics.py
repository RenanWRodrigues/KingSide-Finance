from __future__ import annotations

import math
from typing import TypedDict

import numpy as np

_SELIC_ANNUAL: float = 0.1175  # ~11.75% a.a. — atualizar conforme decisão COPOM


class RiskMetrics(TypedDict):
    retorno_acumulado: float | None
    cagr: float | None
    volatilidade_anual: float | None
    sharpe: float | None
    sortino: float | None
    max_drawdown: float | None
    beta: float | None
    alpha: float | None
    var_95: float | None


def _returns(prices: list[float]) -> np.ndarray:
    arr = np.array(prices, dtype=float)
    return np.diff(arr) / arr[:-1]


def accumulated_return(prices: list[float]) -> float | None:
    if len(prices) < 2 or prices[0] <= 0:
        return None
    return round((prices[-1] / prices[0] - 1) * 100, 2)


def cagr(prices: list[float]) -> float | None:
    """Compound Annual Growth Rate using 252 trading days per year."""
    if len(prices) < 2 or prices[0] <= 0:
        return None
    n_years = len(prices) / 252
    if n_years <= 0:
        return None
    return round(((prices[-1] / prices[0]) ** (1.0 / n_years) - 1) * 100, 2)


def annualized_volatility(prices: list[float]) -> float | None:
    if len(prices) < 3:
        return None
    rets = _returns(prices)
    if len(rets) < 2:
        return None
    return round(float(np.std(rets, ddof=1)) * math.sqrt(252) * 100, 2)


def sharpe_ratio(prices: list[float], rf: float = _SELIC_ANNUAL) -> float | None:
    if len(prices) < 30:
        return None
    rets = _returns(prices)
    rf_daily = (1 + rf) ** (1.0 / 252) - 1
    excess = rets - rf_daily
    std = float(np.std(excess, ddof=1))
    if std == 0:
        return None
    return round(float(np.mean(excess)) / std * math.sqrt(252), 4)


def sortino_ratio(prices: list[float], rf: float = _SELIC_ANNUAL) -> float | None:
    if len(prices) < 30:
        return None
    rets = _returns(prices)
    rf_daily = (1 + rf) ** (1.0 / 252) - 1
    excess = rets - rf_daily
    downside = excess[excess < 0]
    if len(downside) == 0:
        return None
    dstd = float(np.std(downside, ddof=1))
    if dstd == 0:
        return None
    return round(float(np.mean(excess)) / dstd * math.sqrt(252), 4)


def max_drawdown(prices: list[float]) -> float | None:
    if len(prices) < 2:
        return None
    arr = np.array(prices, dtype=float)
    peak = np.maximum.accumulate(arr)
    dd = (arr - peak) / peak
    return round(float(np.min(dd)) * 100, 2)


def var_95(prices: list[float]) -> float | None:
    """Value at Risk at 95% confidence (5th percentile daily return)."""
    if len(prices) < 30:
        return None
    rets = _returns(prices)
    return round(float(np.percentile(rets, 5)) * 100, 2)


def beta(asset_prices: list[float], mkt_prices: list[float]) -> float | None:
    if len(asset_prices) < 30 or len(mkt_prices) < 30:
        return None
    n = min(len(asset_prices), len(mkt_prices))
    ar = _returns(asset_prices[-n:])
    mr = _returns(mkt_prices[-n:])
    if len(ar) < 2:
        return None
    cov_matrix = np.cov(ar, mr)
    mvar = float(cov_matrix[1, 1])
    if mvar == 0:
        return None
    return round(float(cov_matrix[0, 1]) / mvar, 4)


def alpha(
    asset_prices: list[float],
    mkt_prices: list[float],
    rf: float = _SELIC_ANNUAL,
) -> float | None:
    b = beta(asset_prices, mkt_prices)
    if b is None or len(asset_prices) < 2 or len(mkt_prices) < 2:
        return None
    a_ret = (asset_prices[-1] / asset_prices[0] - 1) * 100
    n = len(mkt_prices) / 252
    m_ret = (
        ((mkt_prices[-1] / mkt_prices[0]) ** (1.0 / n) - 1) * 100
        if n > 0 and mkt_prices[0] > 0
        else 0.0
    )
    return round(a_ret - (rf * 100 + b * (m_ret - rf * 100)), 4)


def compute_all(
    prices: list[float],
    mkt_prices: list[float] | None = None,
    rf: float = _SELIC_ANNUAL,
) -> RiskMetrics:
    """Compute all risk metrics for a price series. mkt_prices used for beta/alpha."""
    b = beta(prices, mkt_prices) if mkt_prices else None
    a = alpha(prices, mkt_prices, rf) if mkt_prices else None
    return RiskMetrics(
        retorno_acumulado=accumulated_return(prices),
        cagr=cagr(prices),
        volatilidade_anual=annualized_volatility(prices),
        sharpe=sharpe_ratio(prices, rf),
        sortino=sortino_ratio(prices, rf),
        max_drawdown=max_drawdown(prices),
        beta=b,
        alpha=a,
        var_95=var_95(prices),
    )
