"""Finance Charts — Receita x Lucro (Dual-Axis Bar + Line)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from .styles import (
    C_NEG, C_NEUT, C_NEUT2, C_POS, C_WARN, C_PURPLE,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
    BG_CARD, BORDER, LEGEND_RIGHT, base_layout,
)
from .utils import (
    insight_box, kpi_card, make_annual_df, section_header_charts,
    color_pos_neg, _fmt_brl, _chart_scale,
)


def _cagr(first: float, last: float, n: int) -> float:
    if first <= 0 or n <= 0:
        return 0.0
    return ((last / first) ** (1 / n) - 1) * 100


def _yoy(series: list[float]) -> list[float | None]:
    result: list[float | None] = [None]
    for i in range(1, len(series)):
        if series[i - 1] and series[i - 1] != 0:
            result.append((series[i] / series[i - 1] - 1) * 100)
        else:
            result.append(None)
    return result


def _auto_insight(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    n = len(df)
    rec = df["receita"].tolist()
    luc = df["lucro_liquido"].tolist()
    mar = df["margem_liquida"].tolist()

    cagr_rec = _cagr(rec[0], rec[-1], n - 1) if n > 1 else 0
    cagr_luc = _cagr(max(luc[0], 0.01), max(luc[-1], 0.01), n - 1) if n > 1 else 0
    mar_cur, mar_ini = mar[-1], mar[0]

    if cagr_rec > 5 and cagr_luc > cagr_rec:
        return (
            f"Receita cresce a CAGR de {cagr_rec:.1f}% a.a. com lucro avançando a "
            f"{cagr_luc:.1f}% a.a. — expansão de margem de {mar_ini:.1f}% para {mar_cur:.1f}%, "
            "indicando alavancagem operacional positiva e eficiência crescente."
        )
    if cagr_rec > 5:
        return (
            f"Receita cresce a {cagr_rec:.1f}% a.a. (CAGR), porém o lucro avança a "
            f"{cagr_luc:.1f}% a.a., com leve compressão de margem. "
            "Monitorar evolução dos custos e despesas financeiras."
        )
    return (
        f"Crescimento de receita moderado ({cagr_rec:.1f}% CAGR). "
        f"Margem líquida atual de {mar_cur:.1f}% — estabilidade operacional em linha com setor."
    )


def render_revenue_vs_profit(
    df: pd.DataFrame | None = None,
    ticker: str = "TICKER",
) -> None:
    if df is None or df.empty:
        df = make_annual_df(ticker)

    df = df.copy().sort_values("ano")
    anos = df["ano"].astype(str).tolist()
    receita = df["receita"].tolist()
    lucro   = df["lucro_liquido"].tolist()
    margem  = df["margem_liquida"].tolist()

    n = len(df)
    cagr_rec = _cagr(receita[0], receita[-1], n - 1) if n > 1 else 0
    cagr_luc = _cagr(max(lucro[0], 0.01), max(lucro[-1], 0.01), n - 1) if n > 1 else 0
    yoy_rec  = _yoy(receita)
    yoy_luc  = _yoy(lucro)

    section_header_charts(
        "Receita vs Lucro Líquido",
        f"{ticker} · Histórico Anual com Margem",
        C_NEUT,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("Receita Atual", _fmt_brl(receita[-1]),
                             f"CAGR {cagr_rec:+.1f}%", cagr_rec >= 0, C_NEUT, "⊞"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Lucro Atual", _fmt_brl(lucro[-1]),
                             f"CAGR {cagr_luc:+.1f}%", cagr_luc >= 0, C_POS, "◆"), unsafe_allow_html=True)
    with c3:
        delta_yoy = yoy_rec[-1]
        st.markdown(kpi_card("Receita YoY", f"{delta_yoy:+.1f}%" if delta_yoy is not None else "—",
                             delta_positive=delta_yoy >= 0 if delta_yoy is not None else None,
                             accent=C_WARN, icon="↗"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Margem Líquida", f"{margem[-1]:.1f}%",
                             f"vs {margem[0]:.1f}% inicial",
                             margem[-1] >= margem[0], C_PURPLE, "◎"), unsafe_allow_html=True)

    scale, unit = _chart_scale(receita + lucro)
    r_scaled = [v / scale for v in receita]
    l_scaled = [v / scale for v in lucro]

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.72, 0.28],
        subplot_titles=[f"Receita & Lucro — {ticker}", "Variação YoY (%)"],
    )

    # Receita bars
    fig.add_trace(go.Bar(
        x=anos, y=r_scaled,
        name="Receita Líquida",
        marker=dict(
            color=[f"rgba(59,130,246,{0.45 + i * 0.05 / n})" for i in range(n)],
            line=dict(color="rgba(59,130,246,0.6)", width=0.5),
        ),
        hovertemplate=f"<b>Receita %{{x}}</b><br>R$ %{{y:,.2f}}{unit}<extra></extra>",
    ), row=1, col=1)

    # Lucro bars
    fig.add_trace(go.Bar(
        x=anos, y=l_scaled,
        name="Lucro Líquido",
        marker=dict(
            color=[f"rgba(16,185,129,{0.50 + i * 0.04 / n})" for i in range(n)],
            line=dict(color="rgba(16,185,129,0.7)", width=0.5),
        ),
        hovertemplate=f"<b>Lucro %{{x}}</b><br>R$ %{{y:,.2f}}{unit}<extra></extra>",
    ), row=1, col=1)

    # Margem line on secondary Y
    fig.add_trace(go.Scatter(
        x=anos, y=margem,
        name="Margem Líquida (%)",
        mode="lines+markers",
        line=dict(color=C_WARN, width=2.2, shape="spline", smoothing=0.3),
        marker=dict(color=C_WARN, size=6, line=dict(color="rgba(245,158,11,0.4)", width=4)),
        yaxis="y3",
        hovertemplate="<b>Margem %{x}</b><br>%{y:.1f}%<extra></extra>",
    ), row=1, col=1)

    # YoY bars
    yoy_colors = [color_pos_neg(v, True) if v is not None else "#475569" for v in yoy_rec]
    fig.add_trace(go.Bar(
        x=anos, y=[v if v is not None else 0 for v in yoy_rec],
        name="Receita YoY",
        marker=dict(color=yoy_colors, opacity=0.75),
        hovertemplate="%{x}<br>YoY Receita: %{y:+.1f}%<extra></extra>",
    ), row=2, col=1)

    # Layout
    fig.update_layout(
        **base_layout(
            height=520,
            hovermode="x unified",
            barmode="group",
            bargroupgap=0.15,
            bargap=0.2,
            showlegend=True,
            legend=LEGEND_RIGHT,
            margin=dict(r=150),
        )
    )

    for row in [1, 2]:
        fig.update_xaxes(title_text="", gridcolor="rgba(0,0,0,0)", tickfont=dict(color=TEXT_MUTED, size=10), row=row, col=1)
    fig.update_yaxes(title_text="", gridcolor="rgba(255,255,255,0.035)", tickprefix="R$ ", ticksuffix=unit,
                     tickfont=dict(color=TEXT_MUTED, size=10), row=1, col=1)
    fig.update_yaxes(title_text="", gridcolor="rgba(255,255,255,0.025)", ticksuffix="%",
                     tickfont=dict(color=TEXT_MUTED, size=10), row=2, col=1)
    fig.update_layout(
        yaxis3=dict(
            title={"text": ""},
            overlaying="y",
            side="right",
            ticksuffix="%",
            tickfont=dict(color=C_WARN, size=9),
            showgrid=False,
            zeroline=False,
        )
    )

    st.plotly_chart(fig, use_container_width=True, config={"toImageButtonOptions": {"format": "png", "scale": 2}})

    # CAGR badges
    st.markdown(
        f"<div style='display:flex;gap:0.6rem;flex-wrap:wrap;margin-bottom:0.4rem;'>"
        f"<span style='background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.25);"
        f"border-radius:20px;padding:3px 12px;font-size:0.68rem;font-weight:700;"
        f"color:#3B82F6;font-family:Inter,sans-serif;'>CAGR Receita: {cagr_rec:.1f}%</span>"
        f"<span style='background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.25);"
        f"border-radius:20px;padding:3px 12px;font-size:0.68rem;font-weight:700;"
        f"color:#10B981;font-family:Inter,sans-serif;'>CAGR Lucro: {cagr_luc:.1f}%</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    insight_box(_auto_insight(df), C_NEUT)
