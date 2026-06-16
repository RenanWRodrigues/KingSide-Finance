"""Finance Charts — Análise de Sentimento Financeiro."""
from __future__ import annotations

import random
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .styles import (
    C_NEG, C_NEUT, C_NEUT2, C_POS, C_POS2, C_WARN, C_PURPLE, C_CYAN,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, base_layout,
)
from .utils import (
    insight_box, kpi_card, section_header_charts, _seed,
)


def _fetch_real_news(ticker: str) -> list[dict]:
    """Fetch real news headlines from yfinance for the given B3 ticker."""
    try:
        import yfinance as yf
        ticker_sa = ticker if ticker.endswith(".SA") else ticker + ".SA"
        news_raw = yf.Ticker(ticker_sa).news
        if not news_raw:
            return []
        results = []
        for item in news_raw[:8]:
            title = item.get("title", "").strip()
            if not title:
                continue
            ts = item.get("providerPublishTime", 0)
            date_str = (
                pd.to_datetime(ts, unit="s").strftime("%d/%m/%Y")
                if ts else "—"
            )
            results.append({
                "headline": title,
                "sentiment": "neutro",   # label — no NLP model available
                "score":     0.5,
                "impact":    "Médio",
                "data":      date_str,
                "real":      True,
            })
        return results
    except Exception:
        return []


def _generate_sentiment_data(ticker: str) -> dict:
    """Synthetic sentiment — used only when real news cannot be fetched."""
    rng = random.Random(_seed(ticker) + 30)
    positivo = rng.uniform(0.35, 0.65)
    negativo = rng.uniform(0.10, 0.35)
    neutro   = 1 - positivo - negativo
    score    = positivo - negativo

    headlines = [
        (f"{ticker} supera estimativas de lucro no último trimestre", "positivo"),
        (f"Analistas elevam preço-alvo de {ticker}", "positivo"),
        (f"{ticker} anuncia novo dividendo extraordinário", "positivo"),
        (f"{ticker} revisa guidance para baixo", "negativo"),
        (f"Pressão regulatória pode afetar {ticker}", "negativo"),
        (f"{ticker} mantém resultados em linha com consenso", "neutro"),
        (f"Setor de {ticker} enfrenta desafios macroeconômicos", "negativo"),
        (f"{ticker} assina contrato relevante com governo", "positivo"),
        (f"CEO de {ticker} comenta perspectivas para 2025", "neutro"),
        (f"{ticker} anuncia programa de recompra de ações", "positivo"),
    ]
    selected = rng.sample(headlines, min(6, len(headlines)))
    news = []
    for h, s in selected:
        sc = rng.uniform(0.6, 0.95) if s == "positivo" else (
            rng.uniform(0.55, 0.90) if s == "negativo" else rng.uniform(0.5, 0.75)
        )
        news.append({"headline": h, "sentiment": s, "score": sc,
                     "impact": rng.choice(["Alto", "Médio", "Baixo"]),
                     "data": "—", "real": False})

    n = 30
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="B")
    return {
        "positivo":        positivo,
        "negativo":        negativo,
        "neutro":          neutro,
        "composite_score": score,
        "news":            news,
        "dates":           dates,
        "sentiment_trend": [rng.uniform(-0.3, 0.8) for _ in range(n)],
        "is_real_news":    False,
    }


def _sentiment_label(score: float) -> tuple[str, str]:
    if score > 0.2:
        return "Positivo", C_POS
    if score < -0.1:
        return "Negativo", C_NEG
    return "Neutro", C_WARN


def _auto_insight(data: dict) -> str:
    score   = data["composite_score"]
    pos_pct = data["positivo"] * 100
    lbl, _  = _sentiment_label(score)
    trend   = data["sentiment_trend"]
    trend_3d = float(np.mean(trend[-3:])) if len(trend) >= 3 else score
    real_note = " (score ilustrativo — sem modelo NLP ativo)" if not data.get("is_real_news") else ""

    if lbl == "Positivo" and trend_3d > 0.1:
        return (
            f"Sentimento predominantemente positivo ({pos_pct:.0f}% das notícias){real_note}. "
            "Tendência de melhora recente. Fluxo de notícias favorável pode suportar pressão compradora."
        )
    if lbl == "Negativo":
        return (
            f"Sentimento de mercado negativo{real_note}. "
            "Monitorar catalisadores que possam reverter o fluxo de notícias."
        )
    return (
        f"Sentimento neutro com escore composto de {score:+.2f}{real_note}. "
        "Mercado aguarda catalisadores mais claros para definição de tendência."
    )


