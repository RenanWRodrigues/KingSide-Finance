"""Finance — Market Overview Page."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import CHART_LAYOUT
from utils.api import fetch_parallel, to_float
from utils.ui import section_header, apply_period_filter, any_period_filter_active

_MOVERS = ["PETR4", "VALE3", "ITUB4", "WEGE3", "RENT3", "ABEV3", "EMBR3", "BBAS3"]


def render() -> None:
    section_header("Visão de Mercado", "#3b82f6")

    with st.spinner("Carregando dados de mercado..."):
        selic_data, ipca_data, cambio_data, igpm_data = fetch_parallel([
            ("/macro/brasil/selic", None),
            ("/macro/brasil/ipca", None),
            ("/macro/brasil/cambio_dolar", None),
            ("/macro/brasil/igpm", None),
        ])

    def _metric(series: list | None) -> tuple[float | None, float | None]:
        if not series or not isinstance(series, list):
            return None, None
        last = to_float(series[-1].get("valor"))
        prev = to_float(series[-2].get("valor")) if len(series) >= 2 else None
        return last, prev

    selic_l, selic_p = _metric(selic_data)
    ipca_l, ipca_p = _metric(ipca_data)
    cambio_l, cambio_p = _metric(cambio_data)
    igpm_l, igpm_p = _metric(igpm_data)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        d = f"{selic_l - selic_p:+.2f}" if selic_l and selic_p else None
        st.metric("SELIC Rate", f"{selic_l:.2f}%" if selic_l else "—", d)
    with col2:
        d = f"{ipca_l - ipca_p:+.2f}" if ipca_l and ipca_p else None
        st.metric("IPCA 12m", f"{ipca_l:.2f}%" if ipca_l else "—", d, delta_color="inverse")
    with col3:
        d = f"{cambio_l - cambio_p:+.4f}" if cambio_l and cambio_p else None
        st.metric("USD / BRL", f"R$ {cambio_l:.4f}" if cambio_l else "—", d, delta_color="inverse")
    with col4:
        d = f"{igpm_l - igpm_p:+.2f}" if igpm_l and igpm_p else None
        st.metric("IGP-M", f"{igpm_l:.2f}%" if igpm_l else "—", d, delta_color="inverse")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1.3, 1], gap="medium")

    with col_left:
        section_header("Maiores Variações", "#f59e0b")
        with st.spinner("Buscando variações..."):
            mover_results = fetch_parallel(
                [(f"/stocks/{t}/history", {"period": "5d"}) for t in _MOVERS]
            )

        rows = []
        for ticker, hist in zip(_MOVERS, mover_results):
            cotacoes = (hist or {}).get("cotacoes", [])
            if len(cotacoes) >= 2:
                last_p = to_float(cotacoes[-1]["fechamento"])
                prev_p = to_float(cotacoes[-2]["fechamento"])
                vol = int(cotacoes[-1].get("volume") or 0)
                if last_p and prev_p and prev_p != 0:
                    chg = (last_p - prev_p) / prev_p * 100
                    rows.append({
                        "Ticker": ticker,
                        "Preço": f"R$ {last_p:.2f}",
                        "Variação": f"{chg:+.2f}%",
                        "Volume": f"{vol/1e6:.1f}M",
                        "_chg": chg,
                    })

        if rows:
            df = pd.DataFrame(rows).sort_values("_chg", ascending=False)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[r["_chg"] for r in df.to_dict("records")],
                y=df["Ticker"],
                orientation="h",
                marker=dict(
                    color=["#10b981" if r["_chg"] >= 0 else "#ef4444" for r in df.to_dict("records")],
                    opacity=0.85,
                    line=dict(color="rgba(255,255,255,0.05)", width=0.5),
                ),
                text=[f"{r['_chg']:+.2f}%" for r in df.to_dict("records")],
                textposition="outside",
                textfont=dict(color="#94a3b8", size=11),
                hovertemplate="<b>%{y}</b>  %{x:+.2f}%<extra></extra>",
            ))
            layout = dict(CHART_LAYOUT)
            layout.update(height=320, margin=dict(t=10, b=20, l=60, r=50))
            layout["xaxis"] = dict(layout["xaxis"])  # type: ignore[index]
            layout["xaxis"].update({"title": {"text": "Variação (%)"}, "tickformat": "+.1f", "ticksuffix": "%"})
            layout["yaxis"] = dict(layout["yaxis"])  # type: ignore[index]
            layout["yaxis"].update({"title": {"text": ""}})
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("<div style='margin-top:1.4rem;'></div>", unsafe_allow_html=True)
            section_header("Cotações — Maiores Variações", "#3b82f6")
            from utils.ui import render_dark_table
            df_mv = df[["Ticker", "Preço", "Variação", "Volume", "_chg"]].reset_index(drop=True)
            cell_colors_mv: dict[tuple[int, str], str] = {
                (i, "Variação"): ("#10b981" if v >= 0 else "#ef4444")
                for i, v in enumerate(df_mv["_chg"])
                if isinstance(v, (int, float))
            }
            render_dark_table(df_mv[["Ticker", "Preço", "Variação", "Volume"]], cell_colors=cell_colors_mv)

    with col_right:
        section_header("Tendência Macro", "#10b981")
        if selic_data and isinstance(selic_data, list):
            df_s = pd.DataFrame(selic_data)
            df_s["data"] = pd.to_datetime(df_s["data"])
            df_s["valor"] = df_s["valor"].apply(to_float)
            df_s = df_s.dropna(subset=["valor"]).sort_values("data")
            df_s = apply_period_filter(df_s)
            if not any_period_filter_active():
                df_s = df_s.tail(48)

            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(
                x=df_s["data"], y=df_s["valor"],
                mode="lines", name="SELIC",
                line=dict(color="#3b82f6", width=2),
                fill="tozeroy", fillcolor="rgba(59,130,246,0.06)",
                hovertemplate="%{x|%b %Y}<br>SELIC: %{y:.2f}%<extra></extra>",
            ))
            if cambio_data and isinstance(cambio_data, list):
                df_c = pd.DataFrame(cambio_data)
                df_c["data"] = pd.to_datetime(df_c["data"])
                df_c["valor"] = df_c["valor"].apply(to_float)
                df_c = df_c.dropna(subset=["valor"]).sort_values("data")
                df_c = apply_period_filter(df_c)
                if not any_period_filter_active():
                    df_c = df_c.tail(48)
                fig_s.add_trace(go.Scatter(
                    x=df_c["data"], y=df_c["valor"],
                    mode="lines", name="USD/BRL",
                    line=dict(color="#f59e0b", width=2, dash="dash"),
                    yaxis="y2",
                    hovertemplate="%{x|%b %Y}<br>USD/BRL: R$%{y:.2f}<extra></extra>",
                ))
                layout = dict(CHART_LAYOUT)
                layout.update(
                    height=360, hovermode="x unified",
                    yaxis=dict(layout["yaxis"], title={"text": "Taxa (%)"}),
                    yaxis2=dict(
                        overlaying="y", side="right",
                        title={"text": "R$/USD"},
                        gridcolor="rgba(0,0,0,0)",
                        tickfont=dict(color="#f59e0b", size=10),
                    ),
                )
                fig_s.update_layout(**layout)
                fig_s.update_xaxes(title_text="")
            else:
                layout = dict(CHART_LAYOUT)
                layout.update(
                    height=360, hovermode="x unified",
                    yaxis=dict(layout["yaxis"], title={"text": "Taxa (%)"}),
                )
                fig_s.update_layout(**layout)
                fig_s.update_xaxes(title_text="")

            st.plotly_chart(fig_s, use_container_width=True)
        else:
            st.info("Dados macro indisponíveis — verifique a conectividade com a API.")
