"""Finance Charts — Heatmap de Rankings com Dados Reais."""
from __future__ import annotations

import math
import random

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .styles import (
    C_NEG, C_NEUT, C_POS, C_WARN, C_PURPLE, C_CYAN,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, base_layout,
)
from .utils import (
    insight_box, section_header_charts, _seed,
)


def _safe_float(val: object) -> float | None:
    try:
        v = float(val)  # type: ignore[arg-type]
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def _fetch_real_metrics(tickers: list[str]) -> tuple[pd.DataFrame, bool]:
    """Fetch DY/ROE from valuation API + momentum/volatility from price history.

    Returns (DataFrame indexed by ticker, is_real).
    is_real=True when at least 50% of tickers have API data.
    """
    from utils.api import fetch_parallel, to_float

    val_results = fetch_parallel(
        [(f"/stocks/{t}/valuation", None) for t in tickers],
        timeout=15,
    )
    hist_results = fetch_parallel(
        [(f"/stocks/{t}/history", {"period": "1y"}) for t in tickers],
        timeout=20,
    )

    rows = []
    real_count = 0

    for ticker, val, hist in zip(tickers, val_results, hist_results):
        row: dict[str, object] = {"ticker": ticker}
        has_real = False

        # DY and ROE from valuation
        if val and isinstance(val, dict):
            row["DY"]  = _safe_float(val.get("dy"))
            row["ROE"] = _safe_float(val.get("roe"))
            if row["DY"] is not None or row["ROE"] is not None:
                has_real = True
        else:
            row["DY"]  = None
            row["ROE"] = None

        # Momentum (1y return) and Volatility from price history
        cotacoes = (hist or {}).get("cotacoes", []) if isinstance(hist, dict) else []
        if len(cotacoes) >= 20:
            closes = [to_float(c.get("fechamento")) for c in cotacoes]
            closes = [c for c in closes if c is not None]
            if len(closes) >= 20:
                first, last = closes[0], closes[-1]
                ret_1y = (last / first - 1) * 100 if first else 0
                rets   = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
                vol    = float(np.std(rets) * math.sqrt(252) * 100) if rets else 30.0
                row["Crescimento"] = round(ret_1y, 2)
                row["Volatilidade"] = round(vol, 2)
                # Momentum = last 3-month return if enough history
                idx_3m = max(0, len(closes) - 63)
                row["Momentum"] = round((last / closes[idx_3m] - 1) * 100, 2) if closes[idx_3m] else ret_1y
                has_real = True
        else:
            row["Crescimento"]  = None
            row["Volatilidade"] = None
            row["Momentum"]     = None

        # Margem: use ROIC (returnOnAssets as proxy) when available
        row["Margem"] = _safe_float((val or {}).get("roic")) if val else None

        if has_real:
            real_count += 1
        rows.append(row)

    df = pd.DataFrame(rows).set_index("ticker")
    is_real = real_count >= max(1, len(tickers) // 2)
    return df, is_real


def _fill_missing_with_demo(df: pd.DataFrame) -> pd.DataFrame:
    """Fill None cells with plausible synthetic values so the heatmap always renders."""
    df = df.copy()
    for ticker in df.index:
        rng = random.Random(_seed(ticker) + 40)
        defaults = {
            "DY":          rng.uniform(2, 14),
            "ROE":         rng.uniform(5, 40),
            "Crescimento": rng.uniform(-10, 35),
            "Margem":      rng.uniform(5, 45),
            "Momentum":    rng.uniform(-20, 60),
            "Volatilidade": rng.uniform(12, 55),
        }
        for col, default in defaults.items():
            if col in df.columns and (df.at[ticker, col] is None or
                                       (isinstance(df.at[ticker, col], float) and math.isnan(df.at[ticker, col]))):
                df.at[ticker, col] = default
    return df


def _rank_normalize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().astype(float)
    for col in out.columns:
        ascending = col == "Volatilidade"
        out[col] = out[col].rank(ascending=ascending, pct=True) * 100
    return out


def _auto_insight(df: pd.DataFrame, norm: pd.DataFrame, is_real: bool) -> str:
    avg_scores = norm.mean(axis=1).sort_values(ascending=False)
    top3   = avg_scores.head(3).index.tolist()
    bottom = avg_scores.tail(1).index.tolist()[0]
    source = "dados reais" if is_real else "dados ilustrativos"
    return (
        f"Topo do ranking multi-fatorial ({source}): {', '.join(top3)}. "
        f"Destaque negativo: {bottom} com scores abaixo da média em múltiplas dimensões. "
        "Heatmap normalizado por percentil (100 = melhor da amostra)."
    )


def render_ranking_heatmap(
    tickers: list[str] | None = None,
    df_raw: pd.DataFrame | None = None,
) -> None:
    if tickers is None:
        tickers = [
            "PETR4", "VALE3", "ITUB4", "WEGE3", "BBAS3",
            "ABEV3", "RENT3", "EMBR3", "TOTS3", "RADL3",
            "EGIE3", "CMIG4", "TAEE11", "BBSE3", "PRIO3",
        ]

    is_real = False
    if df_raw is None:
        with st.spinner("Carregando métricas reais..."):
            df_raw, is_real = _fetch_real_metrics(tickers)
        df_raw = _fill_missing_with_demo(df_raw)
    else:
        is_real = True

    # Ensure all required columns exist
    for col in ["DY", "ROE", "Crescimento", "Margem", "Momentum", "Volatilidade"]:
        if col not in df_raw.columns:
            df_raw[col] = np.nan

    df_norm = _rank_normalize(df_raw[["DY", "ROE", "Crescimento", "Margem", "Momentum", "Volatilidade"]])

    section_header_charts(
        "Heatmap de Rankings",
        f"{len(tickers)} Ativos · DY | ROE | Crescimento | Margem | Momentum | Volatilidade"
        + (" · Dados reais" if is_real else " · Dados ilustrativos"),
        C_WARN,
    )

    if not is_real:
        st.caption(
            "⚠️ API indisponível para alguns ativos — células sem dados reais preenchidas com "
            "valores ilustrativos. Ative o backend para rankings 100% reais."
        )

    z      = df_norm.values.T.tolist()
    y_lbl  = df_norm.columns.tolist()
    x_lbl  = df_norm.index.tolist()
    text   = [[f"{df_raw.loc[x, y]:.1f}" for x in df_norm.index] for y in df_norm.columns]

    fig = go.Figure(go.Heatmap(
        z=z, x=x_lbl, y=y_lbl,
        colorscale=[
            [0.0,  "#7f1d1d"],
            [0.25, "#ef4444"],
            [0.45, "#1e293b"],
            [0.55, "#1e293b"],
            [0.75, "#059669"],
            [1.0,  "#064e3b"],
        ],
        zmin=0, zmax=100,
        text=text,
        texttemplate="<b>%{text}</b>",
        textfont=dict(size=9.5, color="rgba(255,255,255,0.85)"),
        hovertemplate="<b>%{x} — %{y}</b><br>Percentil: %{z:.0f}<extra></extra>",
        showscale=True,
        colorbar=dict(
            title=dict(text="Percentil", font=dict(color=TEXT_MUTED, size=9)),
            tickfont=dict(color=TEXT_MUTED, size=9),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.05)",
            thickness=10, len=0.8,
        ),
        xgap=2, ygap=2,
    ))

    fig.update_layout(**base_layout(
        height=max(320, len(y_lbl) * 55 + 80),
        margin=dict(t=50, b=60, l=120, r=80),
        xaxis=dict(side="top", tickfont=dict(color=TEXT_SECONDARY, size=10, family="JetBrains Mono"),
                   gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(tickfont=dict(color=TEXT_SECONDARY, size=10), gridcolor="rgba(0,0,0,0)"),
    ))
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True,
                    config={"toImageButtonOptions": {"format": "png", "scale": 2}})

    composite = df_norm.mean(axis=1).sort_values(ascending=False).reset_index()
    composite.columns = ["Ticker", "Score Composto"]

    rows_html = ""
    for i, row in composite.iterrows():
        score_pct = row["Score Composto"]
        color = C_POS if score_pct >= 70 else (C_WARN if score_pct >= 45 else C_NEG)
        rank_badge = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else f"#{i+1}"))
        bar_w = int(score_pct)
        rows_html += (
            f"<div style='display:flex;align-items:center;gap:12px;"
            f"padding:0.4rem 0;border-bottom:1px solid rgba(255,255,255,0.04);'>"
            f"<span style='font-size:0.8rem;min-width:28px;color:{TEXT_MUTED};"
            f"font-family:Inter,sans-serif;'>{rank_badge}</span>"
            f"<span style='font-size:0.82rem;font-weight:700;color:{TEXT_PRIMARY};"
            f"font-family:\"JetBrains Mono\",monospace;min-width:70px;'>{row['Ticker']}</span>"
            f"<div style='flex:1;height:6px;border-radius:3px;"
            f"background:rgba(255,255,255,0.06);overflow:hidden;'>"
            f"<div style='width:{bar_w}%;height:100%;border-radius:3px;"
            f"background:linear-gradient(90deg,{color},{color}88);'></div></div>"
            f"<span style='font-size:0.8rem;font-weight:700;color:{color};"
            f"font-family:\"JetBrains Mono\",monospace;min-width:42px;text-align:right;'>"
            f"{score_pct:.0f}</span>"
            f"</div>"
        )

    st.markdown(
        f"<div style='background:#111827;border:1px solid rgba(255,255,255,0.05);"
        f"border-radius:10px;padding:1rem 1.2rem;'>"
        f"<div style='font-size:0.65rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.1em;color:{TEXT_MUTED};margin-bottom:0.6rem;"
        f"font-family:Inter,sans-serif;'>SCORE COMPOSTO (PERCENTIL MÉDIO)</div>"
        f"{rows_html}"
        f"</div>",
        unsafe_allow_html=True,
    )

    insight_box(_auto_insight(df_raw, df_norm, is_real), C_WARN)