def render_sentiment_chart(
    data: dict | None = None,
    ticker: str = "TICKER",
) -> None:
    is_real_news = False

    if data is None:
        # Try real yfinance news first
        real_news = _fetch_real_news(ticker)
        base = _generate_sentiment_data(ticker)

        if real_news:
            base["news"] = real_news
            base["is_real_news"] = True
            is_real_news = True
        data = base

    score = data["composite_score"]
    lbl, score_color = _sentiment_label(score)

    section_header_charts(
        "Análise de Sentimento — Notícias de Mercado",
        f"{ticker} · Score Composto | Distribuição de Sentimento | Notícias Recentes",
        score_color,
    )

    # Disclaimer — always shown since the gauge/trend score is illustrative
    st.caption(
        ("📰 Notícias reais via yfinance. " if is_real_news else "⚠️ Notícias ilustrativas — API de notícias indisponível. ")
        + "Score de sentimento e gauge são ilustrativos (sem modelo NLP ativo). "
        "Para análise NLP real, configure FinBERT no pipeline `ml/sentiment_analysis/`."
    )

    c1, c2 = st.columns([1, 2])

    with c1:
        gauge_color = C_POS if score > 0.2 else (C_NEG if score < -0.1 else C_WARN)
        gauge_val   = (score + 1) / 2 * 100

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=gauge_val,
            delta={"reference": 50, "relative": False,
                   "valueformat": ".1f",
                   "increasing": {"color": C_POS},
                   "decreasing": {"color": C_NEG}},
            title=dict(
                text=f"Score Sentimento<br><span style='font-size:0.8em;color:{TEXT_MUTED}'>{lbl} · Ilustrativo</span>",
                font=dict(color=TEXT_SECONDARY, size=12),
            ),
            gauge=dict(
                axis=dict(range=[0, 100], tickvals=[0, 25, 50, 75, 100],
                          ticktext=["Muito Neg.", "Neg.", "Neutro", "Pos.", "Muito Pos."],
                          tickfont=dict(color=TEXT_MUTED, size=8)),
                bar=dict(color=gauge_color, thickness=0.3),
                bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(255,255,255,0.06)",
                steps=[
                    dict(range=[0,  30],  color="rgba(239,68,68,0.10)"),
                    dict(range=[30, 45],  color="rgba(239,68,68,0.05)"),
                    dict(range=[45, 55],  color="rgba(148,163,184,0.05)"),
                    dict(range=[55, 70],  color="rgba(16,185,129,0.05)"),
                    dict(range=[70, 100], color="rgba(16,185,129,0.10)"),
                ],
                threshold=dict(
                    line=dict(color=gauge_color, width=2),
                    thickness=0.8, value=gauge_val,
                ),
            ),
            number=dict(suffix="/100", font=dict(color=gauge_color, size=22, family="JetBrains Mono")),
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", height=220,
            margin=dict(t=40, b=10, l=20, r=20),
            font=dict(family="Inter, sans-serif"),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

        fig_donut = go.Figure(go.Pie(
            values=[data["positivo"], data["neutro"], data["negativo"]],
            labels=["Positivo", "Neutro", "Negativo"],
            hole=0.65,
            marker=dict(colors=[C_POS, C_WARN, C_NEG], line=dict(color="#0B1426", width=2)),
            textinfo="percent",
            textfont=dict(color=TEXT_PRIMARY, size=10),
            hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>",
            pull=[0.03, 0, 0.02],
        ))
        fig_donut.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", height=200,
            margin=dict(t=10, b=10, l=10, r=120),
            showlegend=True,
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02,
                        bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.1)",
                        borderwidth=1, font=dict(color="white", size=11)),
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with c2:
        fig_trend = go.Figure()
        trend = data["sentiment_trend"]
        dates = data["dates"]

        fig_trend.add_trace(go.Scatter(
            x=dates, y=trend,
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.06)",
            line=dict(color=score_color, width=2, shape="spline"),
            hovertemplate="%{x|%d/%m/%Y}<br>Score: %{y:.3f}<extra></extra>",
            name="Sentimento",
        ))
        fig_trend.add_hline(y=0, line_dash="dot", line_color="rgba(148,163,184,0.3)", line_width=1)
        fig_trend.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=160,
            margin=dict(t=20, b=30, l=50, r=10),
            xaxis=dict(title={"text": ""}, gridcolor="rgba(0,0,0,0)",
                       tickfont=dict(color=TEXT_MUTED, size=9), type="date"),
            yaxis=dict(title={"text": ""}, gridcolor="rgba(255,255,255,0.025)",
                       tickfont=dict(color=TEXT_MUTED, size=9), zeroline=False),
            showlegend=False,
            hovermode="x unified",
            font=dict(family="Inter, sans-serif"),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        news_label = "NOTÍCIAS RECENTES (REAIS)" if is_real_news else "NOTÍCIAS RECENTES (ILUSTRATIVAS)"
        st.markdown(
            f"<div style='font-size:0.65rem;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.08em;color:{TEXT_MUTED};margin-bottom:0.4rem;"
            f"font-family:Inter,sans-serif;'>{news_label}</div>",
            unsafe_allow_html=True,
        )

        for item in data["news"][:5]:
            s = item["sentiment"]
            s_color  = C_POS if s == "positivo" else (C_NEG if s == "negativo" else C_WARN)
            dot_char = "▲" if s == "positivo" else ("▼" if s == "negativo" else "●")
            impact_color = C_NEG if item["impact"] == "Alto" else (C_WARN if item["impact"] == "Médio" else TEXT_MUTED)
            date_str = item.get("data", "—")

            st.markdown(
                f"<div style='display:flex;align-items:flex-start;gap:8px;"
                f"padding:0.4rem 0;border-bottom:1px solid rgba(255,255,255,0.04);'>"
                f"<span style='color:{s_color};font-size:0.75rem;font-weight:700;"
                f"flex-shrink:0;margin-top:1px;'>{dot_char}</span>"
                f"<div style='flex:1;'>"
                f"<div style='font-size:0.78rem;color:{TEXT_SECONDARY};"
                f"font-family:Inter,sans-serif;line-height:1.3;'>{item['headline']}</div>"
                f"<div style='display:flex;gap:8px;margin-top:3px;'>"
                f"<span style='font-size:0.62rem;color:{TEXT_MUTED};font-family:Inter,sans-serif;'>"
                f"{date_str}</span>"
                f"<span style='font-size:0.62rem;color:{impact_color};font-family:Inter,sans-serif;'>"
                f"Impacto: {item['impact']}</span>"
                f"</div></div></div>",
                unsafe_allow_html=True,
            )

    insight_box(_auto_insight(data), score_color)
