"""Finance Charts — Margem Líquida Histórica (inspirado no estilo CEMIG)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .styles import (
    BG_CARD, BORDER, C_NEG, C_NEG2, C_NEUT2, C_POS, C_POS2, C_WARN,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, PALETTE, base_layout,
)
from .utils import (
    glow_line_trace, hex_alpha, insight_box, kpi_card, make_quarterly_df,
    section_header_charts, color_pos_neg,
)


def _auto_insight(df: pd.DataFrame, col: str = "margem_liquida") -> str:
    vals = df[col].dropna().tolist()
    if not vals:
        return ""
    trend_last4 = vals[-1] - vals[-5] if len(vals) >= 5 else vals[-1] - vals[0]
    avg = float(np.mean(vals))
    cur = vals[-1]
    pct_vs_avg = (cur - avg) / avg * 100 if avg else 0

    if trend_last4 > 1 and cur > avg:
        return (
            "A empresa apresentou expansão consistente da margem nos últimos períodos, "
            f"com a margem atual de {cur:.1f}% superando a média histórica de {avg:.1f}%. "
            "Isso indica ganho operacional e maior eficiência na conversão de receita em lucro."
        )
    if trend_last4 < -1 and cur < avg:
        return (
            f"A margem recuou nos últimos trimestres, situando-se {abs(pct_vs_avg):.1f}% abaixo da "
            "média histórica. Atenção à pressão de custos ou deterioração do mix de produtos."
        )
    return (
        f"A margem oscila em torno de {avg:.1f}%, com o nível atual de {cur:.1f}% "
        "dentro do intervalo histórico. Empresa mantém desempenho operacional estável."
    )


def render_margin_chart(
    df: pd.DataFrame | None = None,
    ticker: str = "TICKER",
    col: str = "margem_liquida",
    title: str = "Margem Líquida Histórica",
    color: str = C_POS,
    unit: str = "%",
) -> None:
    if df is None or df.empty:
        df = make_quarterly_df(ticker)

    df = df.copy().sort_values("data" if "data" in df.columns else df.columns[0])
    x_col = "data" if "data" in df.columns else df.columns[0]
    y = df[col].values
    x = df[x_col].values

    avg_val  = float(np.nanmean(y))
    cur_val  = float(y[-1])
    min_val  = float(np.nanmin(y))
    max_val  = float(np.nanmax(y))
    min_idx  = int(np.nanargmin(y))
    max_idx  = int(np.nanargmax(y))

    section_header_charts(title, f"{ticker} · Histórico trimestral", color)

    c1, c2, c3, c4 = st.columns(4)
    sparkline_data = list(y[-12:])
    with c1:
        st.markdown(kpi_card("Atual", f"{cur_val:.1f}{unit}",
                             f"{cur_val - avg_val:+.1f}{unit} vs média",
                             cur_val >= avg_val, color, "◉",
                             sparkline_data), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Média Histórica", f"{avg_val:.1f}{unit}",
                             accent=C_NEUT2, icon="≈"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Maior Histórico", f"{max_val:.1f}{unit}",
                             accent=C_POS2, icon="▲"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Menor Histórico", f"{min_val:.1f}{unit}",
                             accent=C_NEG, icon="▼"), unsafe_allow_html=True)

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    fig = go.Figure()

    # Gradient fill area under the line
    for trace in glow_line_trace(x, y, title, color, width=2.8, fill=True, fill_opacity=0.12):
        fig.add_trace(trace)

    # Average dashed line
    fig.add_hline(
        y=avg_val,
        line_dash="dot",
        line_color="rgba(148,163,184,0.45)",
        line_width=1.5,
        annotation_text=f"Média {avg_val:.1f}{unit}",
        annotation_position="top right",
        annotation_font_color=TEXT_SECONDARY,
        annotation_font_size=10,
    )

    # Max point highlight
    fig.add_trace(go.Scatter(
        x=[x[max_idx]], y=[max_val],
        mode="markers+text",
        marker=dict(color=C_POS2, size=10, symbol="circle",
                    line=dict(color="rgba(52,211,153,0.3)", width=6)),
        text=[f"Max: {max_val:.1f}{unit}"],
        textposition="top center",
        textfont=dict(color=C_POS2, size=9, family="JetBrains Mono"),
        showlegend=False, hoverinfo="skip",
    ))

    # Min point highlight
    fig.add_trace(go.Scatter(
        x=[x[min_idx]], y=[min_val],
        mode="markers+text",
        marker=dict(color=C_NEG, size=10, symbol="circle",
                    line=dict(color="rgba(239,68,68,0.3)", width=6)),
        text=[f"Min: {min_val:.1f}{unit}"],
        textposition="bottom center",
        textfont=dict(color=C_NEG, size=9, family="JetBrains Mono"),
        showlegend=False, hoverinfo="skip",
    ))

    # Current value annotation
    fig.add_trace(go.Scatter(
        x=[x[-1]], y=[cur_val],
        mode="markers",
        marker=dict(color=color, size=12, symbol="circle",
                    line=dict(color=hex_alpha(color, 0.33), width=8)),
        showlegend=False,
        hovertemplate=f"<b>Atual</b><br>{cur_val:.1f}{unit}<extra></extra>",
    ))

    layout = base_layout(
        title=dict(text=f"{title} — {ticker}", font=dict(size=13, color=TEXT_PRIMARY)),
        height=380,
        hovermode="x unified",
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.035)",
            ticksuffix=unit,
            tickfont=dict(color=TEXT_MUTED, size=10),
            zeroline=False,
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.025)",
            tickfont=dict(color=TEXT_MUTED, size=10),
            type="date" if hasattr(x[0], "year") or isinstance(x[0], pd.Timestamp) else "-",
        ),
        showlegend=False,
    )
    fig.update_layout(**layout)

    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True,
                                                             "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                                                             "toImageButtonOptions": {"format": "png", "scale": 2}})

    insight_box(_auto_insight(df, col), color)
