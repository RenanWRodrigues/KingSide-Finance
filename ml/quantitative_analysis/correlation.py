from __future__ import annotations

import numpy as np


def _daily_returns(prices: list[float]) -> np.ndarray:
    arr = np.array(prices, dtype=float)
    return np.diff(arr) / arr[:-1]


def _ranks(arr: np.ndarray) -> np.ndarray:
    """Convert array to rank order (handles ties via average rank)."""
    order = np.argsort(arr)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(arr) + 1)
    return ranks


def pearson(x: list[float], y: list[float]) -> float | None:
    n = min(len(x), len(y))
    if n < 5:
        return None
    a = np.array(x[-n:], dtype=float)
    b = np.array(y[-n:], dtype=float)
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    return round(float(np.corrcoef(a, b)[0, 1]), 4)


def spearman(x: list[float], y: list[float]) -> float | None:
    """Spearman = Pearson on ranks — pure numpy, no scipy."""
    n = min(len(x), len(y))
    if n < 5:
        return None
    a = np.array(x[-n:], dtype=float)
    b = np.array(y[-n:], dtype=float)
    return pearson(_ranks(a).tolist(), _ranks(b).tolist())


def kendall(x: list[float], y: list[float]) -> float | None:
    """Kendall τ-b via concordant/discordant pairs — pure numpy."""
    n = min(len(x), len(y))
    if n < 5:
        return None
    a = np.array(x[-n:], dtype=float)
    b = np.array(y[-n:], dtype=float)
    concordant = discordant = tied_x = tied_y = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            dx = float(a[j] - a[i])
            dy = float(b[j] - b[i])
            prod = dx * dy
            if prod > 0:
                concordant += 1
            elif prod < 0:
                discordant += 1
            else:
                if dx == 0:
                    tied_x += 1
                if dy == 0:
                    tied_y += 1
    denom = (concordant + discordant + tied_x) * (concordant + discordant + tied_y)
    if denom <= 0:
        return None
    return round(float(concordant - discordant) / (denom ** 0.5), 4)


def correlation_matrix(
    prices_dict: dict[str, list[float]],
    method: str = "pearson",
) -> dict[str, dict[str, float | None]]:
    """Correlation matrix on daily returns for a dict of {ticker: price_series}."""
    tickers = list(prices_dict.keys())
    rets: dict[str, list[float]] = {}
    for t, v in prices_dict.items():
        if len(v) >= 3:
            rets[t] = _daily_returns(v).tolist()

    _fn = {"pearson": pearson, "spearman": spearman, "kendall": kendall}.get(method, pearson)

    result: dict[str, dict[str, float | None]] = {}
    for t1 in tickers:
        result[t1] = {}
        for t2 in tickers:
            if t1 == t2:
                result[t1][t2] = 1.0
            elif t1 in rets and t2 in rets:
                result[t1][t2] = _fn(rets[t1], rets[t2])
            else:
                result[t1][t2] = None
    return result


def rolling_correlation(
    x: list[float],
    y: list[float],
    window: int = 30,
) -> list[float | None]:
    n = min(len(x), len(y))
    if n < window:
        return []
    xa = np.array(x[-n:], dtype=float)
    ya = np.array(y[-n:], dtype=float)
    out: list[float | None] = []
    for i in range(window - 1, n):
        xi = xa[i - window + 1: i + 1]
        yi = ya[i - window + 1: i + 1]
        if np.std(xi) == 0 or np.std(yi) == 0:
            out.append(None)
        else:
            out.append(round(float(np.corrcoef(xi, yi)[0, 1]), 4))
    return out
