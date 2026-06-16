"""Finance — Premium Dark CSS Theme Injection."""
from __future__ import annotations

import base64
import io
import os

import streamlit as st


def _load_logo_image() -> str:
    try:
        from PIL import Image, ImageDraw, ImageFilter
        _this = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(os.path.dirname(_this)))
        img_path = os.path.join(root, "imagem", "KingSide.png")
        if not os.path.exists(img_path):
            return ""
        size = 270
        with Image.open(img_path) as img:
            img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle([6, 6, size - 6, size - 6], radius=48, fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(radius=20))
            img.putalpha(mask)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


_LOGO_B64 = _load_logo_image()


def _load_bg_image() -> str:
    try:
        from PIL import Image
        _this = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(os.path.dirname(_this)))
        img_path = os.path.join(root, "imagem", "Investiment.jpeg")
        if not os.path.exists(img_path):
            return ""
        with Image.open(img_path) as img:
            img = img.convert("RGB")
            if img.width > 1920:
                ratio = 1920 / img.width
                img = img.resize((1920, int(img.height * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=60, optimize=True)
            return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


_BG_B64 = _load_bg_image()

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Root Variables ─────────────────────────────────────────── */
:root {
    --bg-primary: #080d1a;
    --bg-secondary: #0d1424;
    --bg-card: #111827;
    --bg-card-hover: #162033;
    --border: rgba(255,255,255,0.05);
    --border-light: rgba(255,255,255,0.08);
    --accent: #2563eb;
    --accent-light: #3b82f6;
    --accent-glow: rgba(59,130,246,0.15);
    --success: #10b981;
    --success-bright: #00d4aa;
    --danger: #ef4444;
    --warning: #f59e0b;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #475569;
    --font-ui: 'Inter', system-ui, -apple-system, sans-serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
    --radius: 10px;
    --radius-sm: 6px;
    --radius-lg: 14px;
    --shadow: 0 4px 24px rgba(0,0,0,0.4);
    --shadow-sm: 0 2px 12px rgba(0,0,0,0.3);
    --transition: all 0.18s cubic-bezier(0.4,0,0.2,1);
}

/* ── Global Reset ────────────────────────────────────────────── */
* { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-primary) !important;
    font-family: var(--font-ui) !important;
    color: var(--text-primary) !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
    border-bottom: none !important;
}

[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }

div.block-container {
    padding: 0 2rem 2rem 2rem !important;
    max-width: 100% !important;
}

/* ── Sidebar ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #090e1c 0%, #0b1020 100%) !important;
    border-right: 1px solid var(--border) !important;
    padding-top: 0 !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}

[data-testid="stSidebarContent"] {
    padding: 0 !important;
}

/* ── Typography ─────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-ui) !important;
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

h1 { font-size: 1.75rem !important; }
h2 { font-size: 1.4rem !important; }
h3 { font-size: 1.15rem !important; }

p, span, div, label {
    font-family: var(--font-ui) !important;
    color: var(--text-secondary) !important;
}

/* ── Metric Cards ────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1.1rem 1.2rem !important;
    transition: var(--transition) !important;
    position: relative !important;
    overflow: hidden !important;
}

[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), transparent);
    opacity: 0;
    transition: var(--transition);
}

[data-testid="metric-container"]:hover {
    border-color: var(--border-light) !important;
    background: var(--bg-card-hover) !important;
    transform: translateY(-1px) !important;
    box-shadow: var(--shadow-sm) !important;
}

[data-testid="metric-container"]:hover::before { opacity: 1; }

[data-testid="stMetricLabel"] {
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: var(--text-muted) !important;
}

[data-testid="stMetricValue"] {
    font-size: 1.65rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    font-family: var(--font-mono) !important;
    letter-spacing: -0.02em !important;
    line-height: 1.2 !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    font-family: var(--font-mono) !important;
}

/* ── Tabs ────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
    padding: 0 !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: var(--text-muted) !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.65rem 1.1rem !important;
    margin-bottom: -1px !important;
    transition: var(--transition) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    border-radius: 0 !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-secondary) !important;
    background: rgba(255,255,255,0.02) !important;
}

.stTabs [aria-selected="true"][data-baseweb="tab"] {
    color: var(--accent-light) !important;
    border-bottom-color: var(--accent-light) !important;
    background: transparent !important;
}

.stTabs [data-baseweb="tab-panel"] {
    padding: 1.5rem 0 0 0 !important;
    background: transparent !important;
}

/* ── Buttons ─────────────────────────────────────────────────── */
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, var(--accent) 0%, #1d4ed8 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-family: var(--font-ui) !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 0.5rem 1.1rem !important;
    letter-spacing: 0.02em !important;
    transition: var(--transition) !important;
    box-shadow: 0 2px 12px rgba(37,99,235,0.3) !important;
}

