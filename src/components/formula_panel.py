# ── FORMULA PANEL ──────────────────────────────────────────
"""Formula Inspector — definitions + per‑period computation table.

Mirrors JS ``buildFormulaPanel()``.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.helpers import format_currency


def render_formula_panel(monthly: list[dict]) -> None:
    """Render the Formula Inspector as a Streamlit expander."""
    sym = st.session_state.get("currency", "€")

    with st.expander("📐 Formula Inspector", expanded=False):
        st.markdown("#### Formula Definitions")

        defs = [
            ("Opening MRR",   "= Closing MRR of the prior period"),
            ("New Logo",       "= MRR from customers with no prior MRR history"),
            ("Upsell",         "= Σ MRR increases from existing customers"),
            ("Downsell",       "= Σ MRR decreases from existing customers (negative)"),
            ("Churn",          "= Σ full MRR lost from customers going to $0 (negative)"),
            ("Reactivation",   "= MRR from customers returning after prior churn"),
            ("Closing MRR",    "= Opening + New Logo + Upsell + Downsell + Churn + React"),
            ("GRR",            "= (Opening + Downsell + Churn) / Opening × 100"),
            ("NRR",            "= (Opening + Upsell + Downsell + Churn + React) / Opening × 100"),
            ("MRR Churn %",    "= |Churn| / Opening × 100"),
            ("New Logo %",     "= New Logo / Opening × 100"),
        ]

        cols = st.columns(2)
        half = (len(defs) + 1) // 2
        for i, (name, eq) in enumerate(defs):
            target = cols[0] if i < half else cols[1]
            target.markdown(f"**{name}** {eq}")

        st.markdown("---")
        st.markdown("#### Per‑Period Computation Table")

        rows: list[dict] = []
        for i, b in enumerate(monthly):
            exp = b["opening"] + b["new_logo"] + b["upsell"] + b["downsell"] + b["churn"] + b["react"]
            diff = abs(b["closing"] - exp)
            ch_pct = f"{abs(b['churn']) / b['opening'] * 100:.2f}%" if b["opening"] > 0 else "n/a"
            nl_pct = f"{b['new_logo'] / b['opening'] * 100:.2f}%" if b["opening"] > 0 else "n/a"
            acv = round(b["closing"] / b["cust_closing"]) if b["cust_closing"] > 0 else 0

            rows.append({
                "Period":   b["end_period"]["lbl"],
                "Opening":  "base" if i == 0 else format_currency(b["opening"], sym),
                "New Logo": format_currency(b["new_logo"], sym),
                "Upsell":   format_currency(b["upsell"], sym),
                "Downsell": format_currency(b["downsell"], sym),
                "Churn":    format_currency(b["churn"], sym),
                "React":    format_currency(b["react"], sym),
                "Closing":  format_currency(b["closing"], sym),
                "Check":    "✓" if diff < 0.01 else f"⚠ {format_currency(diff, sym)}",
                "GRR":      f"{b['grr']}%" if b.get("grr") is not None else "—",
                "NRR":      f"{b['nrr']}%" if b.get("nrr") is not None else "—",
                "Churn %":  ch_pct,
                "NL %":     nl_pct,
                "ACV":      format_currency(acv, sym),
                "Customers": f"{b['cust_closing']} (+{b['cust_new']} -{b['cust_churn']} ~{b['cust_react']})",
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True,
                     hide_index=True, height=500)
