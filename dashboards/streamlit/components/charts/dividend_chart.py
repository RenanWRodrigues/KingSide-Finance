"""Finance Charts — Histórico de Dividendos."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from .styles import (
    C_NEG, C_NEUT, C_POS, C_POS2, C_WARN, C_PURPLE, C_CYAN,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, LEGEND_RIGHT, base_layout,
)
from .utils import (
    insight_box, kpi_card, make_dividends_df, section_header_charts,
)


def _auto_insight(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    yld = df["yield_trimestral"].tolist()
    div = df["dividendo"].tolist()
    avg_yield = float(np.mean(yld)) * 4
    consistency = sum(1 for d in div if d > 0) / len(div) * 100

    if avg_yield > 6 and consistency > 90:
        return (
            f"DY anualizado médio de {avg_yield:.1f}% com consistência de {consistency:.0f}% "
            "nos pagamentos. Perfil de empresa pagadora com histórico sólido de remuneração ao acionista."
        )
    if consistency < 70:
        return (
            f"Histórico de pagamentos irregular ({consistency:.0f}% de consistência). "
            "Verificar política de dividendos e sazonalidade dos pagamentos antes de incluir no portfólio."
        )
    return (
        f"DY anualizado aproximado de {avg_yield:.1f}%. "
        f"Pagamentos com {consistency:.0f}% de regularidade histórica."
    )


def render_dividend_chart(
    df: pd.DataFrame | None = None,
    ticker: str = "TICKER",
) -> None:
    if df is None or df.empty:
        df = make_dividends_df(ticker)

    df = df.copy().sort_values("data")

    datas  = df["data"].values
    divs   = df["dividendo"].values
    yields = df["yield_trimestral"].values

    avg_yield_annual = float(np.mean(yields)) * 4
    total_12m = float(df.tail(4)["dividendo"].sum())
    last_div   = float(divs[-1])
    max_div    = float(np.max(divs))

    section_header_charts(
        "Histórico de Dividendos",
        f"{ticker} · Proventos Trimestrais e Dividend Yield",
        C_WARN,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("Último Dividendo", f"R$ {last_div:.3f}",
                             accent=C_WARN, icon="◈", sparkline=list(divs[-8:])), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("DY Anualizado", f"{avg_yield_annual:.1f}%",
                             accent=C_POS, icon="◆"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Total 12M", f"R$ {total_12m:.3f}",
                             accent=C_NEUT, icon="⊞"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Máximo Histórico", f"R$ {max_div:.3f}",
                             accent=C_POS2, icon="▲"), unsafe_allow_html=True)

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.65, 0.35],
        subplot_titles=[f"Proventos por Ação — {ticker}", "Dividend Yield Trimestral (%)"],
    )

    # Dividend bars with gradient coloring
    bar_colors = [f"rgba(245,158,11,{0.4 + 0.5 * d / max_div})" for d in divs]
    fig.add_trace(go.Bar(
        x=datas, y=divs,
        name="Dividendo (R$)",
        marker=dict(color=bar_colors, line=dict(color="rgba(245,158,11,0.6)", width=0.5)),
        hovertemplate="%{x|%d/%m/%Y}<br>Dividendo: R$ %{y:.4f}<extra></extra>",
    ), row=1, col=1)

    # Trend line
    if len(divs) >= 4:
        from numpy.polynomial import polynomial as P
        xs = np.arange(len(divs))
        coef = P.polyfit(xs, divs, 1)
        trend = P.polyval(xs, coef)
        fig.add_trace(go.Scatter(
            x=datas, y=trend,
            name="Tendência",
            mode="lines",
            line=dict(color="rgba(245,158,11,0.4)", width=1.5, dash="dot"),
            showlegend=False,
        ), row=1, col=1)

    # Yield area
    fig.add_trace(go.Scatter(
        x=datas, y=yields,
        name="DY Trimestral (%)",
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(16,185,129,0.08)",
        line=dict(color=C_POS, width=2, shape="spline"),
        hovertemplate="%{x|%d/%m/%Y}<br>DY: %{y:.2f}%<extra></extra>",
    ), row=2, col=1)

    fig.add_hline(
        y=float(np.mean(yields)),
        line_dash="dot", line_color="rgba(148,163,184,0.35)", line_width=1,
        annotation_text=f"Média {float(np.mean(yields)):.2f}%",
        annotation_font=dict(color=TEXT_SECONDARY, size=9),
        row=2, col=1,
    )

    fig.update_layout(**base_layout(
        height=460,
        hovermode="x unified",
        legend=LEGEND_RIGHT,
        margin=dict(r=150),
    ))
    fig.update_xaxes(title_text="", gridcolor="rgba(0,0,0,0)", tickfont=dict(color=TEXT_MUTED, size=10))
    fig.update_yaxes(title_text="", tickprefix="R$ ", gridcolor="rgba(255,255,255,0.03)",
                     tickfont=dict(color=TEXT_MUTED, size=10), row=1, col=1)
    fig.update_yaxes(title_text="", ticksuffix="%", gridcolor="rgba(255,255,255,0.025)",
                     tickfont=dict(color=TEXT_MUTED, size=10), row=2, col=1)

    st.plotly_chart(fig, use_container_width=True, config={"toImageButtonOptions": {"format": "png", "scale": 2}})
    insight_box(_auto_insight(df), C_WARN)
