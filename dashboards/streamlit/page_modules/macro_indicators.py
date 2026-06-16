"""Finance — Macro Indicators Page."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from config import CHART_LAYOUT, PALETTE
from utils.api import fetch, fetch_parallel, to_float
from utils.ui import section_header, apply_period_filter, any_period_filter_active

_INDICATORS = {
    "selic": "SELIC (% a.a.)",
    "ipca": "IPCA 12m (%)",
    "cambio_dolar": "USD/BRL (R$)",
    "igpm": "IGP-M (%)",
}


def render() -> None:
    section_header("Indicadores Macro — Brasil", "#06b6d4")

    tab1, tab2 = st.tabs(["Análise Individual", "Painel Multi-Indicador"])

    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            indicator = st.selectbox(
                "Indicador", list(_INDICATORS.keys()),
                format_func=lambda k: _INDICATORS[k],
                key="macro_ind",
            )
        with c2:
            window = st.selectbox(
                "Janela", [12, 24, 48, 120, 0], key="macro_win",
                format_func=lambda x: f"Últimos {x}m" if x else "Todos",
            )

        params: dict = {}
        ano_filter = st.session_state.get("filter_ano", "Todos")
        if not any_period_filter_active() and window:
            params["data_inicio"] = (
                pd.Timestamp.today() - pd.DateOffset(months=window)
            ).strftime("%Y-%m-%d")
        elif ano_filter != "Todos":
            params["data_inicio"] = f"{ano_filter}-01-01"
            params["data_fim"] = f"{ano_filter}-12-31"

        with st.spinner(f"Carregando {indicator.upper()}..."):
            data = fetch(f"/macro/brasil/{indicator}", params=params or None)

        if not data or not isinstance(data, list):
            st.info(f"Dados de {indicator.upper()} indisponíveis.")
        else:
            df = pd.DataFrame(data)
            df["data"] = pd.to_datetime(df["data"])
            df["valor"] = df["valor"].apply(to_float)
            df = df.dropna(subset=["valor"]).sort_values("data")
            df = apply_period_filter(df)

            last_val = df["valor"].iloc[-1]
            prev_val = df["valor"].iloc[-2] if len(df) >= 2 else last_val

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.metric("Atual", f"{last_val:.4f}", f"{last_val - prev_val:+.4f}")
            with k2:
                st.metric("Máxima (período)", f"{df['valor'].max():.4f}")
            with k3:
                st.metric("Mínima (período)", f"{df['valor'].min():.4f}")
            with k4:
                st.metric("Média", f"{df['valor'].mean():.4f}")

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["data"], y=df["valor"],
                mode="lines", name=_INDICATORS[indicator],
                line=dict(color="#06b6d4", width=2.5),
                fill="tozeroy", fillcolor="rgba(6,182,212,0.06)",
                hovertemplate="%{x|%b %Y}<br>%{y:.4f}<extra></extra>",
            ))
            if len(df) >= 12:
                fig.add_trace(go.Scatter(
                    x=df["data"], y=df["valor"].rolling(12).mean(),
                    mode="lines", name="MM 12m",
                    line=dict(color="#f59e0b", width=1.5, dash="dash"),
                    opacity=0.7, hoverinfo="skip",
                ))
            layout = dict(CHART_LAYOUT)
            layout.update(title=f"{_INDICATORS[indicator]} — Histórico", height=400, hovermode="x unified")
            fig.update_layout(**layout)
            fig.update_xaxes(title_text="")
            fig.update_yaxes(title_text="")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        _render_multi_indicator()


def _render_multi_indicator() -> None:
    with st.spinner("Carregando todos os indicadores macro..."):
        results = fetch_parallel([
            ("/macro/brasil/selic", None),
            ("/macro/brasil/ipca", None),
            ("/macro/brasil/cambio_dolar", None),
            ("/macro/brasil/igpm", None),
        ])

    labels = list(_INDICATORS.values())
    colors = [PALETTE[i] for i in range(4)]

    fig = make_subplots(
        rows=2, cols=2, subplot_titles=labels,
        vertical_spacing=0.12, horizontal_spacing=0.08,
    )

    for idx, (data, label, color) in enumerate(zip(results, labels, colors)):
        row, col = divmod(idx, 2)
        if not data or not isinstance(data, list):
            continue
        df = pd.DataFrame(data)
        df["data"] = pd.to_datetime(df["data"])
        df["valor"] = df["valor"].apply(to_float)
        df = df.dropna(subset=["valor"]).sort_values("data")
        df = apply_period_filter(df)
        if not any_period_filter_active():
            cutoff = df["data"].max() - pd.DateOffset(months=60)
            df = df[df["data"] >= cutoff]
        r_int = int(color[1:3], 16)
        g_int = int(color[3:5], 16)
        b_int = int(color[5:7], 16)
        fig.add_trace(
            go.Scatter(
                x=df["data"], y=df["valor"], mode="lines", name=label,
                line=dict(color=color, width=2),
                fill="tozeroy", fillcolor=f"rgba({r_int},{g_int},{b_int},0.05)",
                hovertemplate=f"%{{x|%b %Y}}<br>{label}: %{{y:.4f}}<extra></extra>",
                showlegend=False,
            ),
            row=row+1, col=col+1,
        )

    layout = dict(CHART_LAYOUT)
    layout.update(height=520, margin=dict(t=40, b=20, l=50, r=20))
    fig.update_layout(**layout)

    for i in range(1, 3):
        for j in range(1, 3):
            fig.update_xaxes(title_text="", gridcolor="rgba(255,255,255,0.035)", linecolor="rgba(255,255,255,0.06)",
                             tickfont=dict(color="#64748b", size=9), row=i, col=j)
            fig.update_yaxes(title_text="", gridcolor="rgba(255,255,255,0.035)", linecolor="rgba(255,255,255,0.06)",
                             tickfont=dict(color="#64748b", size=9), row=i, col=j)

    for ann in fig.layout.annotations:
        ann.font.update(color="#94a3b8", size=11)

    st.plotly_chart(fig, use_container_width=True)
