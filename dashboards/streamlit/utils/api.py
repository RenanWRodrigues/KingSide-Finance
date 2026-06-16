"""Finance Dashboard — API Fetch Utilities with direct-data fallback."""
from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import streamlit as st

from config import API_URL

_logger = logging.getLogger(__name__)


def fetch(
    endpoint: str,
    params: dict | None = None,
    silent: bool = False,
    timeout: int = 3,
) -> dict | list | None:
    # ── 1. Try FastAPI backend ────────────────────────────────────
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{API_URL}{endpoint}", params=params or {})
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        _logger.debug("API unavailable for %s (%s: %s) — trying direct fallback", endpoint, type(exc).__name__, exc)

    # ── 2. Direct fallback (yfinance / BCB) ──────────────────────
    try:
        result = _direct(endpoint, params or {})
    except Exception as exc:
        _logger.warning("Direct fallback failed for %s: %s", endpoint, exc)
        result = None
    if result is not None:
        return result

    if not silent:
        st.warning(
            f"Dados indisponíveis para `{endpoint}` — API offline e fallback sem dados.",
            icon="⚠️",
        )
    return None


def fetch_parallel(
    calls: list[tuple[str, dict | None]],
    timeout: int = 3,
) -> list:
    results: list = [None] * len(calls)
    with ThreadPoolExecutor(max_workers=min(len(calls), 8)) as pool:
        futures = {
            pool.submit(fetch, ep, params, True, timeout): idx
            for idx, (ep, params) in enumerate(calls)
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return results


def _direct(endpoint: str, params: dict) -> dict | list | None:
    """Map API endpoint → direct yfinance/BCB data provider."""
    from utils import direct as d

    # /stocks/{ticker}/history
    m = re.match(r"^/stocks/([^/]+)/history$", endpoint)
    if m:
        return d.stock_history(m.group(1), params.get("period", "1y"))

    # /macro/brasil/cambio_dolar — short-TTL route (BCB PTAX, refreshes every 5 min)
    if endpoint == "/macro/brasil/cambio_dolar":
        return d.macro_cambio()

    # /macro/brasil/{indicator}
    m = re.match(r"^/macro/brasil/([^/]+)$", endpoint)
    if m:
        return d.macro_indicator(m.group(1))

    # /compare
    if endpoint == "/compare":
        raw = params.get("tickers", "")
        tickers = tuple(t.strip() for t in raw.split(",") if t.strip())
        if tickers:
            return d.compare_assets(tickers, params.get("periodo", "1y"))

    # /ranking/{kind}
    m = re.match(r"^/ranking/([^/]+)$", endpoint)
    if m:
        return d.ranking(m.group(1), int(params.get("limite", 15)))

    # /forecast/{ticker}
    m = re.match(r"^/forecast/([^/]+)$", endpoint)
    if m:
        return d.forecast_linear(m.group(1), int(params.get("horizonte_dias", 30)))

    # /stocks/{ticker}/financials
    m = re.match(r"^/stocks/([^/]+)/financials$", endpoint)
    if m:
        return d.stock_financials(m.group(1), params.get("period", "annual"))

    # /stocks/{ticker}/dividends
    m = re.match(r"^/stocks/([^/]+)/dividends$", endpoint)
    if m:
        return d.stock_dividends(m.group(1))

    # /stocks/{ticker}/balance-sheet
    m = re.match(r"^/stocks/([^/]+)/balance-sheet$", endpoint)
    if m:
        return d.stock_balance_sheet(m.group(1))

    # /stocks/{ticker}/valuation
    m = re.match(r"^/stocks/([^/]+)/valuation$", endpoint)
    if m:
        return d.stock_valuation(m.group(1))

    return None


def to_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def safe_pct(num: float | None, denom: float | None) -> float | None:
    if num is None or denom is None or denom == 0:
        return None
    return (num - denom) / abs(denom) * 100


# ── API Health ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def _api_online() -> bool:
    """Returns True if the FastAPI backend responds to /health with 2xx within 2 s."""
    try:
        base = API_URL.split("/api/")[0]
        with httpx.Client(timeout=2) as c:
            r = c.get(f"{base}/health")
            return r.is_success
    except Exception:
        return False


def api_offline_banner() -> None:
    """Render one centralized info banner when the backend is unreachable.

    Call this once at the top of each page render so users are not flooded
    with per-endpoint warnings. Individual endpoint failures still surface
    via fetch() when both API and direct fallback return nothing.
    """
    if not _api_online():
        st.info(
            "**Backend offline** — dados via yfinance / BCB (modo fallback direto). "
            f"Para ativar o backend: `uvicorn app.main:app --port 8000` "
            f"_(API configurada em: `{API_URL}`)_",
            icon="🔌",
        )
