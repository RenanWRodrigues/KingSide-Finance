"""Finance — Market Heatmap Page (Finviz-inspired)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import CHART_LAYOUT, SECTOR_COLORS
from utils.api import fetch_parallel, to_float
from utils.charts import market_treemap
from utils.ui import render_dark_table, section_header

_HEATMAP_TICKERS = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3", "SANB11",
    "WEGE3", "EMBR3", "ABEV3", "JBSS3", "BBSE3", "TAEE11",
    "EGIE3", "ELET3", "CMIG4", "PRIO3", "SUZB3", "MGLU3",
    "LREN3", "ASAI3", "TOTS3", "CYRE3", "RAIL3", "RENT3",
    "SBSP3", "RADL3", "VIVT3", "KLBN11", "CSAN3", "HAPV3",
]

_SECTOR_MAP: dict[str, str] = {
    "PETR4": "Petróleo e Gás", "PRIO3": "Petróleo e Gás", "CSAN3": "Petróleo e Gás",
    "VALE3": "Mineração",
    "ITUB4": "Bancos", "BBDC4": "Bancos", "BBAS3": "Bancos", "SANB11": "Bancos",
    "WEGE3": "Bens Industriais", "EMBR3": "Bens Industriais",
    "ABEV3": "Bebidas",
    "JBSS3": "Alimentos",
    "BBSE3": "Seguros",
    "TAEE11": "Energia Elétrica", "EGIE3": "Energia Elétrica",
    "ELET3": "Energia Elétrica", "CMIG4": "Energia Elétrica",
    "SUZB3": "Papel e Celulose", "KLBN11": "Papel e Celulose",
    "MGLU3": "Varejo", "LREN3": "Varejo",
    "ASAI3": "Varejo Alimentar",
    "TOTS3": "Tecnologia",
    "CYRE3": "Construção Civil",
    "RAIL3": "Logística",
    "RENT3": "Locação de Veículos",
    "SBSP3": "Saneamento",
    "RADL3": "Saúde", "HAPV3": "Saúde",
    "VIVT3": "Telecomunicações",
}

_MARKET_CAP = {
    "PETR4": 420, "VALE3": 350, "ITUB4": 280, "BBDC4": 120, "BBAS3": 160,
    "WEGE3": 180, "ABEV3": 130, "RENT3": 85, "EMBR3": 60, "RAIL3": 70,
    "TOTS3": 45, "RADL3": 55, "BBSE3": 70, "EGIE3": 40, "TAEE11": 30,
    "ELET3": 90, "CMIG4": 25, "SUZB3": 80, "PRIO3": 65, "SANB11": 75,
    "ASAI3": 35, "MGLU3": 20, "LREN3": 30, "JBSS3": 50, "CYRE3": 15,
    "HAPV3": 18, "SBSP3": 45, "VIVT3": 55, "CSAN3": 60, "KLBN11": 22,
}


def render() -> None:
    section_header("Mapa de Calor", "#f59e0b")
    st.caption("B3 — Visão Geral de Desempenho por Setor")

    c1, c2 = st.columns([2, 1])
    with c1:
        period = st.selectbox("Período", ["5d", "1mo", "3mo", "6mo", "1y"], key="hm_period")
    with c2:
        view_mode = st.radio("Visualização", ["Treemap", "Barras por Setor"], horizontal=True, key="hm_view")

    with st.spinner("Carregando dados do mapa de calor..."):
        results = fetch_parallel(
            [(f"/stocks/{t}/history", {"period": period}) for t in _HEATMAP_TICKERS],
            timeout=30,
        )

    hm_data = []
    for ticker, hist in zip(_HEATMAP_TICKERS, results):
        cotacoes = (hist or {}).get("cotacoes", [])
        if len(cotacoes) >= 2:
            last_p = to_float(cotacoes[-1].get("fechamento"))
            first_p = to_float(cotacoes[0].get("fechamento"))
            if last_p is None or first_p is None or first_p == 0:
                continue
            chg = (last_p / first_p - 1) * 100
        else:
            continue  # sem dados reais — omitir do mapa

        hm_data.append({
            "ticker": ticker,
            "setor": _SECTOR_MAP.get(ticker, "Outros"),
            "change_pct": round(chg, 2),
            "preco": last_p,
            "market_cap": float(_MARKET_CAP.get(ticker, 30)),
        })

    if not hm_data:
        st.warning("Nenhum dado de preço disponível para o período selecionado.")
        return

    if view_mode == "Treemap":
        fig = market_treemap(hm_data)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Tamanho = peso do Market Cap · Cor = variação % (verde = alta, vermelho = queda)")
    else:
        _render_sector_bars(hm_data)

    section_header("Tabela de Desempenho por Ativo", "#3b82f6")

    df = pd.DataFrame(hm_data).sort_values("change_pct", ascending=False)
    df["change_pct"] = df["change_pct"].round(2)
    df = df.rename(columns={
        "ticker": "Ticker", "setor": "Setor",
        "change_pct": f"Variação {period} (%)", "preco": "Preço (R$)",
    })

    chg_col = f"Variação {period} (%)"
    df_display = df[["Ticker", "Setor", chg_col, "Preço (R$)"]].reset_index(drop=True)
    cell_colors = {
        (i, chg_col): ("#10b981" if v > 0 else "#ef4444")
        for i, v in enumerate(df_display[chg_col])
        if isinstance(v, (int, float))
    }
    df_display[chg_col] = df_display[chg_col].apply(
        lambda v: f"{v:+.2f}%" if isinstance(v, (int, float)) else "—"
    )
    df_display["Preço (R$)"] = df_display["Preço (R$)"].apply(
        lambda v: f"R$ {v:.2f}" if isinstance(v, (int, float)) else "—"
    )
    render_dark_table(df_display, cell_colors=cell_colors, height=400)


def _render_sector_bars(hm_data: list[dict]) -> None:
    sector_agg: dict[str, list[float]] = {}
    for item in hm_data:
        sector_agg.setdefault(item["setor"], []).append(item["change_pct"])

    sector_rows = [
        {"Setor": s, "Variação (%)": sum(ch) / len(ch)}
        for s, ch in sector_agg.items()
    ]
    df_s = pd.DataFrame(sector_rows).sort_values("Variação (%)", ascending=True)

    colors = [
        SECTOR_COLORS.get(s, "#3b82f6") if v >= 0 else "#ef4444"
        for s, v in zip(df_s["Setor"], df_s["Variação (%)"])
    ]
    fig = go.Figure(go.Bar(
        x=df_s["Variação (%)"], y=df_s["Setor"], orientation="h",
        marker=dict(color=colors, opacity=0.85, line=dict(color="rgba(255,255,255,0.05)", width=0.5)),
        text=[f"{v:+.1f}%" for v in df_s["Variação (%)"]],
        textposition="outside", textfont=dict(color="#94a3b8", size=11),
        hovertemplate="<b>%{y}</b><br>%{x:+.2f}%<extra></extra>",
    ))
    layout = dict(CHART_LAYOUT)
    layout.update(height=460, margin=dict(t=20, b=20, l=150, r=60))
    layout["xaxis"] = dict(layout["xaxis"])  # type: ignore[index]
    layout["xaxis"].update({"tickformat": "+.1f", "ticksuffix": "%", "title": {"text": ""}})
    layout["yaxis"] = dict(layout["yaxis"])  # type: ignore[index]
    layout["yaxis"].update({"title": {"text": ""}})
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    fig.add_vline(x=0, line_dash="solid", line_color="rgba(255,255,255,0.1)")
    st.plotly_chart(fig, use_container_width=True)
