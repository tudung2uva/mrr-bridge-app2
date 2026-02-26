# ── FULL TABLE ─────────────────────────────────────────────
"""Full bridge data table with MRR/ARR toggle + period filtering.

Mirrors JS ``renderTablePane`` + ``_groupByYear``.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.helpers import format_currency


def _group_by_year(months: list[dict]) -> list[dict]:
    """Aggregate monthly bridges into yearly summaries.

    Mirrors JS ``_groupByYear``.
    """
    year_map: dict[str, list[dict]] = {}
    for b in months:
        yr = str(b["end_period"]["lbl"]).split()[-1]
        year_map.setdefault(yr, []).append(b)

    results: list[dict] = []
    for yr, ms in year_map.items():
        first, last = ms[0], ms[-1]
        flow_keys = ["new_logo", "upsell", "downsell", "churn", "react",
                     "cust_new", "cust_churn", "cust_react"]
        agg: dict = {
            "end_period": {"lbl": yr},
            "opening":      first["opening"],
            "closing":      last["closing"],
            "cust_opening": first["cust_opening"],
            "cust_closing": last["cust_closing"],
        }
        for k in flow_keys:
            agg[k] = sum(b.get(k, 0) for b in ms)

        # Weighted averages for NRR / GRR
        nrr_ms = [b for b in ms if b.get("nrr") is not None and b.get("opening", 0) > 0]
        agg["nrr"] = (
            round(sum(b["nrr"] * b["opening"] for b in nrr_ms) /
                  sum(b["opening"] for b in nrr_ms), 1)
            if nrr_ms else None
        )
        grr_ms = [b for b in ms if b.get("grr") is not None and b.get("opening", 0) > 0]
        agg["grr"] = (
            round(sum(b["grr"] * b["opening"] for b in grr_ms) /
                  sum(b["opening"] for b in grr_ms), 1)
            if grr_ms else None
        )
        results.append(agg)
    return results


def render_full_table(monthly: list[dict]) -> None:
    """Render the full bridge data table with MRR/ARR + period filter."""
    sym = st.session_state.get("currency", "€")
    show_arr = st.session_state.get("show_arr", False)
    mult = 12 if show_arr else 1
    rr_lbl = "ARR" if show_arr else "MRR"
    mrr_periods = st.session_state["mrr_periods"]
    bridge_start = st.session_state.get("bridge_start", 0)
    bridge_end = st.session_state.get("bridge_end", len(mrr_periods) - 1)

    # Filter to bridge period
    filter_active = st.checkbox("Filter to bridge period", value=True,
                                 key="tbl_filter")
    if filter_active:
        shown_monthly = [b for i, b in enumerate(monthly)
                         if bridge_start <= i <= bridge_end]
        period_label = f"{mrr_periods[bridge_start]['lbl']} → {mrr_periods[bridge_end]['lbl']}"
    else:
        shown_monthly = monthly
        period_label = "All periods"

    # In ARR mode collapse to yearly
    shown = _group_by_year(shown_monthly) if show_arr else shown_monthly

    st.caption(f"Showing: {period_label} · {len(shown)} columns · {rr_lbl} mode")

    # ── Build table data ───────────────────────────────────
    rows_def = [
        (f"Opening {rr_lbl}",     "opening",      "currency"),
        ("+ New Logo",            "new_logo",      "currency"),
        ("+ Upsell",              "upsell",        "currency"),
        ("+ Downsell",            "downsell",      "currency"),
        ("+ Churn",               "churn",         "currency"),
        ("+ Reactivation",        "react",         "currency"),
        (f"Closing {rr_lbl}",     "closing",       "currency"),
        ("—",                     "__div1",        "divider"),
        ("NRR %",                 "nrr",           "pct"),
        ("GRR %",                 "grr",           "pct"),
        (f"{rr_lbl} Churn %",     "__cp",          "calc_pct"),
        ("New Logo %",            "__np",          "calc_pct"),
        ("—",                     "__div2",        "divider"),
        ("Opening Customers",     "cust_opening",  "num"),
        ("+ New Logos",           "cust_new",      "num"),
        ("+ Reactivations",      "cust_react",     "num"),
        ("- Churned",            "cust_churn",      "num"),
        ("Closing Customers",    "cust_closing",    "num"),
        ("Logo Churn %",         "__lcp",          "calc_pct"),
        ("Logo New %",           "__lnp",          "calc_pct"),
    ]

    # Compute totals
    flow_rows = shown[1:] if not show_arr else shown  # skip base row in monthly mode
    totals: dict = {}
    for key in ["new_logo", "upsell", "downsell", "churn", "react",
                "cust_new", "cust_churn", "cust_react"]:
        totals[key] = sum(b.get(key, 0) for b in flow_rows)
    totals["opening"] = shown[0]["opening"] if shown else 0
    totals["closing"] = shown[-1]["closing"] if shown else 0
    totals["cust_opening"] = shown[0].get("cust_opening", 0) if shown else 0
    totals["cust_closing"] = shown[-1].get("cust_closing", 0) if shown else 0

    nrr_v = [b for b in flow_rows if b.get("nrr") is not None and b.get("opening", 0) > 0]
    totals["nrr"] = (
        round(sum(b["nrr"] * b["opening"] for b in nrr_v) /
              sum(b["opening"] for b in nrr_v), 1)
        if nrr_v else None
    )
    grr_v = [b for b in flow_rows if b.get("grr") is not None and b.get("opening", 0) > 0]
    totals["grr"] = (
        round(sum(b["grr"] * b["opening"] for b in grr_v) /
              sum(b["opening"] for b in grr_v), 1)
        if grr_v else None
    )

    # Build DataFrame for display
    data: dict[str, list[str]] = {"Metric": []}
    for b in shown:
        data[b["end_period"]["lbl"]] = []
    data[f"∑ {period_label}"] = []

    for label, key, fmt in rows_def:
        if fmt == "divider":
            continue
        data["Metric"].append(label)
        for b in shown:
            if key == "__cp":
                v = f"{abs(b['churn']) / b['opening'] * 100:.1f}%" if b.get("opening", 0) > 0 else "—"
            elif key == "__np":
                v = f"{b['new_logo'] / b['opening'] * 100:.1f}%" if b.get("opening", 0) > 0 else "—"
            elif key == "__lcp":
                v = f"{b['cust_churn'] / b['cust_opening'] * 100:.1f}%" if b.get("cust_opening", 0) > 0 else "—"
            elif key == "__lnp":
                v = f"{b['cust_new'] / b['cust_opening'] * 100:.1f}%" if b.get("cust_opening", 0) > 0 else "—"
            elif fmt == "pct":
                v = f"{b[key]}%" if b.get(key) is not None else "—"
            elif fmt == "num":
                v = str(b.get(key, "—"))
            else:  # currency
                v = format_currency(b[key] * mult, sym)
            data[b["end_period"]["lbl"]].append(v)

        # Total column
        if key == "__cp":
            tv = f"{abs(totals['churn']) / totals['opening'] * 100:.1f}%" if totals["opening"] > 0 else "—"
        elif key == "__np":
            tv = f"{totals['new_logo'] / totals['opening'] * 100:.1f}%" if totals["opening"] > 0 else "—"
        elif key == "__lcp":
            tv = f"{totals['cust_churn'] / totals['cust_opening'] * 100:.1f}%" if totals["cust_opening"] > 0 else "—"
        elif key == "__lnp":
            tv = f"{totals['cust_new'] / totals['cust_opening'] * 100:.1f}%" if totals["cust_opening"] > 0 else "—"
        elif fmt == "pct":
            tv = f"{totals[key]}%" if totals.get(key) is not None else "—"
        elif fmt == "num":
            tv = str(totals.get(key, "—"))
        else:
            tv = format_currency(totals[key] * mult, sym)
        data[f"∑ {period_label}"].append(tv)

    tdf = pd.DataFrame(data)
    st.dataframe(tdf, use_container_width=True, hide_index=True, height=700)
