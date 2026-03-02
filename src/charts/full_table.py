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

    # ── Row definitions with categories ────────────────────
    # (label, key, fmt, category)
    # category: None = normal row, str = section header (rendered as bold separator)
    rows_def = [
        ("MRR / ARR Flows", None,            "section",   None),
        (f"Opening {rr_lbl}",     "opening",      "currency", True),
        ("+ New Logo",            "new_logo",      "currency", False),
        ("+ Upsell",              "upsell",        "currency", False),
        ("+ Downsell",            "downsell",      "currency", False),
        ("+ Churn",               "churn",         "currency", False),
        ("+ Reactivation",        "react",         "currency", False),
        (f"Closing {rr_lbl}",     "closing",       "currency", True),
        ("Retention Metrics", None,            "section",   None),
        ("NRR %",                 "nrr",           "pct",      False),
        ("GRR %",                 "grr",           "pct",      False),
        (f"{rr_lbl} Churn %",     "__cp",          "calc_pct", False),
        ("New Logo %",            "__np",          "calc_pct", False),
        ("Customer Counts", None,            "section",   None),
        ("Opening Customers",     "cust_opening",  "num",      True),
        ("+ New Logos",           "cust_new",      "num",      False),
        ("+ Reactivations",      "cust_react",     "num",      False),
        ("- Churned",            "cust_churn",      "num",      False),
        ("Closing Customers",    "cust_closing",    "num",      True),
        ("Logo Churn %",         "__lcp",          "calc_pct", False),
        ("Logo New %",           "__lnp",          "calc_pct", False),
    ]

    # Compute totals
    flow_rows = shown[1:] if not show_arr else shown
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

    def _cell_val(b, key, fmt):
        if key == "__cp":
            return f"{abs(b['churn']) / b['opening'] * 100:.1f}%" if b.get("opening", 0) > 0 else "—"
        elif key == "__np":
            return f"{b['new_logo'] / b['opening'] * 100:.1f}%" if b.get("opening", 0) > 0 else "—"
        elif key == "__lcp":
            return f"{b['cust_churn'] / b['cust_opening'] * 100:.1f}%" if b.get("cust_opening", 0) > 0 else "—"
        elif key == "__lnp":
            return f"{b['cust_new'] / b['cust_opening'] * 100:.1f}%" if b.get("cust_opening", 0) > 0 else "—"
        elif fmt == "pct":
            return f"{b[key]}%" if b.get(key) is not None else "—"
        elif fmt == "num":
            return str(b.get(key, "—"))
        else:
            return format_currency(b[key] * mult, sym)

    def _total_val(key, fmt):
        if key == "__cp":
            return f"{abs(totals['churn']) / totals['opening'] * 100:.1f}%" if totals["opening"] > 0 else "—"
        elif key == "__np":
            return f"{totals['new_logo'] / totals['opening'] * 100:.1f}%" if totals["opening"] > 0 else "—"
        elif key == "__lcp":
            return f"{totals['cust_churn'] / totals['cust_opening'] * 100:.1f}%" if totals["cust_opening"] > 0 else "—"
        elif key == "__lnp":
            return f"{totals['cust_new'] / totals['cust_opening'] * 100:.1f}%" if totals["cust_opening"] > 0 else "—"
        elif fmt == "pct":
            return f"{totals[key]}%" if totals.get(key) is not None else "—"
        elif fmt == "num":
            return str(totals.get(key, "—"))
        else:
            return format_currency(totals[key] * mult, sym)

    # ── Detect year boundaries for separators ──────────────
    col_years = []
    for b in shown:
        lbl_text = b["end_period"]["lbl"]
        yr = lbl_text.split()[-1] if " " in lbl_text else lbl_text
        col_years.append(yr)

    # ── Build styled HTML table ────────────────────────────
    cell_css = "padding:6px 10px;text-align:right;white-space:nowrap"
    hdr_css = "padding:6px 10px;text-align:right;white-space:nowrap;color:#6a7a9a;font-weight:700;font-size:12px"
    metric_css = "padding:6px 10px;text-align:left;white-space:nowrap;color:#dde3f0"

    html = '<div style="overflow-x:auto;font-family:IBM Plex Mono,monospace;font-size:13px">'    
    html += '<table style="border-collapse:collapse;width:100%">'

    # Header row
    html += '<thead><tr>'
    html += f'<th style="{hdr_css};text-align:left;position:sticky;left:0;background:#0c0e14;z-index:1">Metric</th>'
    for i, b in enumerate(shown):
        lbl_text = b["end_period"]["lbl"]
        border = "border-left:2px solid #2a3050;" if i > 0 and col_years[i] != col_years[i - 1] else ""
        html += f'<th style="{hdr_css};{border}">{lbl_text}</th>'
    html += f'<th style="{hdr_css};border-left:2px solid #6a9ae8;color:#6a9ae8">∑ {mrr_periods[bridge_start]["lbl"]} → {mrr_periods[bridge_end]["lbl"]}</th>'
    html += '</tr></thead><tbody>'

    for label, key, fmt, is_bold in rows_def:
        if fmt == "section":
            # Category separator row
            ncols = len(shown) + 2
            html += (
                f'<tr><td colspan="{ncols}" style="padding:10px 8px 4px 8px;'
                f'font-weight:700;color:#6a9ae8;font-size:13px;'
                f'border-bottom:1px solid #2a3050">{label}</td></tr>'
            )
            continue

        bold_style = "font-weight:700;" if is_bold else ""
        row_color = "#dde3f0" if is_bold else "#8a9aba"
        html += '<tr>'
        html += f'<td style="{metric_css};{bold_style}position:sticky;left:0;background:#0c0e14;z-index:1">{label}</td>'
        for i, b in enumerate(shown):
            v = _cell_val(b, key, fmt)
            border = "border-left:2px solid #2a3050;" if i > 0 and col_years[i] != col_years[i - 1] else ""
            html += f'<td style="{cell_css};{bold_style}color:{row_color};{border}">{v}</td>'
        tv = _total_val(key, fmt)
        html += f'<td style="{cell_css};{bold_style}color:#6a9ae8;border-left:2px solid #6a9ae8">{tv}</td>'
        html += '</tr>'

    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)
