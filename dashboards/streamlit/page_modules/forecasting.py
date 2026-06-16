"""Finance — Forecasting Page."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import CHART_LAYOUT
from utils.api import fetch, to_float
from utils.ui import section_header, apply_period_filter


def render(ticker: str) -> None:
    section_header("Previsão ML", "#a855f7")
    st.markdown(
        f"<span style='font-size:0.9rem;font-weight:700;color:#a855f7;"
        f"font-family:\"JetBrains Mono\",monospace;'>{ticker}</span>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        model = st.selectbox("Modelo", ["prophet", "arima"], key="fc_model")
    with c2:
        horizon = st.slider("Horizonte (dias)", 7, 90, 30, key="fc_horizon")
    with c3:
        show_history = st.checkbox("Mostrar preço histórico", value=True, key="fc_hist")

    with st.spinner(f"Gerando previsão {model.upper()} para {ticker}..."):
        forecast_data = fetch(
            f"/forecast/{ticker}",
            {"horizonte_dias": horizon, "modelo": model},
            timeout=60,
        )
        hist_data = fetch(f"/stocks/{ticker}/history", {"period": "6mo"}, silent=True) if show_history else None

    if not forecast_data or not isinstance(forecast_data, list):
        st.info(
            f"Previsão indisponível para **{ticker}**. "
            "As bibliotecas de ML podem não estar instaladas neste container."
        )
        return

    df_fc = pd.DataFrame(forecast_data)
    df_fc["data_forecast"] = pd.to_datetime(df_fc["data_forecast"])
    df_fc["preco_previsto"] = df_fc["preco_previsto"].apply(to_float)

    fig = go.Figure()

    if hist_data and hist_data.get("cotacoes"):
        df_hist = pd.DataFrame(hist_data["cotacoes"])
        df_hist["data"] = pd.to_datetime(df_hist["data"])
        df_hist["fechamento"] = df_hist["fechamento"].apply(to_float)
        df_hist = df_hist.dropna(subset=["fechamento"])
        df_hist = apply_period_filter(df_hist)
        fig.add_trace(go.Scatter(
            x=df_hist["data"], y=df_hist["fechamento"],
            mode="lines", name="Histórico",
            line=dict(color="#94a3b8", width=1.5),
            hovertemplate="%{x|%d/%m/%Y}<br>Preço: R$ %{y:.2f}<extra></extra>",
        ))
        if len(df_hist) > 0:
            fig.add_vline(
                x=df_hist["data"].iloc[-1].timestamp() * 1000,
                line_dash="dot", line_color="rgba(255,255,255,0.2)",
                annotation_text="Início da previsão",
                annotation_font_color="#64748b", annotation_font_size=10,
            )

    if "lower_bound" in df_fc.columns and "upper_bound" in df_fc.columns:
        df_fc["lower_bound"] = df_fc["lower_bound"].apply(to_float)
        df_fc["upper_bound"] = df_fc["upper_bound"].apply(to_float)
        fig.add_trace(go.Scatter(
            x=pd.concat([df_fc["data_forecast"], df_fc["data_forecast"].iloc[::-1]]),
            y=pd.concat([df_fc["upper_bound"], df_fc["lower_bound"].iloc[::-1]]),
            fill="toself", fillcolor="rgba(168,85,247,0.1)",
            line=dict(color="rgba(255,255,255,0)"),
            name="IC 95%", hoverinfo="skip",
        ))

    fig.add_trace(go.Scatter(
        x=df_fc["data_forecast"], y=df_fc["preco_previsto"],
        mode="lines+markers",
        name=f"Previsão {model.upper()}",
        line=dict(color="#a855f7", width=2.5),
        marker=dict(color="#a855f7", size=4, line=dict(color="rgba(255,255,255,0.3)", width=1)),
        hovertemplate="%{x|%d/%m/%Y}<br>Forecast: R$ %{y:.2f}<extra></extra>",
    ))

    layout = dict(CHART_LAYOUT)
    layout.update(
        title=f"{ticker} — {model.upper()} · Previsão de Preço {horizon} dias",
        height=460, hovermode="x unified",
    )
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="Preço (R$)")
    st.plotly_chart(fig, use_container_width=True)

    last_fc = df_fc["preco_previsto"].dropna().iloc[-1] if len(df_fc) > 0 else None
    first_fc = df_fc["preco_previsto"].dropna().iloc[0] if len(df_fc) > 0 else None

    if last_fc and first_fc:
        upside = (last_fc / first_fc - 1) * 100
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Preço Inicial Previsto", f"R$ {first_fc:.2f}")
        with k2:
            st.metric(f"Preço em {horizon}d", f"R$ {last_fc:.2f}", f"{upside:+.1f}%")
        with k3:
            if "upper_bound" in df_fc.columns:
                ub = df_fc["upper_bound"].dropna().iloc[-1]
                st.metric("Limite Superior (95%)", f"R$ {ub:.2f}")
        with k4:
            if "lower_bound" in df_fc.columns:
                lb = df_fc["lower_bound"].dropna().iloc[-1]
                st.metric("Limite Inferior (95%)", f"R$ {lb:.2f}")

    st.caption(f"Modelo: **{model.upper()}** · Horizonte: {horizon} dias · Não constitui recomendação de investimento.")
