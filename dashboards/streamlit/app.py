"""Finance — Premium Financial Intelligence Dashboard."""
from __future__ import annotations
from config import TICKER_UNIVERSE
import streamlit.components.v1 as components
import streamlit as st
import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


st.set_page_config(
    page_title="Finance · Inteligência Financeira",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Finance v2.0 — Plataforma de Análise Financeira Empresarial",
    },
)

# ── CSS Theme ─────────────────────────────────────────────────
_LOGO_B64 = ""
try:
    from styles.theme import inject_theme, _LOGO_B64
    inject_theme()
except Exception:
    pass  # Theme is cosmetic — app runs without it

# ── Sidebar Navigation ────────────────────────────────────────
_PAGES = [
    ("◉  Visão de Mercado",          "overview"),
    ("↗  Análise de Ações",          "analysis"),
    ("◈  Análise Fundamentalista",   "fundamentals"),
    ("◆  Insights de Investimento",  "insights"),
    ("⊞  Mapa de Calor",             "heatmap"),
    ("◎  Previsão ML",               "forecast"),
    ("≈  Indicadores Macro",         "macro"),
    ("☰  Rankings",                  "rankings"),
    ("⇄  Comparar Ativos",           "compare"),
]

with st.sidebar:
    # ── Logo ──────────────────────────────────────────────────
    if _LOGO_B64:
        _logo_css = (
            "<style>"
            ".ks-outer{width:90%;max-width:240px;"
            "filter:drop-shadow(0 8px 32px rgba(0,0,0,0.72));}"
            ".ks-wrap{position:relative;overflow:hidden;"
            "border-radius:16px;line-height:0;}"
            ".ks-wrap img{display:block;width:100%;height:auto;}"
            ".ks-shine{"
            "position:absolute;top:-20%;left:-130%;width:65%;height:140%;"
            "background:linear-gradient(115deg,"
            "transparent 20%,"
            "rgba(200,220,255,0.06) 38%,"
            "rgba(230,245,255,0.30) 50%,"
            "rgba(200,220,255,0.06) 62%,"
            "transparent 80%);"
            "animation:ks-glide 3.8s cubic-bezier(0.45,0,0.55,1) infinite;"
            "pointer-events:none;}"
            "@keyframes ks-glide{"
            "0%{left:-130%;}"
            "52%{left:165%;}"
            "100%{left:165%;}}"
            "</style>"
        )
        _logo_html = (
            "<div style='padding:1.4rem 1rem 1.2rem;"
            "border-bottom:1px solid rgba(255,255,255,0.05);"
            "margin-bottom:0.1rem;display:flex;justify-content:center;'>"
            "<div class='ks-outer'><div class='ks-wrap'>"
            f"<img src='data:image/png;base64,{_LOGO_B64}' alt='KingSide' />"
            "<div class='ks-shine'></div>"
            "</div></div></div>"
        )
        st.markdown(_logo_css + _logo_html, unsafe_allow_html=True)
    else:
        st.markdown(
            "<div style='padding:1.4rem 1rem 1rem;"
            "border-bottom:1px solid rgba(255,255,255,0.05);margin-bottom:0.25rem;'>"
            "<div style='font-size:1.35rem;font-weight:800;color:#f1f5f9;"
            "font-family:Inter,sans-serif;letter-spacing:-0.04em;line-height:1;'>"
            "Fin<span style='color:#3b82f6;'>ance</span></div>"
            "<div style='font-size:0.6rem;color:#334155;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.15em;margin-top:5px;'>"
            "Inteligência Financeira</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Navegação ─────────────────────────────────────────────
    page_labels = [label for label, _ in _PAGES]
    page_keys = [key for _, key in _PAGES]

    current_idx = page_keys.index(st.session_state.get("page", "overview")) \
        if st.session_state.get("page", "overview") in page_keys else 0

    selected_label = st.radio(
        "Menu",
        page_labels,
        index=current_idx,
        label_visibility="collapsed",
    )
    page_key = page_keys[page_labels.index(selected_label)]

    # ── Filtros de Período ────────────────────────────────────
    _ano_atual = datetime.date.today().year
    _anos = ["Todos"] + [str(a) for a in range(_ano_atual, 2014, -1)]
    _meses = [
        "Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ]
    _dias = ["Todos"] + [str(d) for d in range(1, 32)]

    st.markdown(
        "<div style='height:1px;background:rgba(255,255,255,0.04);margin:0.3rem 1rem 0;'></div>"
        "<div class='qv-sb-sec'>Ano</div>",
        unsafe_allow_html=True,
    )
    ano = st.selectbox(
        "Ano",
        options=_anos,
        index=0,
        label_visibility="collapsed",
        key="filter_ano",
    )

    st.markdown(
        "<div style='height:1px;background:rgba(255,255,255,0.04);margin:0.3rem 1rem 0;'></div>"
        "<div class='qv-sb-sec'>Mês</div>",
        unsafe_allow_html=True,
    )
    mes = st.selectbox(
        "Mês",
        options=_meses,
        index=0,
        label_visibility="collapsed",
        key="filter_mes",
    )

    st.markdown(
        "<div style='height:1px;background:rgba(255,255,255,0.04);margin:0.3rem 1rem 0;'></div>"
        "<div class='qv-sb-sec'>Dia</div>",
        unsafe_allow_html=True,
    )
    dia = st.selectbox(
        "Dia",
        options=_dias,
        index=0,
        label_visibility="collapsed",
        key="filter_dia",
    )

    # ── Ativo Selecionado ─────────────────────────────────────
    st.markdown(
        "<div style='height:1px;background:rgba(255,255,255,0.04);margin:0.3rem 1rem 0;'></div>"
        "<div class='qv-sb-sec'>Ativo Selecionado</div>",
        unsafe_allow_html=True,
    )
    _ticker_list = list(TICKER_UNIVERSE.keys())
    _saved = st.session_state.get("ticker", "PETR4")
    _default_idx = _ticker_list.index(_saved) if _saved in _ticker_list else 0
    ticker = st.selectbox(
        "Ativo",
        options=_ticker_list,
        index=_default_idx,
        format_func=lambda t: f"{t}  ·  {TICKER_UNIVERSE[t].split(' · ')[0]}",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺  Atualizar", use_container_width=True):
            st.cache_data.clear()
            st.session_state.pop("watchlist_data", None)
            st.rerun()
    with col2:
        if st.button("⊘  Cache", use_container_width=True):
            st.cache_data.clear()
            st.session_state.pop("watchlist_data", None)

    # ── Recolher / Versão ─────────────────────────────────────
    st.markdown(
        "<div style='height:1px;background:rgba(255,255,255,0.04);margin:1rem 1rem 0.5rem;'></div>",
        unsafe_allow_html=True,
    )
    components.html(
        """
        <style>
        html,body{margin:0;padding:0;background:transparent;}
        button{
            display:flex;align-items:center;justify-content:center;gap:8px;
            width:calc(100% - 2rem);margin:0 1rem;padding:0.52rem 0;
            background:rgba(59,130,246,0.07);
            border:1px solid rgba(59,130,246,0.2);
            border-radius:8px;color:#5b8fc9;
            font-size:0.73rem;font-weight:600;
            font-family:Inter,system-ui,sans-serif;
            letter-spacing:0.04em;cursor:pointer;
            transition:all 0.15s ease;box-sizing:border-box;
        }
        button:hover{
            background:rgba(59,130,246,0.14);
            border-color:rgba(59,130,246,0.42);
            color:#60a5fa;
            box-shadow:0 2px 12px rgba(59,130,246,0.14);
        }
        </style>
        <button onclick="
            var doc=window.parent.document;
            var b=doc.querySelector('[data-testid=\\'stBaseButton-headerNoPadding\\']')
              ||doc.querySelector('[data-testid=\\'collapsedControl\\']');
            if(b)b.click();
        ">&#8249; Recolher Menu</button>
        """,
        height=42,
    )
    st.markdown(
        "<div style='padding:0.4rem 1rem 0.4rem;text-align:center;'>"
        "<span style='font-size:0.52rem;color:#1e3a5f;font-weight:600;"
        "font-family:Inter,sans-serif;letter-spacing:0.1em;'>v2.0.0 · ENTERPRISE</span>"
        "</div>",
        unsafe_allow_html=True,
    )

st.session_state["page"]   = page_key
st.session_state["ticker"] = ticker

# ── Floating Sidebar Toggle (injected into parent doc) ────────
components.html(
    """
    <script>
    (function(){
        var doc=window.parent.document;
        if(doc.getElementById('qv-float-toggle'))return;
        var btn=doc.createElement('button');
        btn.id='qv-float-toggle';
        btn.title='Expandir / Recolher menu';
        btn.innerHTML='&#9776;';
        btn.style.cssText=[
            'position:fixed','bottom:1.6rem','right:1.6rem','z-index:99999',
            'width:44px','height:44px','border-radius:50%',
            'background:linear-gradient(135deg,#1d4ed8,#1e40af)',
            'border:1px solid rgba(59,130,246,0.45)',
            'color:#fff','font-size:1.1rem','cursor:pointer',
            'box-shadow:0 4px 20px rgba(37,99,235,0.5)',
            'display:flex','align-items:center','justify-content:center',
            'transition:transform 0.2s ease,box-shadow 0.2s ease',
        ].join(';');
        btn.onmouseenter=function(){
            this.style.transform='scale(1.1)';
            this.style.boxShadow='0 6px 28px rgba(37,99,235,0.7)';
        };
        btn.onmouseleave=function(){
            this.style.transform='scale(1)';
            this.style.boxShadow='0 4px 20px rgba(37,99,235,0.5)';
        };
        btn.onclick=function(){
            var b=doc.querySelector('[data-testid="stBaseButton-headerNoPadding"]')
              ||doc.querySelector('[data-testid="collapsedControl"]');
            if(b)b.click();
        };
        doc.body.appendChild(btn);
    })();
    </script>
    """,
    height=0,
)

# ── Market Header Strip ───────────────────────────────────────
try:
    from components.header import render_header
    render_header()
except Exception:
    pass

# ── API Status Banner (shown once if backend is offline) ──────
from utils.api import api_offline_banner
api_offline_banner()

# ── Page Title ────────────────────────────────────────────────
_PAGE_COLORS = {
    "overview": "#3b82f6", "analysis": "#3b82f6", "fundamentals": "#10b981",
    "insights": "#10b981", "heatmap": "#f59e0b", "forecast": "#a855f7",
    "macro": "#06b6d4", "rankings": "#f59e0b", "compare": "#ec4899",
}
_PAGE_LABELS = {
    "overview":     "Visão de Mercado",
    "analysis":     "Análise de Ações",
    "fundamentals": "Análise Fundamentalista",
    "insights":     "Insights de Investimento",
    "heatmap":      "Mapa de Calor",
    "forecast":     "Previsão ML",
    "macro":        "Indicadores Macro",
    "rankings":     "Rankings B3",
    "compare":      "Comparar Ativos",
}

label = _PAGE_LABELS.get(page_key, page_key)
color = _PAGE_COLORS.get(page_key, "#3b82f6")

st.markdown(
    f"<span style='color:{color};font-size:1.5rem;font-weight:800;"
    f"font-family:Inter,sans-serif;letter-spacing:-0.02em;'>{label}</span>",
    unsafe_allow_html=True,
)
st.divider()

# ── Page Router ───────────────────────────────────────────────
if page_key == "overview":
    from page_modules.market_overview import render
    render()

elif page_key == "analysis":
    from page_modules.stock_analysis import render
    render(ticker)

elif page_key == "fundamentals":
    from page_modules.fundamentals import render
    render(ticker)

elif page_key == "insights":
    from page_modules.investment_insights import render
    render()

elif page_key == "heatmap":
    from page_modules.market_heatmap import render
    render()

elif page_key == "forecast":
    from page_modules.forecasting import render
    render(ticker)

elif page_key == "macro":
    from page_modules.macro_indicators import render
    render()

elif page_key == "rankings":
    from page_modules.rankings import render
    render()

elif page_key == "compare":
    from page_modules.compare_assets import render
    render()
