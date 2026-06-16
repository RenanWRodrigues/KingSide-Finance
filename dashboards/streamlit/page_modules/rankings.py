"""Finance — Rankings Page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import SECTOR_COLORS
from utils.api import fetch, to_float
from utils.charts import ranking_bar_chart
from utils.ui import render_dark_table, section_header


def render() -> None:
    section_header("Rankings B3", "#f59e0b")
    st.info("Rankings buscam dados em tempo real — o primeiro carregamento pode levar até 60s. Cache de 1 hora.")

    limit = st.slider("Número de resultados", 5, 30, 15, key="rank_limit")

    tab1, tab2, tab3 = st.tabs(["Dividend Yield / Retorno", "Crescimento de Receita", "Momentum"])

    with tab1:
        _render_ranking_tab("/ranking/dividend", {"limite": limit}, "Top — Dividend Yield (%)")
    with tab2:
        _render_ranking_tab("/ranking/growth", {"limite": limit}, "Top — Crescimento de Receita / Retorno 1A (%)")
    with tab3:
        _render_ranking_tab("/ranking/momentum", {"limite": limit}, "Top — Momentum 1 Ano (%)")


def _render_ranking_tab(endpoint: str, params: dict, title: str) -> None:
    with st.spinner(f"Carregando {title}..."):
        data = fetch(endpoint, params, timeout=90)

    if not data or not data.get("items"):
        st.info("Nenhum dado disponível para este ranking.")
        return

    df = pd.DataFrame(data["items"])
    df["valor"] = df["valor"].apply(to_float)
    df = df.dropna(subset=["valor"])

    fig = ranking_bar_chart(df, title)
    st.plotly_chart(fig, use_container_width=True)

    display_cols = [c for c in ["posicao", "ticker", "nome", "setor", "valor"] if c in df.columns]
    df_display = df[display_cols].copy()
    df_display.columns = [c.title() for c in display_cols]

    val_col = "Valor"
    df_rank = df_display.reset_index(drop=True)
    cell_colors_rank: dict[tuple[int, str], str] = {}
    if val_col in df_rank.columns:
        for i, v in enumerate(df_rank[val_col]):
            if isinstance(v, (int, float)):
                cell_colors_rank[(i, val_col)] = "#10b981" if v > 0 else "#ef4444"
        df_rank[val_col] = df_rank[val_col].apply(
            lambda v: f"{v:.2f}" if isinstance(v, (int, float)) else "—"
        )
    if "Setor" in df_rank.columns:
        for i, v in enumerate(df_rank["Setor"]):
            cell_colors_rank[(i, "Setor")] = SECTOR_COLORS.get(str(v), "#64748b")
    render_dark_table(df_rank, cell_colors=cell_colors_rank)
