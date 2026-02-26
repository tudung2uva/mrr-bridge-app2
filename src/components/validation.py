# ── RECONCILIATION VALIDATION ──────────────────────────────
"""Render the collapsible reconciliation‑checks table.

Mirrors JS ``renderValidation(monthly)`` — verifies that
Opening + flows = Closing for every period.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.helpers import format_currency


def render_validation(monthly: list[dict]) -> None:
    """Show an expander with per‑period reconciliation checks."""
    sym = st.session_state.get("currency", "€")
    checks: list[dict] = []
    for b in monthly[1:]:
        exp = b["opening"] + b["new_logo"] + b["upsell"] + b["downsell"] + b["churn"] + b["react"]
        diff = round(abs(b["closing"] - exp), 2)
        checks.append({
            "Period":   b["end_period"]["lbl"],
            "Opening":  format_currency(b["opening"], sym),
            "New":      format_currency(b["new_logo"], sym),
            "Upsell":   format_currency(b["upsell"], sym),
            "Downsell": format_currency(b["downsell"], sym),
            "Churn":    format_currency(b["churn"], sym),
            "React":    format_currency(b["react"], sym),
            "Expected": format_currency(exp, sym),
            "Closing":  format_currency(b["closing"], sym),
            "Diff":     "—" if diff < 0.01 else format_currency(diff, sym),
            "OK":       "✓" if diff < 0.01 else "✗",
        })

    all_ok = all(c["OK"] == "✓" for c in checks)
    errs = sum(1 for c in checks if c["OK"] != "✓")
    header = (
        f"✓ All {len(checks)} periods balanced"
        if all_ok
        else f"⚠ {errs} imbalance{'s' if errs > 1 else ''} found"
    )

    with st.expander(f"Reconciliation Checks — {header}", expanded=False):
        st.caption("Opening + New Logo + Upsell + Downsell + Churn + React = Closing")
        st.dataframe(pd.DataFrame(checks), use_container_width=True, hide_index=True)
