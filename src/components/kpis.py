# ── KPI CARDS ──────────────────────────────────────────────
"""Render the essential KPI cards using native Streamlit.

Shows: Closing MRR/ARR (with CMGR), NRR (with T12M), GRR (with T12M),
Quick Ratio, Active Customers.
"""
from __future__ import annotations

import streamlit as st

from utils.helpers import format_currency, bench_color, bench_label, trailing_weighted


def render_kpis(bridge: dict, total_customers: int,
                monthly: list[dict] | None = None) -> None:
    """Draw the KPI row — 5 essential metrics."""
    sym = st.session_state.get("currency", "€")
    show_arr = st.session_state.get("show_arr", False)
    mult = 12 if show_arr else 1
    lbl = "ARR" if show_arr else "MRR"

    b = bridge
    closing_val = b["closing"] * mult
    cmgr_str = (
        f"{'+' if b['cmgr'] >= 0 else ''}{b['cmgr'] * 100:.2f}%/mo"
        if b["cmgr"] is not None else None
    )
    nrr_val = b["nrr"]
    grr_val = b["grr"]
    qr_val = b["quick_ratio"]

    # Trailing 12M metrics (if monthly data available)
    t12_nrr = trailing_weighted(monthly, "nrr", 12) if monthly else None
    t12_grr = trailing_weighted(monthly, "grr", 12) if monthly else None

    cols = st.columns(5)

    # 1. Closing MRR/ARR + CMGR
    with cols[0]:
        st.metric(
            f"Closing {lbl}",
            format_currency(closing_val, sym),
            delta=f"CMGR {cmgr_str}" if cmgr_str else None,
        )

    # 2. NRR + T12M
    with cols[1]:
        st.metric(
            "NRR",
            f"{nrr_val}%" if nrr_val is not None else "—",
        )
        if t12_nrr:
            st.caption(f"T12M: {t12_nrr}%")

    # 3. GRR + T12M
    with cols[2]:
        st.metric(
            "GRR",
            f"{grr_val}%" if grr_val is not None else "—",
        )
        if t12_grr:
            st.caption(f"T12M: {t12_grr}%")

    # 4. Quick Ratio
    with cols[3]:
        st.metric(
            "Quick Ratio",
            f"{qr_val}x" if qr_val is not None else "—",
        )

    # 5. Active Customers
    with cols[4]:
        net = b["cust_closing"] - b["cust_opening"]
        st.metric(
            "Active Customers",
            str(b["cust_closing"]),
            delta=f"net {'+' if net >= 0 else ''}{net}" if b["cust_opening"] > 0 else None,
        )