[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 18px rgba(37,99,235,0.45) !important;
}

[data-testid="stButton"] > button:active {
    transform: translateY(0) !important;
}

/* ── Inputs ──────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-baseweb="input"] input,
[data-baseweb="select"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-ui) !important;
    font-size: 0.85rem !important;
    transition: var(--transition) !important;
}

[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
    outline: none !important;
}

/* ── Select / Multiselect ────────────────────────────────────── */
[data-baseweb="select"] > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
}

[data-baseweb="select"] > div:hover {
    border-color: var(--border-light) !important;
}

[data-baseweb="menu"] {
    background: #162033 !important;
    border: 1px solid var(--border-light) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
}

[data-baseweb="menu"] li {
    color: var(--text-secondary) !important;
    font-size: 0.84rem !important;
    transition: var(--transition) !important;
}

[data-baseweb="menu"] li:hover {
    background: rgba(59,130,246,0.12) !important;
    color: var(--text-primary) !important;
}

/* ── DataFrames ──────────────────────────────────────────────── */
[data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
}

[data-testid="stDataFrame"] table,
[data-testid="stDataFrameResizable"] table {
    background: var(--bg-card) !important;
    border-collapse: collapse !important;
    font-size: 0.83rem !important;
}

[data-testid="stDataFrame"] th {
    background: rgba(255,255,255,0.04) !important;
    color: var(--text-muted) !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 0.7rem 0.9rem !important;
}

[data-testid="stDataFrame"] td {
    color: var(--text-secondary) !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 0.6rem 0.9rem !important;
    font-family: var(--font-mono) !important;
    font-size: 0.82rem !important;
}

[data-testid="stDataFrame"] tr:hover td {
    background: rgba(255,255,255,0.02) !important;
}

/* ── Divider ─────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 1.5rem 0 !important;
}

/* ── Spinner ─────────────────────────────────────────────────── */
[data-testid="stSpinner"] {
    color: var(--accent-light) !important;
}

/* ── Alerts / Info ────────────────────────────────────────────── */
[data-testid="stAlert"] {
    background: rgba(59,130,246,0.08) !important;
    border: 1px solid rgba(59,130,246,0.2) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-secondary) !important;
    font-size: 0.84rem !important;
}

[data-testid="stAlert"][data-baseweb="notification"][kind="positive"] {
    background: rgba(16,185,129,0.08) !important;
    border-color: rgba(16,185,129,0.2) !important;
}

[data-testid="stAlert"][data-baseweb="notification"][kind="negative"] {
    background: rgba(239,68,68,0.08) !important;
    border-color: rgba(239,68,68,0.2) !important;
}

/* ── Custom Card Components ──────────────────────────────────── */
.qv-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.2rem;
    transition: var(--transition);
    position: relative;
    overflow: hidden;
}

.qv-card:hover {
    border-color: var(--border-light);
    background: var(--bg-card-hover);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

.qv-card-accent-top::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--success-bright));
}

.qv-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-family: var(--font-ui);
}

