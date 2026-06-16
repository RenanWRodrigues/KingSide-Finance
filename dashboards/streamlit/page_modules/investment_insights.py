"""Finance — Investment Insights Page (Proprietary Scoring Engine)."""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import CHART_LAYOUT, PALETTE, TICKER_UNIVERSE
from utils.api import to_float
from utils.direct import batch_stock_history
from utils.ui import render_dark_table, badge, score_bar_html, section_header

# ── Load ML scorer from ml/ package (project root must be on sys.path) ────────
_ML_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _ML_ROOT not in sys.path:
    sys.path.insert(0, _ML_ROOT)

try:
    from ml.investment_scoring.scorer import InvestmentScorer as _MlScorer
    _SCORER: _MlScorer | None = _MlScorer()
except Exception:
    _SCORER = None

_SIGNAL_PT: dict[str, str] = {
    "Strong Buy":  "Compra Forte",
    "Buy":         "Comprar",
    "Neutral":     "Neutro",
    "Sell":        "Vender",
    "Strong Sell": "Venda Forte",
}


def _compute_score(hist_data: dict | None, ticker: str) -> dict:
    cotacoes = (hist_data or {}).get("cotacoes", [])
    valid = [(c, to_float(c.get("fechamento"))) for c in cotacoes]
    valid = [(c, f) for c, f in valid if f is not None]

    if len(valid) < 20:
        return {
            "ticker": ticker, "score": None, "signal": "Sem Dados",
            "momentum_score": None, "risk_score": None, "trend_score": None,
            "rsi_score": None, "volatility": None, "sharpe": None, "total_return": None,
        }

    prices  = pd.Series([f for _, f in valid], dtype=float)
    vols_raw = [float(c.get("volume") or 0) for c, _ in valid]
    volumes = pd.Series(vols_raw, dtype=float) if any(v > 0 for v in vols_raw) else None

    if _SCORER is not None:
        result = _SCORER.score(prices, volumes)
        result.ticker = ticker
        return {
            "ticker": ticker,
            "score": result.score,
            "signal": _SIGNAL_PT.get(result.signal, result.signal),
            "momentum_score": round(result.components.momentum, 1),
            "trend_score":    round(result.components.trend,    1),
            "risk_score":     round(result.components.risk,     1),
            "rsi_score":      round(result.components.rsi,      1),
            "volatility":     result.volatility_annual,
            "sharpe":         result.sharpe_ratio,
            "total_return":   result.total_return_1y,
        }

    # ── Fallback: lightweight inline scorer (same logic, no volume factor) ─────
    import math
    closes = prices.values
    n = len(closes)
    ret_1m  = (closes[-1] / closes[max(0, n-21)] - 1) * 100 if n >= 21 else 0
    ret_3m  = (closes[-1] / closes[max(0, n-63)] - 1) * 100 if n >= 63 else 0
    ret_1y  = (closes[-1] / closes[0] - 1) * 100
    momentum_score = max(0.0, min(100.0, 50 + (ret_1m * 0.2 + ret_3m * 0.4 + ret_1y * 0.4) * 0.7))
    ma20  = prices.rolling(20).mean().iloc[-1] if n >= 20 else None
    ma50  = prices.rolling(50).mean().iloc[-1] if n >= 50 else None
    ma200 = prices.rolling(200).mean().iloc[-1] if n >= 200 else None
    price = closes[-1]
    trend_pts = 50.0
    if ma20 is not None: trend_pts += 15 if price > ma20 else -15
    if ma50 is not None: trend_pts += 20 if price > ma50 else -20
    if ma200 is not None: trend_pts += 15 if price > ma200 else -15
    if ma20 is not None and ma50 is not None: trend_pts += 10 if ma20 > ma50 else -10
    trend_score = max(0.0, min(100.0, trend_pts))
    rets = prices.pct_change().dropna()
    vol_annual = rets.std() * math.sqrt(252) * 100 if len(rets) > 5 else 30
    risk_score = max(0.0, min(100.0, 100 - vol_annual * 1.2))
    rf_daily = (1 + 0.1475) ** (1 / 252) - 1
    sharpe   = float((rets.mean() - rf_daily) / rets.std() * math.sqrt(252)) if rets.std() > 0 else 0
    delta  = prices.diff()
    gain   = delta.clip(lower=0).rolling(14).mean()
    loss   = (-delta.clip(upper=0)).rolling(14).mean()
    rs     = gain / loss.replace(0, float("nan"))
    rsi_v  = (100 - 100 / (1 + rs)).iloc[-1] if n >= 15 else 50
    rsi_score = max(0.0, 100 - abs(rsi_v - 50) * 1.5)
    composite = momentum_score * 0.30 + trend_score * 0.30 + risk_score * 0.20 + rsi_score * 0.20

    def _sig(s: float) -> str:
        if s >= 75: return "Compra Forte"
        if s >= 60: return "Comprar"
        if s >= 40: return "Neutro"
        if s >= 25: return "Vender"
        return "Venda Forte"

    return {
        "ticker": ticker,
        "score": round(composite, 1),
        "signal": _sig(composite),
        "momentum_score": round(momentum_score, 1),
        "trend_score":    round(trend_score,    1),
        "risk_score":     round(risk_score,     1),
        "rsi_score":      round(rsi_score,      1),
        "volatility":     round(vol_annual,     1),
        "sharpe":         round(sharpe,         2),
        "total_return":   round(ret_1y,         1),
    }


