"""Finance Charts — EBITDA Recorrente x Lucro Líquido Recorrente (Glassmorphism Cards)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .styles import (
    BG_CARD, BG_CARD2, BORDER, C_NEG, C_NEUT, C_POS, C_POS2, C_WARN, C_PURPLE,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, LEGEND_RIGHT, base_layout,
)
from .utils import (
    insight_box, kpi_card, make_annual_df, section_header_charts,
    _sparkline_svg, _fmt_brl, _chart_scale,
)


def _glasscard(
    title: str,
    current: float,
    prev: float,
    unit: str = "M",
    color: str = C_POS,
    icon: str = "◆",
    sparkline: list[float] | None = None,
) -> str:
    delta = current - prev
    delta_pct = (delta / abs(prev) * 100) if prev != 0 else 0
    is_pos = delta >= 0
    arrow = "▲" if is_pos else "▼"
    delta_color = C_POS if is_pos else C_NEG
    spark_html = _sparkline_svg(sparkline or [], color) if sparkline else ""

    return (
        f"<div style='background:linear-gradient(135deg,{BG_CARD} 0%,{BG_CARD2} 100%);"
        f"border:1px solid {BORDER};border-top:2px solid {color};"
        f"border-radius:12px;padding:1.25rem 1.35rem;position:relative;overflow:hidden;"
        f"box-shadow:0 4px 24px rgba(0,0,0,0.4);backdrop-filter:blur(4px);'>"
        f"<div style='font-size:0.62rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.1em;color:{TEXT_MUTED};font-family:Inter,sans-serif;"
        f"margin-bottom:0.5rem;'>{icon} {title}</div>"
        f"<div style='font-size:1.6rem;font-weight:800;color:{TEXT_PRIMARY};"
        f"font-family:\"JetBrains Mono\",monospace;letter-spacing:-0.03em;"
        f"line-height:1.1;'>{_fmt_brl(current)}</div>"
        f"<div style='font-size:0.78rem;margin-top:0.35rem;'>"
        f"<span style='color:{delta_color};font-weight:700;font-family:\"JetBrains Mono\",monospace;'>"
        f"{arrow} {delta_pct:+.1f}%</span>"
        f"<span style='color:{TEXT_MUTED};font-family:Inter,sans-serif;margin-left:6px;'>"
        f"vs ano anterior</span>"
        f"</div>"
        f"<div style='margin-top:0.6rem;height:3px;border-radius:2px;"
        f"background:linear-gradient(90deg,{color},{color}44);width:{min(abs(delta_pct)*2,100):.0f}%;'>"
        f"</div>"
        f"{spark_html}"
        f"</div>"
    )


def _auto_insight(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    ebitda = df["ebitda"].tolist()
    lucro  = df["lucro_liquido"].tolist()
    conv   = [l / e * 100 for l, e in zip(lucro, ebitda) if e]

    conv_trend = conv[-1] - conv[-3] if len(conv) >= 3 else 0
    ebitda_cagr = ((ebitda[-1] / ebitda[0]) ** (1 / max(len(ebitda) - 1, 1)) - 1) * 100

    if ebitda_cagr > 8 and conv_trend > 0:
        return (
            f"EBITDA crescendo a {ebitda_cagr:.1f}% a.a. com melhora na conversão para lucro "
            f"(+{conv_trend:.1f}p.p. em 3 anos). Indicativo de alavancagem operacional positiva."
        )
    if conv[-1] < 30:
        return (
            f"Conversão EBITDA→Lucro de apenas {conv[-1]:.1f}%, abaixo do padrão setorial. "
            "Atenção às despesas financeiras e carga tributária efetiva."
        )
    return (
        f"EBITDA com CAGR de {ebitda_cagr:.1f}% a.a. Conversão para lucro líquido de "
        f"{conv[-1]:.1f}% — consistência operacional dentro do esperado para o setor."
    )


def render_recurring_results(
    df: pd.DataFrame | None = None,
    ticker: str = "TICKER",
) -> None:
    if df is None or df.empty:
        df = make_annual_df(ticker)

    df = df.copy().sort_values("ano")

    section_header_charts(
        "EBITDA Recorrente × Lucro Líquido Recorrente",
        f"{ticker} · Consistência Operacional",
        C_POS,
    )

    ebitda_vals = df["ebitda"].tolist()
    lucro_vals  = df["lucro_liquido"].tolist()
    anos        = df["ano"].astype(str).tolist()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            _glasscard(
                "EBITDA Recorrente",
                ebitda_vals[-1],
                ebitda_vals[-2] if len(ebitda_vals) >= 2 else ebitda_vals[-1],
                color=C_NEUT,
                icon="≈",
                sparkline=ebitda_vals[-8:],
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _glasscard(
                "Lucro Líquido Recorrente",
                lucro_vals[-1],
                lucro_vals[-2] if len(lucro_vals) >= 2 else lucro_vals[-1],
                color=C_POS,
                icon="◆",
                sparkline=lucro_vals[-8:],
            ),
            unsafe_allow_html=True,
        )

    scale, unit = _chart_scale(ebitda_vals + lucro_vals)
    e_scaled = [v / scale for v in ebitda_vals]
    l_scaled = [v / scale for v in lucro_vals]

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # Bar chart EBITDA vs Lucro comparison
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=anos, y=e_scaled,
        name="EBITDA",
        marker=dict(
            color=[f"rgba(59,130,246,{0.4 + 0.35 * i / max(len(anos)-1,1)})" for i in range(len(anos))],
            line=dict(color="rgba(59,130,246,0.7)", width=0.5),
        ),
        hovertemplate=f"<b>EBITDA %{{x}}</b><br>R$ %{{y:,.2f}}{unit}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        x=anos, y=l_scaled,
        name="Lucro Líquido",
        marker=dict(
            color=[f"rgba(16,185,129,{0.4 + 0.35 * i / max(len(anos)-1,1)})" for i in range(len(anos))],
            line=dict(color="rgba(16,185,129,0.7)", width=0.5),
        ),
        hovertemplate=f"<b>Lucro %{{x}}</b><br>R$ %{{y:,.2f}}{unit}<extra></extra>",
    ))

    # Conversão % line
    conversao = [l / e * 100 for l, e in zip(lucro_vals, ebitda_vals) if e]
    fig.add_trace(go.Scatter(
        x=anos[:len(conversao)], y=conversao,
        name="Conv. EBITDA→Lucro (%)",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color=C_WARN, width=2, dash="dot"),
        marker=dict(size=5, color=C_WARN),
        hovertemplate="%{x}<br>Conversão: %{y:.1f}%<extra></extra>",
    ))

    fig.update_layout(**base_layout(
        height=400,
        hovermode="x unified",
        barmode="group",
        bargroupgap=0.12,
        yaxis=dict(tickprefix="R$ ", ticksuffix=unit, gridcolor="rgba(255,255,255,0.03)",
                   tickfont=dict(color=TEXT_MUTED, size=10)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=TEXT_MUTED, size=10)),
        yaxis2=dict(overlaying="y", side="right", ticksuffix="%",
                    tickfont=dict(color=C_WARN, size=9), showgrid=False),
        legend=LEGEND_RIGHT,
        margin=dict(r=150),
    ))

    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True, config={"toImageButtonOptions": {"format": "png", "scale": 2}})
    insight_box(_auto_insight(df), C_POS)
