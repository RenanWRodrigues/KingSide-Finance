"""Finance Charts — Patrimônio x Dívida Bruta x Dívida Líquida."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from .styles import (
    C_NEG, C_NEUT, C_POS, C_WARN, C_PURPLE, C_CYAN,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, LEGEND_RIGHT, base_layout,
)
from .utils import (
    insight_box, kpi_card, make_annual_df, section_header_charts,
    _fmt_brl, _chart_scale,
)


def _auto_insight(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    pat = df["patrimonio_liquido"].tolist()
    db  = df["divida_bruta"].tolist()
    dl  = df["divida_liquida"].tolist()

    pat_growth = (pat[-1] / pat[0] - 1) * 100 if pat[0] else 0
    debt_growth = (db[-1] / db[0] - 1) * 100 if db[0] else 0
    cover = pat[-1] / db[-1] if db[-1] else 0

    if pat_growth > debt_growth and cover > 0.8:
        return (
            f"Patrimônio cresceu {pat_growth:.0f}% no período, superando o crescimento "
            f"da dívida bruta ({debt_growth:.0f}%), com cobertura patrimonial de {cover:.1f}x. "
            "Estrutura de capital sólida com tendência de fortalecimento."
        )
    if cover < 0.5:
        return (
            f"Dívida bruta supera significativamente o patrimônio (cobertura de {cover:.1f}x). "
            "Estrutura de capital alavancada — risco financeiro elevado a ser monitorado."
        )
    return (
        f"Patrimônio líquido atual cobre {cover:.1f}x a dívida bruta. "
        f"Crescimento patrimonial de {pat_growth:.0f}% no período analisado."
    )


def render_patrimony_vs_debt(
    df: pd.DataFrame | None = None,
    ticker: str = "TICKER",
) -> None:
    if df is None or df.empty:
        df = make_annual_df(ticker)

    df = df.copy().sort_values("ano")
    anos = df["ano"].astype(str).tolist()
    patrimonio = df["patrimonio_liquido"].tolist()
    div_bruta  = df["divida_bruta"].tolist()
    div_liq    = df["divida_liquida"].tolist()

    cover = patrimonio[-1] / div_bruta[-1] if div_bruta[-1] else 0
    pat_yoy = (patrimonio[-1] / patrimonio[-2] - 1) * 100 if len(patrimonio) >= 2 and patrimonio[-2] else 0

    section_header_charts(
        "Estrutura de Capital",
        f"{ticker} · Patrimônio × Dívida Bruta × Dívida Líquida",
        C_NEUT,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("Patrimônio Líq.", _fmt_brl(patrimonio[-1]),
                             f"YoY {pat_yoy:+.1f}%", pat_yoy >= 0, C_POS, "◈"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Dívida Bruta", _fmt_brl(div_bruta[-1]),
                             accent=C_NEG, icon="▼"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Dívida Líquida", _fmt_brl(div_liq[-1]),
                             accent=C_WARN, icon="≈"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Cobertura", f"{cover:.1f}x",
                             "Patrim. / Dív. Bruta", cover >= 0.8, C_CYAN, "⊞"), unsafe_allow_html=True)

    scale, unit = _chart_scale(patrimonio + div_bruta + [v for v in div_liq if v is not None])
    pat_s  = [v / scale for v in patrimonio]
    db_s   = [v / scale for v in div_bruta]
    dl_s   = [v / scale for v in div_liq]

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=anos, y=pat_s,
        name="Patrimônio Líquido",
        marker=dict(
            color="rgba(16,185,129,0.55)",
            line=dict(color="rgba(16,185,129,0.8)", width=0.5),
        ),
        hovertemplate=f"<b>Patrimônio %{{x}}</b><br>R$ %{{y:,.2f}}{unit}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        x=anos, y=db_s,
        name="Dívida Bruta",
        marker=dict(
            color="rgba(239,68,68,0.40)",
            line=dict(color="rgba(239,68,68,0.65)", width=0.5),
        ),
        hovertemplate=f"<b>Dívida Bruta %{{x}}</b><br>R$ %{{y:,.2f}}{unit}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=anos, y=dl_s,
        name="Dívida Líquida",
        mode="lines+markers",
        line=dict(color=C_WARN, width=2.5, shape="spline", smoothing=0.3),
        marker=dict(color=C_WARN, size=7, line=dict(color="rgba(245,158,11,0.35)", width=5)),
        hovertemplate=f"<b>Dív. Líquida %{{x}}</b><br>R$ %{{y:,.2f}}{unit}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=anos, y=pat_s,
        name="Tendência Patrim.",
        mode="lines",
        line=dict(color=C_POS, width=1.5, dash="dot"),
        opacity=0.6,
        showlegend=False,
        hoverinfo="skip",
    ))

    fig.update_layout(**base_layout(
        height=440,
        hovermode="x unified",
        barmode="group",
        bargroupgap=0.12,
        bargap=0.18,
        yaxis=dict(tickprefix="R$ ", ticksuffix=unit, gridcolor="rgba(255,255,255,0.035)",
                   tickfont=dict(color=TEXT_MUTED, size=10)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=TEXT_MUTED, size=10)),
        legend=LEGEND_RIGHT,
        margin=dict(r=150),
    ))

    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True, config={"toImageButtonOptions": {"format": "png", "scale": 2}})
    insight_box(_auto_insight(df), C_NEUT)