def _score_color(score: float | None) -> str:
    if score is None:
        return "#64748b"
    return "#10b981" if score >= 70 else ("#f59e0b" if score >= 50 else "#ef4444")


_INSIGHT_TICKERS = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3", "SANB11",
    "WEGE3", "EMBR3", "ABEV3", "JBSS3", "BBSE3", "TAEE11",
    "EGIE3", "ELET3", "CMIG4", "PRIO3", "CSAN3", "SUZB3",
    "KLBN11", "MGLU3", "LREN3", "ASAI3", "TOTS3", "CYRE3",
    "RAIL3", "RENT3", "SBSP3", "RADL3", "HAPV3", "VIVT3",
    "CPFE3", "EQTL3", "BRFS3", "TIMS3",
]


def render() -> None:
    section_header("Insights de Investimento", "#10b981")
    engine_label = "Motor ML ativo (`ml/investment_scoring/scorer.py`)" if _SCORER is not None else "Motor local (fallback)"
    st.caption(f"Motor de Pontuação Quantitativa — Análise Multi-Fator · {engine_label}")

    c1, c2 = st.columns([3, 1])
    with c1:
        selected_tickers = st.multiselect(
            "Analisar ativos",
            options=list(TICKER_UNIVERSE.keys()),
            default=_INSIGHT_TICKERS,
            format_func=lambda t: f"{t} — {TICKER_UNIVERSE.get(t, t)}",
            key="ii_tickers",
        )
    with c2:
        period = st.selectbox("Período", ["1y", "6mo", "3mo"], key="ii_period")

    if not selected_tickers:
        st.info("Selecione pelo menos um ativo para analisar.")
        return

    with st.spinner(f"Calculando pontuações para {len(selected_tickers)} ativos..."):
        batch = batch_stock_history(tuple(sorted(selected_tickers)), period)

    scores = [
        _compute_score(
            {"ticker": t, "cotacoes": batch[t]} if t in batch else None,
            t,
        )
        for t in selected_tickers
    ]
    scores.sort(key=lambda x: (x["score"] is not None, x["score"] or 0), reverse=True)

    strong_buy = sum(1 for s in scores if s["signal"] == "Compra Forte")
    buy = sum(1 for s in scores if s["signal"] == "Comprar")
    neutral = sum(1 for s in scores if s["signal"] == "Neutro")
    sell_count = sum(1 for s in scores if s["signal"] in ("Vender", "Venda Forte"))

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Analisados", len(scores))
    with k2:
        st.metric("Compra Forte", strong_buy)
    with k3:
        st.metric("Comprar", buy)
    with k4:
        st.metric("Neutro", neutral)
    with k5:
        st.metric("Vender / Venda Forte", sell_count)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Ranking de Score", "Decomposição do Score", "Matriz Risco-Retorno"])

    with tab1:
        _render_ranking(scores)

    with tab2:
        _render_breakdown(scores)

    with tab3:
        _render_risk_return(scores)


def _render_ranking(scores: list[dict]) -> None:
    scored = [s for s in scores if s["score"] is not None]
    no_data = [s for s in scores if s["score"] is None]
    if no_data:
        st.caption(f"⚠️ Dados insuficientes para: {', '.join(s['ticker'] for s in no_data)}")
    scores = scored

    df_rows = []
    for i, s in enumerate(scores):
        rank_prefix = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else f"#{i+1}"))
        df_rows.append({
            "Rank": rank_prefix,
            "Ticker": s["ticker"],
            "QV Score": s["score"],
            "Sinal": s["signal"],
            "Retorno": s.get("total_return", 0),
            "Volatilidade": s.get("volatility", 0),
            "Sharpe": s.get("sharpe", 0),
        })

    if not df_rows:
        st.info("Nenhum ativo com dados suficientes para calcular pontuações. Aguarde o carregamento dos dados e recarregue a página.")
        return

    df = pd.DataFrame(df_rows)

    _signal_colors = {
        "Compra Forte": "#00d4aa",
        "Comprar": "#10b981",
        "Neutro": "#94a3b8",
        "Vender": "#ef4444",
        "Venda Forte": "#fca5a5",
    }
    df_rank = df.reset_index(drop=True)
    cell_colors_ii: dict[tuple[int, str], str] = {}
    for i, row in df_rank.iterrows():
        score = row.get("QV Score")
        if isinstance(score, (int, float)):
            cell_colors_ii[(i, "QV Score")] = "#10b981" if score >= 70 else ("#f59e0b" if score >= 50 else "#ef4444")
        sig = str(row.get("Sinal", ""))
        if sig in _signal_colors:
            cell_colors_ii[(i, "Sinal")] = _signal_colors[sig]
        for c in ["Retorno", "Sharpe"]:
            v = row.get(c)
            if isinstance(v, (int, float)):
                cell_colors_ii[(i, c)] = "#10b981" if v >= 0 else "#ef4444"
    df_rank["QV Score"] = df_rank["QV Score"].apply(lambda v: f"{v:.1f}" if isinstance(v, (int, float)) else "—")
    df_rank["Retorno"] = df_rank["Retorno"].apply(lambda v: f"{v:+.1f}%" if isinstance(v, (int, float)) else "—")
    df_rank["Volatilidade"] = df_rank["Volatilidade"].apply(lambda v: f"{v:.1f}%" if isinstance(v, (int, float)) else "—")
    df_rank["Sharpe"] = df_rank["Sharpe"].apply(lambda v: f"{v:.2f}" if isinstance(v, (int, float)) else "—")
    render_dark_table(df_rank, cell_colors=cell_colors_ii, height=420)