.qv-badge-buy    { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
.qv-badge-strong-buy { background: rgba(0,212,170,0.18); color: #00d4aa; border: 1px solid rgba(0,212,170,0.35); }
.qv-badge-sell   { background: rgba(239,68,68,0.12); color: #ef4444; border: 1px solid rgba(239,68,68,0.25); }
.qv-badge-strong-sell { background: rgba(239,68,68,0.2); color: #fca5a5; border: 1px solid rgba(239,68,68,0.4); }
.qv-badge-neutral { background: rgba(148,163,184,0.1); color: #94a3b8; border: 1px solid rgba(148,163,184,0.2); }

.qv-stat-label {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    font-family: var(--font-ui);
}

.qv-stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    font-family: var(--font-mono);
    letter-spacing: -0.02em;
    line-height: 1.2;
}

.qv-positive { color: #10b981 !important; }
.qv-negative { color: #ef4444 !important; }
.qv-neutral  { color: #94a3b8 !important; }
.qv-warning  { color: #f59e0b !important; }
.qv-accent   { color: #3b82f6 !important; }

/* ── Section Headers ─────────────────────────────────────────── */
.qv-section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 1rem;
    padding-bottom: 0.65rem;
    border-bottom: 1px solid var(--border);
}

.qv-section-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text-primary) !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-family: var(--font-ui);
}

.qv-section-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--accent-light);
    box-shadow: 0 0 8px var(--accent-light);
    flex-shrink: 0;
}

/* ── Header Strip ────────────────────────────────────────────── */
.qv-header {
    background: linear-gradient(135deg, #0d1424 0%, #0f1a2e 100%);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.8rem 1.2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
}

.qv-header-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    min-width: 90px;
    padding: 0 0.8rem;
    border-right: 1px solid var(--border);
}

.qv-header-item:last-child { border-right: none; }

.qv-header-label {
    font-size: 0.62rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    font-family: var(--font-ui);
}

.qv-header-value {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text-primary);
    font-family: var(--font-mono);
}

.qv-header-delta-pos { color: #10b981; font-size: 0.72rem; font-weight: 600; font-family: var(--font-mono); }
.qv-header-delta-neg { color: #ef4444; font-size: 0.72rem; font-weight: 600; font-family: var(--font-mono); }

/* ── Sidebar Components ──────────────────────────────────────── */
.qv-sidebar-logo {
    padding: 1.2rem 1rem 0.8rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0;
}

.qv-sidebar-logo-text {
    font-size: 1.3rem;
    font-weight: 800;
    color: var(--text-primary) !important;
    letter-spacing: -0.04em;
    font-family: var(--font-ui);
    line-height: 1;
}

.qv-sidebar-logo-sub {
    font-size: 0.62rem;
    font-weight: 500;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-top: 2px;
    font-family: var(--font-ui);
}

.qv-nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0.6rem 1rem;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: var(--transition);
    font-size: 0.84rem;
    font-weight: 500;
    color: var(--text-muted);
    font-family: var(--font-ui);
    margin: 1px 0.5rem;
    border: 1px solid transparent;
}

.qv-nav-item:hover {
    background: rgba(255,255,255,0.04);
    color: var(--text-secondary);
    border-color: var(--border);
}

.qv-nav-item.active {
    background: var(--accent-glow);
    color: var(--accent-light);
    border-color: rgba(59,130,246,0.2);
    font-weight: 600;
}

.qv-watchlist-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    border-radius: var(--radius-sm);
    transition: var(--transition);
    cursor: pointer;
    margin: 1px 0.5rem;
}

.qv-watchlist-item:hover {
    background: rgba(255,255,255,0.03);
}

.qv-ticker-badge {
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--text-primary);
    font-family: var(--font-mono);
}

.qv-ticker-change-pos {
    font-size: 0.72rem;
    font-weight: 600;
    color: #10b981;
    font-family: var(--font-mono);
    background: rgba(16,185,129,0.1);
    padding: 1px 6px;
    border-radius: 4px;
}

.qv-ticker-change-neg {
    font-size: 0.72rem;
    font-weight: 600;
    color: #ef4444;
    font-family: var(--font-mono);
    background: rgba(239,68,68,0.1);
    padding: 1px 6px;
    border-radius: 4px;
}

/* ── Score Progress Bar ──────────────────────────────────────── */
.qv-score-bar {
    height: 4px;
    border-radius: 2px;
    background: var(--border-light);
    overflow: hidden;
    margin-top: 6px;
}

.qv-score-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.6s ease;
}

/* ── Chart Container ─────────────────────────────────────────── */
.qv-chart-container {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.5rem;
    overflow: hidden;
}

/* ── Hide Streamlit Auto-Page Navigation ─────────────────────── */
[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNavSeparator"] {
    display: none !important;
}

/* ── Hide native sidebar header (keyboard shortcut icon text) ── */
[data-testid="stSidebarHeader"] {
    display: none !important;
}

/* ── Make iframes inside sidebar transparent ─────────────────── */
[data-testid="stSidebar"] iframe {
    background: transparent !important;
    border: none !important;
    display: block !important;
}

/* Remove the ghost height left by label_visibility="collapsed" */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
    height: 0 !important;
    min-height: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ── Sidebar Radio → Professional Nav List ───────────────────── */
/* Container */
[data-testid="stSidebar"] [data-testid="stRadio"] {
    margin: 0 !important;
    padding: 0.25rem 0.5rem !important;
}

/* Hide the baseweb visual radio circle (first child inside label) */
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {
    display: none !important;
}

/* Nav item */
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    padding: 0.52rem 0.9rem !important;
    border-radius: 7px !important;
    cursor: pointer !important;
    font-size: 0.845rem !important;
    font-weight: 500 !important;
    color: #475569 !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    transition: background 0.14s ease, color 0.14s ease, border-color 0.14s ease !important;
    border: 1px solid transparent !important;
    letter-spacing: 0.01em !important;
    line-height: 1.4 !important;
    margin: 1px 0 !important;
    gap: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label > div:last-child p,
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:last-child {
    color: inherit !important;
    font-family: inherit !important;
    font-size: inherit !important;
    font-weight: inherit !important;
    letter-spacing: inherit !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(255,255,255,0.04) !important;
    color: #94a3b8 !important;
    border-color: rgba(255,255,255,0.06) !important;
}

/* Selected nav item */
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: rgba(59,130,246,0.1) !important;
    color: #60a5fa !important;
    border-color: rgba(59,130,246,0.18) !important;
    font-weight: 600 !important;
}

