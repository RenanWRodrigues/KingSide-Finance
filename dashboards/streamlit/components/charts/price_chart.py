"""Finance Charts — Gráfico de Preços Premium (TradingView style)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from .styles import (
    C_NEG, C_NEG2, C_NEUT, C_NEUT2, C_POS, C_POS2, C_WARN, C_PURPLE, C_CYAN,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, LEGEND_RIGHT, base_layout,
)
from .utils import (
    insight_box, kpi_card, section_header_charts,
    color_pos_neg, _generate_price_history, _seed,
)


def render_price_chart(
    df: pd.DataFrame | None = None,
    ticker: str = "TICKER",
    show_volume: bool = True,
    show_rsi: bool = True,
    show_macd: bool = True,
    ma_periods: list[int] | None = None,
) -> None:
    import random

    if df is None or df.empty:
        df = _generate_price_history(ticker)
        df["abertura"] = df["fechamento"].shift(1).fillna(df["fechamento"])
        df["maxima"]   = df["fechamento"] * 1.012
        df["minima"]   = df["fechamento"] * 0.990
        df["volume"]   = [random.Random(_seed(ticker)+i).uniform(2e6, 10e6) for i in range(len(df))]

    ma_periods = ma_periods or [20, 50, 200]
    closes = df["fechamento"]

    last   = closes.iloc[-1]
    prev   = closes.iloc[-2] if len(df) > 1 else last
    chg    = (last - prev) / prev * 100 if prev else 0
    h52w   = df.get("maxima", closes).max()
    l52w   = df.get("minima", closes).min()
    avg_v  = df["volume"].mean() if "volume" in df.columns else 0
    ret    = (last / closes.iloc[0] - 1) * 100 if closes.iloc[0] else 0

    section_header_charts(f"Análise de Preços — {ticker}", "Candlestick com Indicadores", C_NEUT)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(kpi_card("Preço", f"R$ {last:.2f}", f"{chg:+.2f}%",
                             chg >= 0, C_NEUT, "◉", list(closes.tail(20))), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Retorno", f"{ret:+.1f}%",
                             delta_positive=ret >= 0, accent=C_POS if ret >= 0 else C_NEG, icon="↗"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Máx 52s", f"R$ {h52w:.2f}", accent=C_POS2, icon="▲"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Mín 52s", f"R$ {l52w:.2f}", accent=C_NEG, icon="▼"), unsafe_allow_html=True)
    with c5:
        vol_str = f"{avg_v/1e6:.1f}M" if avg_v >= 1e6 else f"{avg_v/1e3:.0f}K"
        st.markdown(kpi_card("Vol. Médio", vol_str, accent=C_CYAN, icon="≈"), unsafe_allow_html=True)

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    n_rows = 1 + (1 if show_volume else 0) + (1 if show_rsi else 0) + (1 if show_macd else 0)
    heights = [0.55]
    if show_volume: heights.append(0.12)
    if show_rsi:    heights.append(0.16)
    if show_macd:   heights.append(0.17)
    # Normalize
    total = sum(heights)
    heights = [h / total for h in heights]

    titles = [f"{ticker} — Preço"]
    if show_volume: titles.append("Volume")
    if show_rsi:    titles.append("RSI(14)")
    if show_macd:   titles.append("MACD")

    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        row_heights=heights,
        subplot_titles=titles,
    )

    row = 1

    # Candlestick
    if "abertura" in df.columns:
        fig.add_trace(go.Candlestick(
            x=df["data"], open=df["abertura"],
            high=df.get("maxima", df["fechamento"]),
            low=df.get("minima", df["fechamento"]),
            close=closes,
            name=ticker,
            increasing=dict(fillcolor=C_POS, line=dict(color=C_POS, width=1)),
            decreasing=dict(fillcolor=C_NEG, line=dict(color=C_NEG, width=1)),
        ), row=row, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=df["data"], y=closes, name=ticker, mode="lines",
            line=dict(color=C_NEUT, width=2), fill="tozeroy",
            fillcolor="rgba(59,130,246,0.06)",
        ), row=row, col=1)

    # Bollinger
    bb_ma  = closes.rolling(20).mean()
    bb_std = closes.rolling(20).std()
    bb_u   = bb_ma + 2 * bb_std
    bb_l   = bb_ma - 2 * bb_std
    fig.add_trace(go.Scatter(
        x=pd.concat([df["data"], df["data"].iloc[::-1]]),
        y=pd.concat([bb_u, bb_l.iloc[::-1]]),
        fill="toself", fillcolor="rgba(59,130,246,0.05)",
        line=dict(color="rgba(0,0,0,0)"), name="BB(20)", showlegend=True,
    ), row=row, col=1)

    # MAs
    ma_colors = {"20": "#3B82F6", "50": "#F59E0B", "200": "#8B5CF6"}
    for period in ma_periods:
        if len(df) >= period:
            ma = closes.rolling(period).mean()
            fig.add_trace(go.Scatter(
                x=df["data"], y=ma, name=f"MM{period}",
                line=dict(color=ma_colors.get(str(period), "#94A3B8"), width=1.3),
            ), row=row, col=1)

    # Volume
    if show_volume and "volume" in df.columns:
        row += 1
        vol_colors = [C_POS if c >= o else C_NEG
                      for c, o in zip(df["fechamento"], df.get("abertura", df["fechamento"]))]
        fig.add_trace(go.Bar(
            x=df["data"], y=df["volume"],
            marker=dict(color=vol_colors, opacity=0.65),
            name="Volume", showlegend=False,
        ), row=row, col=1)

    # RSI
    if show_rsi:
        row += 1
        delta = closes.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, np.nan)
        rsi   = 100 - 100 / (1 + rs)
        fig.add_trace(go.Scatter(
            x=df["data"], y=rsi, name="RSI(14)",
            line=dict(color=C_PURPLE, width=1.8),
            fill="tozeroy", fillcolor="rgba(139,92,246,0.07)",
        ), row=row, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="rgba(239,68,68,0.33)", row=row, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="rgba(16,185,129,0.33)", row=row, col=1)
        fig.update_yaxes(range=[0, 100], row=row, col=1)

    # MACD
    if show_macd:
        row += 1
        ema12  = closes.ewm(span=12).mean()
        ema26  = closes.ewm(span=26).mean()
        macd   = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        hist   = macd - signal
        hist_colors = [C_POS if v >= 0 else C_NEG for v in hist]
        fig.add_trace(go.Bar(
            x=df["data"], y=hist,
            marker=dict(color=hist_colors, opacity=0.7),
            showlegend=False,
        ), row=row, col=1)
        fig.add_trace(go.Scatter(x=df["data"], y=macd, name="MACD",
                                  line=dict(color=C_NEUT, width=1.4)), row=row, col=1)
        fig.add_trace(go.Scatter(x=df["data"], y=signal, name="Signal",
                                  line=dict(color=C_WARN, width=1.4, dash="dash")), row=row, col=1)

    total_h = 480 + 80 * (n_rows - 1)
    fig.update_layout(**base_layout(
        height=total_h,
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        legend=LEGEND_RIGHT,
        margin=dict(r=150),
    ))

    for r in range(1, n_rows + 1):
        fig.update_xaxes(title_text="", gridcolor="rgba(255,255,255,0.02)",
                         tickfont=dict(color=TEXT_MUTED, size=9), row=r, col=1)
        fig.update_yaxes(title_text="", gridcolor="rgba(255,255,255,0.025)",
                         tickfont=dict(color=TEXT_MUTED, size=9), row=r, col=1)

    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "toImageButtonOptions": {"format": "png", "scale": 2},
    })
