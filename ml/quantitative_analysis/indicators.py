from __future__ import annotations

import numpy as np


def _ema_series(prices: list[float], period: int) -> list[float]:
    if len(prices) < period:
        return []
    arr = np.array(prices, dtype=float)
    k = 2.0 / (period + 1)
    val = float(np.mean(arr[:period]))
    result = [val]
    for p in arr[period:]:
        val = float(p) * k + val * (1 - k)
        result.append(val)
    return result


def rsi(prices: list[float], period: int = 14) -> float | None:
    if len(prices) < period + 2:
        return None
    window = prices[-(period * 4):] if len(prices) > period * 4 else prices
    arr = np.array(window, dtype=float)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains[-period:]))
    avg_loss = float(np.mean(losses[-period:]))
    if avg_loss == 0:
        return 100.0
    return round(100.0 - 100.0 / (1.0 + avg_gain / avg_loss), 2)


def sma(prices: list[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    return round(float(np.mean(prices[-period:])), 2)


def ema(prices: list[float], period: int) -> float | None:
    series = _ema_series(prices, period)
    return round(series[-1], 2) if series else None


def macd(
    prices: list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> dict[str, float | None]:
    if len(prices) < slow + signal_period:
        return {"macd": None, "signal_line": None, "histogram": None}
    fast_s = _ema_series(prices, fast)
    slow_s = _ema_series(prices, slow)
    offset = len(fast_s) - len(slow_s)
    macd_series = [f - s for f, s in zip(fast_s[offset:], slow_s)]
    if len(macd_series) < signal_period:
        return {"macd": round(macd_series[-1], 4) if macd_series else None, "signal_line": None, "histogram": None}
    signal_s = _ema_series(macd_series, signal_period)
    if not signal_s:
        return {"macd": round(macd_series[-1], 4), "signal_line": None, "histogram": None}
    m = round(macd_series[-1], 4)
    s = round(signal_s[-1], 4)
    return {"macd": m, "signal_line": s, "histogram": round(m - s, 4)}


def bollinger(
    prices: list[float],
    period: int = 20,
    n_std: float = 2.0,
) -> dict[str, float | None]:
    if len(prices) < period:
        return {"upper": None, "middle": None, "lower": None}
    window = np.array(prices[-period:], dtype=float)
    mid = float(np.mean(window))
    std = float(np.std(window, ddof=1))
    return {
        "upper": round(mid + n_std * std, 2),
        "middle": round(mid, 2),
        "lower": round(mid - n_std * std, 2),
    }


def technical_summary(prices: list[float]) -> dict[str, object]:
    macd_v = macd(prices)
    bb = bollinger(prices)
    return {
        "preco_atual": round(prices[-1], 2) if prices else None,
        "rsi_14": rsi(prices),
        "ma_20": sma(prices, 20),
        "ma_50": sma(prices, 50),
        "ma_200": sma(prices, 200),
        "ema_20": ema(prices, 20),
        "macd": macd_v["macd"],
        "macd_signal": macd_v["signal_line"],
        "macd_histogram": macd_v["histogram"],
        "bollinger_upper": bb["upper"],
        "bollinger_middle": bb["middle"],
        "bollinger_lower": bb["lower"],
    }