/* ── Responsive tweaks ───────────────────────────────────────── */
@media (max-width: 768px) {
    div.block-container { padding: 0 0.75rem 1rem !important; }
    .qv-header-item { min-width: 70px; padding: 0 0.4rem; }
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
}

/* ── Plotly chart overrides ──────────────────────────────────── */
.js-plotly-plot .plotly .bg { fill: transparent !important; }
.js-plotly-plot .modebar { background: rgba(13,20,36,0.8) !important; border-radius: 6px !important; }
.js-plotly-plot .modebar-btn path { fill: #475569 !important; }
.js-plotly-plot .modebar-btn:hover path { fill: #94a3b8 !important; }

/* ── Scrollbar ───────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.18); }

/* ── Captions ────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] small,
.streamlit-expanderHeader,
small {
    color: var(--text-muted) !important;
    font-size: 0.72rem !important;
}

/* ── Sidebar Section Labels ──────────────────────────────────── */
.qv-sb-sec {
    padding: 0.65rem 1rem 0.2rem;
    font-size: 0.5rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: #2d4a68;
    font-family: Inter, sans-serif;
}

/* ── Sidebar Collapse Handle (native Streamlit button) ───────── */
[data-testid="collapsedControl"] {
    background: linear-gradient(180deg, #090e1c 0%, #0b1020 100%) !important;
    border: 1px solid rgba(59,130,246,0.3) !important;
    border-left: none !important;
    border-radius: 0 10px 10px 0 !important;
    width: 24px !important;
    transition: all 0.2s ease !important;
    box-shadow: 4px 0 20px rgba(0,0,0,0.5) !important;
}
[data-testid="collapsedControl"]:hover {
    background: rgba(59,130,246,0.1) !important;
    border-color: rgba(59,130,246,0.55) !important;
    width: 30px !important;
    box-shadow: 6px 0 24px rgba(59,130,246,0.15) !important;
}
[data-testid="collapsedControl"] svg {
    fill: #3b82f6 !important;
    width: 12px !important;
    height: 12px !important;
}

/* ── In-Sidebar Collapse Button ──────────────────────────────── */
.qv-collapse-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: calc(100% - 2rem);
    margin: 0 1rem;
    padding: 0.55rem 0;
    background: rgba(59,130,246,0.06);
    border: 1px solid rgba(59,130,246,0.18);
    border-radius: 8px;
    color: #4b7ab5;
    font-size: 0.74rem;
    font-weight: 600;
    font-family: Inter, sans-serif;
    letter-spacing: 0.04em;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease,
                box-shadow 0.15s ease;
}
.qv-collapse-btn:hover {
    background: rgba(59,130,246,0.13);
    border-color: rgba(59,130,246,0.4);
    color: #60a5fa;
    box-shadow: 0 2px 12px rgba(59,130,246,0.12);
}
.qv-collapse-btn svg {
    width: 13px;
    height: 13px;
    stroke: currentColor;
    fill: none;
    stroke-width: 2.5;
    stroke-linecap: round;
    stroke-linejoin: round;
    flex-shrink: 0;
}

/* ── Floating Sidebar Toggle (main area) ────────────────────── */
#qv-sidebar-toggle {
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    z-index: 9997;
}
#qv-sidebar-toggle button {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
    border: 1px solid rgba(59,130,246,0.4);
    color: #fff;
    font-size: 1.1rem;
    cursor: pointer;
    box-shadow: 0 4px 20px rgba(37,99,235,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
}
#qv-sidebar-toggle button:hover {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    box-shadow: 0 6px 28px rgba(37,99,235,0.7);
    transform: scale(1.08);
}