def _render_breakdown(scores: list[dict]) -> None:
    top8 = [s for s in scores if s["score"] is not None][:8]
    if not top8:
        st.info("Sem dados para decompor. Aguarde o carregamento e recarregue a página.")
        return
    categories = ["Momentum", "Tendência", "Risco", "RSI"]

    fig = go.Figure()
    for i, s in enumerate(top8):
        color = PALETTE[i % len(PALETTE)]
        vals = [s.get("momentum_score", 50), s.get("trend_score", 50),
                s.get("risk_score", 50), s.get("rsi_score", 50), s.get("momentum_score", 50)]
        r_int = int(color[1:3], 16)
        g_int = int(color[3:5], 16)
        b_int = int(color[5:7], 16)
        fig.add_trace(go.Scatterpolar(
            r=vals,
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor=f"rgba({r_int},{g_int},{b_int},0.08)",
            line=dict(color=color, width=2),
            name=s["ticker"],
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(255,255,255,0.06)",
                            tickfont=dict(color="#475569", size=9), tickvals=[25, 50, 75, 100]),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.1)",
                             tickfont=dict(color="#94a3b8", size=11)),
        ),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#94a3b8"),
        legend=dict(bgcolor="rgba(13,20,36,0.8)", bordercolor="rgba(255,255,255,0.06)",
                    borderwidth=1, font=dict(color="#94a3b8", size=10)),
        height=460, margin=dict(t=20, b=20, l=60, r=60),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    df_sub = pd.DataFrame([{
        "Ticker": s["ticker"],
        "Momentum": s.get("momentum_score", 0),
        "Tendência": s.get("trend_score", 0),
        "Risco": s.get("risk_score", 0),
        "RSI": s.get("rsi_score", 0),
    } for s in top8]).set_index("Ticker")

    df_sub_disp = df_sub.reset_index()
    score_cols = [c for c in df_sub_disp.columns if c != "Ticker"]
    cell_colors_bd: dict[tuple[int, str], str] = {}
    for i, row in df_sub_disp.iterrows():
        for col in score_cols:
            v = row[col]
            if isinstance(v, (int, float)):
                cell_colors_bd[(i, col)] = "#10b981" if v >= 70 else ("#f59e0b" if v >= 45 else "#ef4444")
    for col in score_cols:
        df_sub_disp[col] = df_sub_disp[col].apply(lambda v: f"{v:.1f}" if isinstance(v, (int, float)) else "—")
    render_dark_table(df_sub_disp, cell_colors=cell_colors_bd)


def _render_risk_return(scores: list[dict]) -> None:
    scored = [s for s in scores if s["score"] is not None]
    if not scored:
        st.info("Sem dados suficientes para a matriz. Aguarde o carregamento e recarregue a página.")
        return
    fig = go.Figure()
    for s in scored:
        score = s["score"] or 0.0
        color = _score_color(score)
        vol = s.get("volatility") or 20
        ret = s.get("total_return") or 0
        sharpe = s.get("sharpe") or 0
        size = max(abs(sharpe) * 16 + 10, 10)

        fig.add_trace(go.Scatter(
            x=[vol], y=[ret],
            mode="markers+text",
            text=[s["ticker"]],
            textposition="top center",
            textfont=dict(size=10, color="#f1f5f9"),
            marker=dict(color=color, size=size, opacity=0.85,
                        line=dict(color="rgba(255,255,255,0.15)", width=1)),
            name=s["ticker"],
            showlegend=False,
            hovertemplate=(
                f"<b>{s['ticker']}</b><br>QV Score: {score:.1f}<br>"
                f"Sinal: {s['signal']}<br>Volatilidade: {vol:.1f}%<br>"
                f"Retorno: {ret:+.1f}%<br>Sharpe: {sharpe:.2f}<extra></extra>"
            ),
        ))

    layout = dict(CHART_LAYOUT)
    layout.update(
        height=480, hovermode="closest",
        shapes=[dict(type="line", x0=0, x1=100, y0=0, y1=0,
                     line=dict(color="rgba(255,255,255,0.12)", width=1, dash="dot"))],
    )
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="Volatilidade Anual (%)")
    fig.update_yaxes(title_text="Retorno Total (%)")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    st.caption("Tamanho = |Sharpe Ratio| · Cor: verde = score alto, âmbar = médio, vermelho = baixo")
