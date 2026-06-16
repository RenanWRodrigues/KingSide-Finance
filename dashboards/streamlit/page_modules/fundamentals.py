"""Finance — Análise Fundamentalista (página premium com todos os gráficos institucionais)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import TICKER_UNIVERSE
from utils.api import fetch, to_float
from utils.ui import section_header, apply_period_filter

from components.charts import (
    render_margin_chart,
    render_leverage_chart,
    render_revenue_vs_profit,
    render_patrimony_vs_debt,
    render_recurring_results,
    render_valuation_card,
    render_dividend_chart,
    render_forecast_chart,
    render_anomaly_chart,
    render_sentiment_chart,
    render_technical_indicators,
    render_ranking_heatmap,
    render_macro_correlation,
)
from components.charts.data import (
    fetch_annual_df,
    fetch_quarterly_df,
    fetch_dividends_df,
    fetch_valuation_data,
    enrich_dividends_with_price,
)
from components.charts.styles import C_POS, C_NEUT, C_WARN, C_PURPLE, C_NEG, TEXT_MUTED, TEXT_PRIMARY


_SECTOR_MAP = {t: v.split(" · ")[1] if " · " in v else "Geral" for t, v in TICKER_UNIVERSE.items()}


def _has_cols(df: pd.DataFrame | None, *cols: str) -> bool:
    """Return True only if df is non-empty and has all required columns with data."""
    if df is None or df.empty:
        return False
    return all(c in df.columns and df[c].notna().any() for c in cols)


def _guard(df: pd.DataFrame | None, *required: str) -> pd.DataFrame | None:
    """Return df if it has all required columns with data, else None (triggers demo)."""
    return df if _has_cols(df, *required) else None


def _header_strip(ticker: str, data: dict | None = None) -> None:
    name    = TICKER_UNIVERSE.get(ticker, ticker).split(" · ")[0]
    sector  = _SECTOR_MAP.get(ticker, "—")
    price   = "—"
    chg     = "—"
    chg_pos = True

    if data and data.get("cotacoes"):
        cots  = data["cotacoes"]
        last  = to_float(cots[-1].get("fechamento"))
        prev  = to_float(cots[-2].get("fechamento")) if len(cots) > 1 else last
        if last and prev:
            price = f"R$ {last:.2f}"
            delta = (last - prev) / prev * 100 if prev else 0
            chg   = f"{delta:+.2f}%"
            chg_pos = delta >= 0

    chg_color  = C_POS if chg_pos else C_NEG
    badge_text = "● AO VIVO" if data else "● DEMO"

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:20px;"
        f"background:linear-gradient(135deg,#0d1424 0%,#0f1a2e 100%);"
        f"border:1px solid rgba(255,255,255,0.05);border-radius:10px;"
        f"padding:0.8rem 1.4rem;margin-bottom:1.25rem;flex-wrap:wrap;'>"
        f"<div style='display:flex;flex-direction:column;'>"
        f"<span style='font-size:1.5rem;font-weight:900;color:{TEXT_PRIMARY};"
        f"font-family:\"JetBrains Mono\",monospace;letter-spacing:-0.03em;"
        f"line-height:1;'>{ticker}</span>"
        f"<span style='font-size:0.65rem;color:{TEXT_MUTED};font-family:Inter,sans-serif;"
        f"letter-spacing:0.08em;text-transform:uppercase;'>{name}</span>"
        f"</div>"
        f"<div style='display:flex;align-items:center;gap:8px;"
        f"padding-left:20px;border-left:1px solid rgba(255,255,255,0.06);'>"
        f"<span style='font-size:1.2rem;font-weight:800;color:{TEXT_PRIMARY};"
        f"font-family:\"JetBrains Mono\",monospace;'>{price}</span>"
        f"<span style='font-size:0.88rem;font-weight:700;color:{chg_color};"
        f"font-family:\"JetBrains Mono\",monospace;'>{chg}</span>"
        f"</div>"
        f"<div style='padding:2px 10px;border-radius:20px;"
        f"background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.2);'>"
        f"<span style='font-size:0.68rem;font-weight:700;color:#3B82F6;"
        f"font-family:Inter,sans-serif;letter-spacing:0.06em;'>{sector}</span>"
        f"</div>"
        f"<div style='margin-left:auto;padding:2px 10px;border-radius:20px;"
        f"background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);'>"
        f"<span style='font-size:0.62rem;font-weight:700;color:#10B981;"
        f"font-family:Inter,sans-serif;'>{badge_text}</span>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _try_build_df(data: dict | None, ticker: str) -> pd.DataFrame | None:
    if not data or not data.get("cotacoes"):
        return None
    rows = []
    for c in data["cotacoes"]:
        rows.append({
            "data":       pd.to_datetime(c.get("data")),
            "fechamento": to_float(c.get("fechamento")),
            "abertura":   to_float(c.get("abertura")) or to_float(c.get("fechamento")),
            "maxima":     to_float(c.get("maxima"))   or to_float(c.get("fechamento")),
            "minima":     to_float(c.get("minima"))   or to_float(c.get("fechamento")),
            "volume":     float(c.get("volume") or 0),
        })
    df = pd.DataFrame(rows).dropna(subset=["fechamento"])
    return df if not df.empty else None


def render(ticker: str = "PETR4") -> None:
    sector = _SECTOR_MAP.get(ticker, "Geral")

    with st.spinner(f"Carregando dados de {ticker}..."):
        price_data = fetch(f"/stocks/{ticker}/history", {"period": "1y"})
        annual_df = fetch_annual_df(ticker)
        quarterly_df = fetch_quarterly_df(ticker)

    price_df = _try_build_df(price_data, ticker)
    price_df = apply_period_filter(price_df)
    annual_df = apply_period_filter(annual_df, year_col="ano")
    quarterly_df = apply_period_filter(quarterly_df)
    _header_strip(ticker, price_data)

    dividends_df = fetch_dividends_df(ticker)
    if dividends_df is not None and price_df is not None:
        dividends_df = enrich_dividends_with_price(dividends_df, price_df)

    valuation_data = fetch_valuation_data(ticker) or {}

    # Inject div_liq_ebitda from annual balance sheet data if available
    if annual_df is not None and "alavancagem" in annual_df.columns:
        alavancagem_vals = annual_df["alavancagem"].dropna()
        if not alavancagem_vals.empty:
            valuation_data["div_liq_ebitda"] = float(alavancagem_vals.iloc[-1])

    valuation_data = valuation_data if valuation_data else None

    # ── Navigation Tabs ─────────────────────────────────────────────────────────
    tabs = st.tabs([
        "◉  Precificação",
        "◈  Fundamentos",
        "⊞  Estrutura de Capital",
        "◆  Retornos",
        "◎  Valuation",
        "↗  Previsão ML",
        "≈  Sentimento",
        "⊞  Rankings",
        "∿  Macro",
    ])

    # ── Tab 0 — Price ────────────────────────────────────────────────────────────
    with tabs[0]:
        from components.charts import render_price_chart, render_technical_indicators

        c1, c2, c3 = st.columns(3)
        with c1:
            ma_opts = st.multiselect("Médias Móveis", [20, 50, 200], default=[20, 50], key="fund_ma")
        with c2:
            show_rsi_ch = st.checkbox("RSI", value=True, key="fund_rsi")
        with c3:
            show_macd_ch = st.checkbox("MACD", value=True, key="fund_macd")

        render_price_chart(price_df, ticker, show_rsi=show_rsi_ch, show_macd=show_macd_ch, ma_periods=ma_opts or [20, 50])
        st.markdown(
            "<div style='margin:2rem 0 3rem;height:1px;"
            "background:rgba(255,255,255,0.05);'></div>",
            unsafe_allow_html=True,
        )
        render_technical_indicators(price_df, ticker)

    # ── Tab 1 — Fundamentals ──────────────────────────────────────────────────────
    with tabs[1]:
        render_revenue_vs_profit(
            _guard(annual_df, "receita", "lucro_liquido", "margem_liquida"), ticker)
        st.markdown(
            "<div style='margin:2rem 0 3rem;height:1px;"
            "background:rgba(255,255,255,0.05);'></div>",
            unsafe_allow_html=True,
        )
        render_recurring_results(
            _guard(annual_df, "ebitda", "lucro_liquido"), ticker)
        st.markdown(
            "<div style='margin:2rem 0 3rem;height:1px;"
            "background:rgba(255,255,255,0.05);'></div>",
            unsafe_allow_html=True,
        )
        render_margin_chart(
            _guard(quarterly_df, "margem_liquida"), ticker,
            col="margem_liquida", title="Margem Líquida Histórica", color=C_POS)
        st.markdown(
            "<div style='margin:2rem 0 3rem;height:1px;"
            "background:rgba(255,255,255,0.05);'></div>",
            unsafe_allow_html=True,
        )
        render_margin_chart(
            _guard(quarterly_df, "margem_ebitda"), ticker,
            col="margem_ebitda", title="Margem EBITDA Histórica", color=C_NEUT)

    # ── Tab 2 — Capital Structure ─────────────────────────────────────────────────
    with tabs[2]:
        render_leverage_chart(
            _guard(annual_df, "alavancagem"), ticker)
        st.markdown(
            "<div style='margin:2rem 0 3rem;height:1px;"
            "background:rgba(255,255,255,0.05);'></div>",
            unsafe_allow_html=True,
        )
        render_patrimony_vs_debt(
            _guard(annual_df, "patrimonio_liquido", "divida_bruta", "divida_liquida"), ticker)

    # ── Tab 3 — Returns ───────────────────────────────────────────────────────────
    with tabs[3]:
        render_dividend_chart(
            _guard(dividends_df, "dividendo"), ticker)

    # ── Tab 4 — Valuation ─────────────────────────────────────────────────────────
    with tabs[4]:
        render_valuation_card(valuation_data, ticker, sector)

    # ── Tab 5 — ML Forecast ───────────────────────────────────────────────────────
    with tabs[5]:
        n_days = st.select_slider("Horizonte de previsão (dias úteis)", [30, 45, 60, 90, 120], value=60, key="fund_horizon")
        render_forecast_chart(price_df, ticker, n_forecast_days=n_days)
        st.markdown(
            "<div style='margin:2rem 0 3rem;height:1px;"
            "background:rgba(255,255,255,0.05);'></div>",
            unsafe_allow_html=True,
        )
        render_anomaly_chart(price_df, ticker)

    # ── Tab 6 — Sentiment ─────────────────────────────────────────────────────────
    with tabs[6]:
        render_sentiment_chart(None, ticker)

    # ── Tab 7 — Rankings ──────────────────────────────────────────────────────────
    with tabs[7]:
        from config import TICKER_UNIVERSE
        all_tickers = list(TICKER_UNIVERSE.keys())[:20]
        selected_tickers = st.multiselect(
            "Selecione ativos para o ranking",
            all_tickers,
            default=all_tickers[:15],
            key="fund_rank_tickers",
        )
        if selected_tickers:
            render_ranking_heatmap(selected_tickers)
        else:
            st.info("Selecione ao menos 3 ativos para gerar o ranking.")

    # ── Tab 8 — Macro ─────────────────────────────────────────────────────────────
    with tabs[8]:
        render_macro_correlation(None, ticker, price_df=price_df)
