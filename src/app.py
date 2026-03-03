# ── MRR BRIDGE ANALYZER — STREAMLIT APP ────────────────────
"""Main orchestrator — mirrors the JS ARR Bridge Analyzer v8.4.

Tab layout:
  Dashboard | MRR Bridge | Logo Bridge | MRR Trend | Components | ACV Trend
  Logo Retention | GRR Cohort | NRR Cohort | NRR Chart
  Revenue Insights | New Investments | Product Mix | Full Table

Run: streamlit run src/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# ── Make 'src/' importable ─────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

st.set_page_config(
    page_title="MRR Bridge Analyzer — Vortex Capital Partners",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Scrollable tabs CSS ───────────────────────────────────
st.markdown("""
<style>
div[data-baseweb="tab-list"] {
    overflow-x: auto;
    flex-wrap: nowrap !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
}
div[data-baseweb="tab-list"] button[role="tab"] {
    white-space: nowrap;
    flex-shrink: 0;
}
</style>
""", unsafe_allow_html=True)

# ── Imports (after path fix) ───────────────────────────────
from data.upload import render_upload
from data.engine import (
    filtered_data,
    build_bridge_range,
    all_monthly_bridges,
)
from components.sidebar import render_sidebar
from components.validation import render_validation
from charts.bridge import render_mrr_bridge, render_logo_bridge, render_period_selector
from charts.trend import render_trend, render_components
from charts.acv import render_acv
from charts.cohort import render_cohort_table, render_nrr_chart
from charts.concentration import render_concentration
from charts.full_table import render_full_table
from charts.new_logos import render_new_logos
from charts.product_mix import render_product_mix
from charts.dashboard import render_dashboard
from utils.helpers import format_currency


# ── Header ─────────────────────────────────────────────────
st.markdown(
    "<h2 style='margin-bottom:0'>📊 MRR Bridge Analyzer</h2>"
    "<p style='color:#6a7a9a;margin-top:0'>Vortex Capital Partners </p>",
    unsafe_allow_html=True,
)

# ── Upload gate ────────────────────────────────────────────
if not render_upload():
    st.info("Upload an MRR data file to get started.  \n"
            "Expected columns: one column per MRR period "
            "(e.g. `MRR_2023_01`) plus optional Company Name, Industry, Country.")
    st.stop()

# ── Sidebar: currency, mode, filters ──────────────────────
filters = render_sidebar()

# ── Compute ────────────────────────────────────────────────
df_raw = st.session_state["raw_data"]
mrr_periods = st.session_state["mrr_periods"]
col_map = st.session_state.get("col_map", {})

df = filtered_data(df_raw, filters)
monthly = all_monthly_bridges(df, mrr_periods)

# Total unique customers
if col_map.get("companyName") and col_map["companyName"] in df.columns:
    total_customers = df[col_map["companyName"]].nunique()
else:
    total_customers = len(df)

# ── Period strip ───────────────────────────────────────────
sym = st.session_state.get("currency", "€")
show_arr = st.session_state.get("show_arr", False)
lbl = "ARR" if show_arr else "MRR"

active_filters = sum(
    1 for f in filters.values()
    if 0 < len(f["selected"]) < len(f["vals"])
)
filter_txt = f" · **{active_filters} filter{'s' if active_filters > 1 else ''} active**" if active_filters else ""

first_p = monthly[0]["start_period"]["lbl"] if monthly else "—"
last_p = monthly[-1]["end_period"]["lbl"] if monthly else "—"
n_with_new = sum(1 for b in monthly if b["new_logo"] > 0)
n_with_churn = sum(1 for b in monthly if b["churn"] < 0)

st.markdown(
    f"**Coverage · {lbl} · {sym}** &nbsp; {first_p} → {last_p} &nbsp; | &nbsp; "
    f"{len(monthly)} months · {n_with_new} with new logos · {n_with_churn} with churn"
    f"{filter_txt}",
)

# ── Reconciliation checks (above date filter) ─────────────
render_validation(monthly)

# ── Period selectors (global date range for all tabs) ─────
bridge_start, bridge_end = render_period_selector("brg_")

# Create date-filtered monthly subset for non-cohort tabs
bridge_monthly = [b for idx, b in enumerate(monthly) if bridge_start <= idx <= bridge_end]

# ── Tabs ───────────────────────────────────────────────────
tab_names = [
    "Dashboard",
    "MRR Bridge", "Logo Bridge", "MRR Trend", "Components", "ACV Trend",
    "Logo Retention", "GRR Cohort", "NRR Cohort", "NRR Chart",
    "Revenue Insights", "New Investments", "Product Mix", "Full Table",
]
tabs = st.tabs(tab_names)

with tabs[0]:
    render_dashboard(df, mrr_periods, col_map, bridge_monthly)

with tabs[1]:
    render_mrr_bridge(df, mrr_periods)

with tabs[2]:
    render_logo_bridge(df, mrr_periods)

with tabs[3]:
    render_trend(bridge_monthly)

with tabs[4]:
    render_components(bridge_monthly)

with tabs[5]:
    render_acv(bridge_monthly)

with tabs[6]:
    render_cohort_table(df, mrr_periods, "logo")

with tabs[7]:
    render_cohort_table(df, mrr_periods, "grr")

with tabs[8]:
    render_cohort_table(df, mrr_periods, "nrr")

with tabs[9]:
    render_nrr_chart(df, mrr_periods)

with tabs[10]:
    render_concentration(df, mrr_periods, col_map)

with tabs[11]:
    render_new_logos(df, mrr_periods, col_map)

with tabs[12]:
    render_product_mix(df, mrr_periods, col_map)

with tabs[13]:
    render_full_table(bridge_monthly)

# ── Footer ─────────────────────────────────────────────────
st.markdown("---")
import_dt = st.session_state.get("import_datetime")
import_fn = st.session_state.get("import_filename", "")
if import_dt:
    st.caption(
        f"Imported: {import_fn} · {import_dt.strftime('%d %b %Y %H:%M')} · "
        f"{len(df_raw)} rows · {len(mrr_periods)} periods"
    )