/* ── DataFrames — dark background (Streamlit 1.40 Glide Data Grid) ── */
[data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"],
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrameResizable"] > div,
[data-testid="stDataFrame"] > div > div,
[data-testid="stDataFrameResizable"] > div > div,
[data-testid="stDataFrame"] iframe,
[data-testid="stDataFrameResizable"] iframe {
    background: var(--bg-card) !important;
    border-radius: var(--radius) !important;
}

[data-testid="stDataFrame"] canvas,
[data-testid="stDataFrameResizable"] canvas {
    background: var(--bg-card) !important;
}

/* Glide Data Grid wrapper elements */
.glideDataEditor,
.dvn-stack,
.dvn-scroller,
.dvn-underlay,
.gdg-style,
[class*="glide"],
[class*="dvn-"] {
    background: var(--bg-card) !important;
    color: var(--text-secondary) !important;
}

/* Streamlit 1.40 dataframe scroll container */
[data-testid="stDataFrame"] [role="grid"],
[data-testid="stDataFrameResizable"] [role="grid"] {
    background: var(--bg-card) !important;
}
"""


def inject_theme() -> None:
    css = _CSS
    if _BG_B64:
        css += (
            "[data-testid='stAppViewContainer']{"
            "background:"
            f"linear-gradient(rgba(8,13,26,0.95),rgba(8,13,26,0.95)),"
            f"url('data:image/jpeg;base64,{_BG_B64}') center/cover no-repeat fixed !important;"
            "}"
        )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
