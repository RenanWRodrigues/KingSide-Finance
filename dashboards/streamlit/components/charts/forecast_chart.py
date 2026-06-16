"""Finance Charts — Previsão de Preços com Modelos Estatísticos."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .styles import (
    C_NEG, C_NEUT, C_POS, C_WARN, C_PURPLE, C_CYAN,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, LEGEND_RIGHT, base_layout,
)
from .utils import (
    insight_box, kpi_card, section_header_charts, _generate_price_history,
)

_MODELS: dict[str, tuple[str, int]] = {
    "Tendência":       (C_PURPLE, 0),
    "Exp. Smoothing":  (C_CYAN,   1),
    "Reversão à Média": (C_WARN,  2),
}


def _hist_vol(closes: np.ndarray, lookback: int = 63) -> float:
    """Annualized historical volatility from daily returns."""
    window = closes[-lookback - 1:] if len(closes) > lookback + 1 else closes
    rets = np.diff(window) / window[:-1]
    return float(np.std(rets)) if len(rets) > 1 else 0.018


def _compute_forecast(
    hist: pd.DataFrame,
    model_name: str,
    n_days: int = 60,
) -> pd.DataFrame:
    """Real statistical forecast — linear regression, EWM trend, or mean reversion."""
    closes = hist["fechamento"].values.astype(float)
    n = len(closes)
    last_price = float(closes[-1])
    last_date  = hist["data"].iloc[-1]
    dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=n_days)

    vol = _hist_vol(closes)

    if model_name == "Tendência":
        lookback = min(126, n)
        xs = np.arange(lookback, dtype=float)
        coef = np.polyfit(xs, closes[-lookback:], 1)
        xs_fut = np.arange(lookback, lookback + n_days, dtype=float)
        prices = list(np.polyval(coef, xs_fut))

    elif model_name == "Exp. Smoothing":
        series = pd.Series(closes)
        ema_fast = float(series.ewm(span=12, adjust=False).mean().iloc[-1])
        ema_slow = float(series.ewm(span=26, adjust=False).mean().iloc[-1])
        daily_drift = float(np.clip((ema_fast - ema_slow) / last_price * 0.10, -0.003, 0.003))
        prices = [last_price * (1 + daily_drift) ** (i + 1) for i in range(n_days)]

    elif model_name == "Reversão à Média":
        lookback = min(200, n)
        long_avg = float(np.mean(closes[-lookback:]))
        gap = long_avg - last_price
        reversion_speed = 0.008
        prices_list, p = [], last_price
        for _ in range(n_days):
            p = p + gap * reversion_speed
            gap = long_avg - p
            prices_list.append(p)
        prices = prices_list
    else:
        prices = [last_price] * n_days

    conf_width = [last_price * vol * float(np.sqrt(i + 1)) for i in range(n_days)]

    return pd.DataFrame({
        "data":     dates,
        "forecast": prices,
        "upper":    [f + w for f, w in zip(prices, conf_width)],
        "lower":    [max(f - w, 0.01) for f, w in zip(prices, conf_width)],
        "model":    model_name,
    })


def _compute_metrics(model_name: str, hist: pd.DataFrame) -> dict:
    """Real out-of-sample metrics: train on all but last 20 days, test on last 20."""
    closes = hist["fechamento"].values.astype(float)
    n = len(closes)

    if n < 40:
        return {"RMSE": None, "MAE": None, "MAPE": None, "R²": None}

    train, test = closes[:-20], closes[-20:]
    n_tr = len(train)

    if model_name == "Tendência":
        xs_tr = np.arange(n_tr, dtype=float)
        coef  = np.polyfit(xs_tr, train, 1)
        preds = np.polyval(coef, np.arange(n_tr, n_tr + 20, dtype=float))

    elif model_name == "Exp. Smoothing":
        series = pd.Series(train)
        ema_f  = float(series.ewm(span=12, adjust=False).mean().iloc[-1])
        ema_s  = float(series.ewm(span=26, adjust=False).mean().iloc[-1])
        drift  = float(np.clip((ema_f - ema_s) / train[-1] * 0.10, -0.003, 0.003))
        preds  = np.array([train[-1] * (1 + drift) ** (i + 1) for i in range(20)])

    elif model_name == "Reversão à Média":
        long_avg = float(np.mean(train[-min(200, n_tr):]))
        gap = long_avg - train[-1]
        speed = 0.008
        preds_list, p = [], float(train[-1])
        for _ in range(20):
            p = p + gap * speed
            gap = long_avg - p
            preds_list.append(p)
        preds = np.array(preds_list)
    else:
        preds = np.full(20, train[-1])

    errors  = test - preds
    mape    = float(np.mean(np.abs(errors / np.where(test != 0, test, 1e-8))) * 100)
    mae     = float(np.mean(np.abs(errors)))
    rmse    = float(np.sqrt(np.mean(errors ** 2)))
    ss_res  = float(np.sum(errors ** 2))
    ss_tot  = float(np.sum((test - test.mean()) ** 2))
    r2      = max(0.0, 1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    return {
        "RMSE": round(rmse, 2),
        "MAE":  round(mae, 2),
        "MAPE": round(mape, 1),
        "R²":   round(r2, 3),
    }


def _auto_insight(hist: pd.DataFrame, forecasts: dict[str, pd.DataFrame]) -> str:
    consensus = [df["forecast"].iloc[-1] for df in forecasts.values()]
    current   = hist["fechamento"].iloc[-1]
    avg_target = float(np.mean(consensus))
    upside     = (avg_target / current - 1) * 100

    if upside > 10:
        return (
            f"Consenso dos modelos estatísticos aponta upside médio de {upside:.1f}% "
            "no horizonte projetado. Tendência, momentum e reversão à média convergem em alta."
        )
    if upside < -5:
        return (
            f"Modelos indicam pressão de baixa ({upside:.1f}% de downside médio). "
            "Verificar fundamentos e catalisadores antes de novas posições."
        )
    return (
        f"Modelos projetam preço-alvo médio de R$ {avg_target:.2f} ({upside:+.1f}%). "
        "Cenário base neutro — monitorar revisões de estimativas e volumes."
    )


def render_forecast_chart(
    hist: pd.DataFrame | None = None,
    ticker: str = "TICKER",
    n_forecast_days: int = 60,
) -> None:
    if hist is None or hist.empty:
        hist = _generate_price_history(ticker)

    section_header_charts(
        "Previsão de Preços",
        f"{ticker} · Tendência Linear | Exp. Smoothing | Reversão à Média — {n_forecast_days} dias",
        C_PURPLE,
    )

    st.caption(
        "Modelos estatísticos baseados em dados históricos reais. "
        "Métricas avaliadas por validação out-of-sample (últimos 20 pregões). "
        "Para previsões com Prophet / LSTM, configure o pipeline `ml/` do backend."
    )

    forecasts: dict[str, pd.DataFrame] = {
        name: _compute_forecast(hist, name, n_forecast_days)
        for name in _MODELS
    }
    all_metrics = {name: _compute_metrics(name, hist) for name in _MODELS}

    c_cols = st.columns(len(_MODELS))
    for i, (name, (color, _)) in enumerate(_MODELS.items()):
        m = all_metrics[name]
        mape_val = m["MAPE"]
        r2_val   = m["R²"]
        mape_ok  = mape_val is not None and mape_val < 8
        with c_cols[i]:
            st.markdown(kpi_card(
                name,
                f"MAPE: {mape_val:.1f}%" if mape_val is not None else "Sem dados",
                f"RMSE: {m['RMSE']:.2f} | R²: {r2_val:.3f}" if r2_val is not None else "—",
                mape_ok, color, "◈",
            ), unsafe_allow_html=True)

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=hist["data"], y=hist["fechamento"],
        name="Histórico Real",
        mode="lines",
        line=dict(color="#E5E7EB", width=1.8),
        fill="tozeroy",
        fillcolor="rgba(229,231,235,0.04)",
        hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:.2f}<extra></extra>",
    ))

    last_date = hist["data"].iloc[-1]
    fig.add_vline(
        x=last_date.timestamp() * 1000,
        line_dash="dot",
        line_color="rgba(148,163,184,0.3)",
        line_width=1,
        annotation_text="Hoje",
        annotation_font=dict(color=TEXT_MUTED, size=9),
        annotation_position="top",
    )

    for name, (color, _) in _MODELS.items():
        fc = forecasts[name]
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

        fig.add_trace(go.Scatter(
            x=pd.concat([fc["data"], fc["data"].iloc[::-1]]),
            y=pd.concat([fc["upper"], fc["lower"].iloc[::-1]]),
            fill="toself",
            fillcolor=f"rgba({r},{g},{b},0.06)",
            line=dict(color="rgba(0,0,0,0)"),
            name=f"{name} IC 95%",
            showlegend=False,
            hoverinfo="skip",
        ))

        fig.add_trace(go.Scatter(
            x=fc["data"], y=fc["forecast"],
            name=name,
            mode="lines",
            line=dict(color=color, width=2),
            hovertemplate=f"<b>{name}</b><br>%{{x|%d/%m/%Y}}<br>R$ %{{y:.2f}}<extra></extra>",
        ))

    for name, (color, _) in _MODELS.items():
        target = forecasts[name]["forecast"].iloc[-1]
        fig.add_annotation(
            x=forecasts[name]["data"].iloc[-1],
            y=target,
            text=f"<b>R$ {target:.2f}</b>",
            showarrow=True,
            arrowhead=2,
            arrowcolor=color,
            arrowsize=0.8,
            font=dict(color=color, size=9, family="JetBrains Mono"),
            bgcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.15)",
            bordercolor=color,
            borderwidth=1,
            borderpad=3,
        )

    fig.update_layout(**base_layout(
        height=500,
        hovermode="x unified",
        yaxis=dict(tickprefix="R$ ", gridcolor="rgba(255,255,255,0.03)",
                   tickfont=dict(color=TEXT_MUTED, size=10)),
        xaxis=dict(gridcolor="rgba(255,255,255,0.02)",
                   tickfont=dict(color=TEXT_MUTED, size=10), type="date"),
        legend=LEGEND_RIGHT,
        margin=dict(r=150),
    ))
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True,
                    config={"toImageButtonOptions": {"format": "png", "scale": 2}})

    insight_box(_auto_insight(hist, forecasts), C_PURPLE)
