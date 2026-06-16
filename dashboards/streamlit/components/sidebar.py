"""Finance Dashboard — Premium Sidebar Component."""
from __future__ import annotations

import streamlit as st

from config import PAGES, TICKER_UNIVERSE
from utils.api import fetch_parallel, to_float


_WATCHLIST = ["PETR4", "VALE3", "ITUB4", "WEGE3", "ABEV3"]


def _watchlist_data() -> dict[str, float | None]:
    results = fetch_parallel(
        [(f"/stocks/{t}/history", {"period": "5d"}) for t in _WATCHLIST],
        timeout=6,
    )
    changes: dict[str, float | None] = {}
    for ticker, data in zip(_WATCHLIST, results):
        cotacoes = (data or {}).get("cotacoes", [])
        if len(cotacoes) >= 2:
            last = to_float(cotacoes[-1].get("fechamento"))
            prev = to_float(cotacoes[-2].get("fechamento"))
            if last and prev and prev != 0:
                changes[ticker] = (last - prev) / prev * 100
            else:
                changes[ticker] = None
        else:
            changes[ticker] = None
    return changes


def render_sidebar() -> tuple[str, str]:
    """Render premium sidebar. Returns (page_key, ticker)."""
    with st.sidebar:
        # ── Logo ───────────────────────────────────────────────
        st.markdown(
            "<div style='padding:1.2rem 1rem 0.8rem;"
            "border-bottom:1px solid rgba(255,255,255,0.05);margin-bottom:0.5rem;'>"
            "<div style='font-size:1.3rem;font-weight:800;color:#f1f5f9;"
            "letter-spacing:-0.04em;font-family:Inter,sans-serif;line-height:1;'>"
            "Finance</div>"
            "<div style='font-size:0.58rem;font-weight:500;color:#334155;"
            "text-transform:uppercase;letter-spacing:0.14em;margin-top:3px;"
            "font-family:Inter,sans-serif;'>Financial Intelligence Platform</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # ── Navigation ─────────────────────────────────────────
        st.markdown(
            "<div style='padding:0.3rem 1rem 0.3rem;font-size:0.58rem;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.14em;color:#334155;"
            "font-family:Inter,sans-serif;'>Navigation</div>",
            unsafe_allow_html=True,
        )

        page_labels = [label for label, _ in PAGES]
        page_keys = [key for _, key in PAGES]
        current = st.session_state.get("page", "overview")
        selected_idx = page_keys.index(current) if current in page_keys else 0

        selected_label = st.radio(
            "nav",
            page_labels,
            index=selected_idx,
            label_visibility="collapsed",
        )
        page_key = page_keys[page_labels.index(selected_label)]

        st.markdown(
            "<hr style='margin:0.4rem 0.5rem;border:none;"
            "border-top:1px solid rgba(255,255,255,0.05);'>",
            unsafe_allow_html=True,
        )

        # ── Ticker Input ────────────────────────────────────────
        st.markdown(
            "<div style='padding:0.3rem 1rem 0.3rem;font-size:0.58rem;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.14em;color:#334155;"
            "font-family:Inter,sans-serif;'>Ticker</div>",
            unsafe_allow_html=True,
        )

        ticker = st.text_input(
            "ticker_search",
            value=st.session_state.get("ticker", "PETR4"),
            placeholder="ex: VALE3",
            label_visibility="collapsed",
        ).upper().strip() or "PETR4"

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Refresh", use_container_width=True):
                st.cache_data.clear()
                st.session_state.pop("watchlist_data", None)
                st.rerun()
        with col2:
            if st.button("Clear Cache", use_container_width=True):
                st.cache_data.clear()
                st.session_state.pop("watchlist_data", None)

        st.markdown(
            "<hr style='margin:0.4rem 0.5rem;border:none;"
            "border-top:1px solid rgba(255,255,255,0.05);'>",
            unsafe_allow_html=True,
        )

        # ── Watchlist ───────────────────────────────────────────
        st.markdown(
            "<div style='padding:0.3rem 1rem 0.4rem;font-size:0.58rem;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.14em;color:#334155;"
            "font-family:Inter,sans-serif;'>Watchlist</div>",
            unsafe_allow_html=True,
        )

        if st.session_state.get("watchlist_data") is None:
            with st.spinner(""):
                wl_data = _watchlist_data()
                st.session_state["watchlist_data"] = wl_data
        else:
            wl_data = st.session_state["watchlist_data"]

        for t in _WATCHLIST:
            change = wl_data.get(t)
            if change is not None:
                sign = "+" if change >= 0 else ""
                bg = "rgba(16,185,129,0.1)" if change >= 0 else "rgba(239,68,68,0.1)"
                clr = "#10b981" if change >= 0 else "#ef4444"
                badge = (
                    f"<span style='font-size:0.7rem;font-weight:600;color:{clr};"
                    f"font-family:\"JetBrains Mono\",monospace;background:{bg};"
                    f"padding:1px 6px;border-radius:4px;'>{sign}{change:.2f}%</span>"
                )
            else:
                badge = "<span style='color:#475569;font-size:0.7rem;'>—</span>"

            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:0.45rem 1rem;border-radius:6px;cursor:pointer;'>"
                f"<span style='font-size:0.78rem;font-weight:700;color:#f1f5f9;"
                f"font-family:\"JetBrains Mono\",monospace;'>{t}</span>"
                f"{badge}</div>",
                unsafe_allow_html=True,
            )

        # ── Footer ──────────────────────────────────────────────
        st.markdown(
            "<div style='padding:0.8rem 1rem;border-top:1px solid rgba(255,255,255,0.05);"
            "font-size:0.58rem;color:#334155;font-family:Inter,sans-serif;"
            "text-align:center;letter-spacing:0.04em;margin-top:0.5rem;'>"
            "Finance v2.0.0 · Enterprise Analytics</div>",
            unsafe_allow_html=True,
        )

    st.session_state["page"] = page_key
    st.session_state["ticker"] = ticker
    return page_key, ticker
