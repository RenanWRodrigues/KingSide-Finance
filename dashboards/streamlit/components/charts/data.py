"""Finance Charts — Data fetching layer (API-first, yfinance fallback, demo last resort)."""
from __future__ import annotations

import pandas as pd
import streamlit as st


def _fetch(endpoint: str, params: dict | None = None) -> dict | list | None:
    from utils.api import fetch
    return fetch(endpoint, params, silent=True)


def _f(val: object) -> float | None:
    try:
        return float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_annual_df(ticker: str) -> pd.DataFrame | None:
    """Annual income statement merged with balance sheet → annual_df shape."""
    inc_raw = _fetch(f"/stocks/{ticker}/financials", {"period": "annual"})
    bs_raw = _fetch(f"/stocks/{ticker}/balance-sheet")

    if not inc_raw:
        return None

    rows = []
    for r in inc_raw:
        periodo = str(r.get("periodo", ""))
        try:
            ano = int(periodo[:4])
        except ValueError:
            continue
        rows.append({
            "ano": ano,
            "receita": _f(r.get("receita_liquida")),
            "ebitda": _f(r.get("ebitda")),
            "lucro_liquido": _f(r.get("lucro_liquido")),
            "margem_liquida": _f(r.get("margem_liquida")),
            "margem_ebitda": _f(r.get("margem_ebitda")),
        })

    inc_df = pd.DataFrame(rows).dropna(subset=["receita"])
    if inc_df.empty:
        return None

    if bs_raw:
        bs_rows = []
        for r in bs_raw:
            periodo = str(r.get("periodo", ""))
            try:
                ano = int(periodo[:4])
            except ValueError:
                continue
            bs_rows.append({
                "ano": ano,
                "divida_bruta": _f(r.get("divida_bruta")),
                "caixa": _f(r.get("caixa")),
                "divida_liquida": _f(r.get("divida_liquida")),
                "patrimonio_liquido": _f(r.get("patrimonio_liquido")),
            })
        bs_df = pd.DataFrame(bs_rows)
        if not bs_df.empty:
            inc_df = inc_df.merge(bs_df, on="ano", how="left")

    if "divida_liquida" in inc_df.columns and "ebitda" in inc_df.columns:
        inc_df["alavancagem"] = inc_df.apply(
            lambda row: row["divida_liquida"] / row["ebitda"]
            if row["ebitda"] is not None and row["ebitda"] != 0 and row["divida_liquida"] is not None
            else None,
            axis=1,
        )

    return inc_df.sort_values("ano").reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_quarterly_df(ticker: str) -> pd.DataFrame | None:
    """Quarterly income statement → quarterly_df shape."""
    data = _fetch(f"/stocks/{ticker}/financials", {"period": "quarterly"})
    if not data:
        return None

    rows = []
    for r in data:
        rows.append({
            "data": pd.to_datetime(r.get("periodo")),
            "receita": _f(r.get("receita_liquida")),
            "ebitda": _f(r.get("ebitda")),
            "lucro_liquido": _f(r.get("lucro_liquido")),
            "margem_liquida": _f(r.get("margem_liquida")),
            "margem_ebitda": _f(r.get("margem_ebitda")),
        })

    df = pd.DataFrame(rows).dropna(subset=["receita"])
    return df.sort_values("data").reset_index(drop=True) if not df.empty else None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_dividends_df(ticker: str, _price_df_hash: str = "") -> pd.DataFrame | None:
    """Dividends history → dividends_df shape.

    ``_price_df_hash`` is not used for computation — it exists only as a cache
    discriminator so callers can pass ``str(id(price_df))`` without breaking the
    @cache signature (DataFrames aren't hashable).
    """
    data = _fetch(f"/stocks/{ticker}/dividends")
    if not data:
        return None

    rows = []
    for r in data:
        rows.append({
            "data": pd.to_datetime(r.get("data_ex")),
            "dividendo": _f(r.get("valor")),
            "tipo": r.get("tipo", "DIVIDENDO"),
        })

    df = pd.DataFrame(rows).dropna(subset=["dividendo"])
    if df.empty:
        return None

    df = df.sort_values("data").reset_index(drop=True)
    df["preco"] = 0.0
    df["yield_trimestral"] = 0.0
    return df


def enrich_dividends_with_price(
    div_df: pd.DataFrame, price_df: pd.DataFrame
) -> pd.DataFrame:
    """Add 'preco' and 'yield_trimestral' columns using nearest-date price lookup."""
    if price_df is None or price_df.empty:
        return div_df

    df = div_df.copy()
    price_df = price_df.sort_values("data")

    def _nearest(dt: pd.Timestamp) -> float | None:
        idx = price_df["data"].searchsorted(dt)
        idx = min(idx, len(price_df) - 1)
        return _f(price_df["fechamento"].iloc[idx])

    df["preco"] = df["data"].apply(lambda d: _nearest(d) or 0.0)
    df["yield_trimestral"] = df.apply(
        lambda row: row["dividendo"] / row["preco"] * 100
        if row["preco"] and row["preco"] != 0
        else 0.0,
        axis=1,
    )
    return df


@st.cache_data(ttl=300, show_spinner=False)
def fetch_valuation_data(ticker: str) -> dict | None:
    """Current valuation multiples dict."""
    return _fetch(f"/stocks/{ticker}/valuation")
