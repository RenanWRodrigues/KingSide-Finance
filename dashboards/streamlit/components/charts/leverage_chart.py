"""Finance Charts — Alavancagem Financeira (Dívida Líquida / EBITDA)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .styles import (
    BG_CARD, C_NEG, C_POS, C_POS2, C_WARN, TEXT_MUTED,
    TEXT_PRIMARY, TEXT_SECONDARY, base_layout,
)
from .utils import (
    glow_line_trace, hex_alpha, insight_box, kpi_card,
    leverage_color, make_annual_df, section_header_charts,
)


def _classify_leverage(ratio: float) -> tuple[str, str]:
    if ratio <= 1.5:
        return "Saudável", C_POS
    if ratio <= 3.0:
        return "Moderada", C_WARN
    return "Arriscada", C_NEG


def _auto_insight(df: pd.DataFrame) -> str:
    vals = df["alavancagem"].dropna().tolist()
    if not vals:
        return ""
    cur, avg = vals[-1], float(np.mean(vals))
    lbl, _ = _classify_leverage(cur)
    trend = vals[-1] - vals[-3] if len(vals) >= 3 else 0

    if lbl == "Saudável" and trend < 0:
        return (
            f"A alavancagem de {cur:.1f}x EBITDA é considerada saudável e está em trajetória "
            "de desalavancagem, sinalizando solidez financeira e capacidade de reinvestimento."
        )
    if lbl == "Moderada":
        return (
            f"A relação Dívida Líq./EBITDA de {cur:.1f}x está em nível moderado. "
            "Monitorar a evolução do endividamento nos próximos trimestres é recomendado."
        )
    return (
        f"Alavancagem em {cur:.1f}x EBITDA, acima do limiar prudente de 3x. "
        "Risco financeiro elevado pode comprometer a flexibilidade operacional."
    )


def render_leverage_chart(
    df: pd.DataFrame | None = None,
    ticker: str = "TICKER",
) -> None:
    if df is None or df.empty:
        df = make_annual_df(ticker)

    df = df.copy().dropna(subset=["alavancagem"])
    x = df["ano"].astype(str).values
    y = df["alavancagem"].values

    cur_val  = float(y[-1])
    avg_val  = float(np.nanmean(y))
    min_val  = float(np.nanmin(y))
    max_val  = float(np.nanmax(y))
    lbl, cur_color = _classify_leverage(cur_val)

    section_header_charts(
        "Alavancagem Financeira",
        f"{ticker} · Dívida Líquida / EBITDA Ajustado",
        cur_color,
    )

    c1, c2, c3, c4 = st.columns(4)
    spark = list(y[-8:])
    with c1:
        st.markdown(kpi_card(
            "Atual", f"{cur_val:.1f}x",
            f"Classificação: {lbl}",
            cur_val <= 2.0, cur_color, "◈", spark,
        ), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Média Histórica", f"{avg_val:.1f}x", accent="#3B82F6", icon="≈"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Menor Histórico", f"{min_val:.1f}x", accent=C_POS2, icon="▼"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Maior Histórico", f"{max_val:.1f}x", accent=C_NEG, icon="▲"), unsafe_allow_html=True)

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    fig = go.Figure()

    # Risk zones background shading
    fig.add_hrect(y0=0,   y1=1.5, fillcolor="rgba(16,185,129,0.04)", line_width=0, layer="below")
    fig.add_hrect(y0=1.5, y1=3.0, fillcolor="rgba(245,158,11,0.04)", line_width=0, layer="below")
    fig.add_hrect(y0=3.0, y1=max(max_val * 1.3, 6), fillcolor="rgba(239,68,68,0.04)", line_width=0, layer="below")

    # Threshold lines
    for threshold, label, tcolor in [(1.5, "Saudável ≤ 1.5x", C_POS), (3.0, "Risco > 3.0x", C_NEG)]:
        fig.add_hline(
            y=threshold, line_dash="dot", line_color=hex_alpha(tcolor, 0.33), line_width=1.2,
            annotation_text=label,
            annotation_position="top left",
            annotation_font=dict(color=tcolor, size=9),
        )

    # Glow line
    for trace in glow_line_trace(x, y, "Alavancagem", cur_color, width=3.0, fill=True, fill_opacity=0.15):
        fig.add_trace(trace)

    # Data point labels on every bar
    for xi, yi in zip(x, y):
        fig.add_annotation(
            x=xi, y=yi,
            text=f"<b>{yi:.1f}x</b>",
            showarrow=False,
            yshift=14,
            font=dict(color=leverage_color(yi), size=9, family="JetBrains Mono"),
        )

    # Current highlight
    fig.add_trace(go.Scatter(
        x=[x[-1]], y=[cur_val],
        mode="markers",
        marker=dict(color=cur_color, size=13, symbol="circle",
                    line=dict(color=hex_alpha(cur_color, 0.33), width=10)),
        showlegend=False,
        hovertemplate=f"<b>{x[-1]}</b><br>Alavancagem: {cur_val:.1f}x<br>Status: {lbl}<extra></extra>",
    ))

    layout = base_layout(
        title=dict(text=f"Dívida Líquida / EBITDA — {ticker}", font=dict(size=13, color=TEXT_PRIMARY)),
        height=400,
        hovermode="x unified",
        yaxis=dict(ticksuffix="x", zeroline=False, gridcolor="rgba(255,255,255,0.03)",
                   tickfont=dict(color=TEXT_MUTED, size=10)),
        xaxis=dict(tickfont=dict(color=TEXT_MUTED, size=10), gridcolor="rgba(0,0,0,0)"),
        showlegend=False,
    )
    fig.update_layout(**layout)

    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True,
                                                             "toImageButtonOptions": {"format": "png", "scale": 2}})

    # Classification badge
    badge_bg = "rgba(16,185,129,0.12)" if lbl == "Saudável" else ("rgba(245,158,11,0.12)" if lbl == "Moderada" else "rgba(239,68,68,0.12)")
    st.markdown(
        f"<div style='display:inline-flex;align-items:center;gap:8px;"
        f"background:{badge_bg};border:1px solid {cur_color}44;"
        f"border-radius:20px;padding:4px 14px;margin-bottom:0.5rem;'>"
        f"<span style='color:{cur_color};font-size:0.7rem;font-weight:800;"
        f"letter-spacing:0.06em;font-family:Inter,sans-serif;'>◈ {lbl.upper()}</span>"
        f"<span style='color:{TEXT_MUTED};font-size:0.68rem;font-family:Inter,sans-serif;'>"
        f"Alavancagem atual: {cur_val:.1f}x</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    insight_box(_auto_insight(df), cur_color)
