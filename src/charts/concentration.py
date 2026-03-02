# ── CONCENTRATION / REVENUE INSIGHTS ───────────────────────
"""Revenue per customer / industry horizontal bar chart + stats.

Mirrors JS ``drawConcentrationChart`` / ``setRevView``.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from data.engine import get_mrr
from utils.constants import PALETTE
from utils.helpers import format_currency


def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert '#RRGGBB' to 'rgba(r,g,b,a)'."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def render_concentration(df, mrr_periods, col_map: dict) -> None:
    """Render revenue concentration chart with customer/industry toggle."""
    sym = st.session_state.get("currency", "€")
    mult = 12 if st.session_state.get("show_arr", False) else 1
    lbl = "ARR" if st.session_state.get("show_arr", False) else "MRR"
    bridge_start = st.session_state.get("bridge_start", 0)
    bridge_end = st.session_state.get("bridge_end", len(mrr_periods) - 1)

    # Build per‑customer data — average MRR across the full selected range
    n_periods = bridge_end - bridge_start + 1
    customers: list[dict] = []
    for _, row in df.iterrows():
        total_mrr = 0.0
        active_periods = 0
        for pi in range(bridge_start, bridge_end + 1):
            m = get_mrr(row, mrr_periods[pi]["key"])
            if m > 0:
                total_mrr += m
                active_periods += 1
        if active_periods == 0:
            continue
        avg_mrr = total_mrr / active_periods
        name = str(row.get(col_map.get("companyName", ""), "Unknown") or "Unknown")
        industry = str(row.get(col_map.get("industry", ""), "Unknown") or "Unknown")
        customers.append({"name": name, "mrr": avg_mrr, "industry": industry})

    # Aggregate product-line rows by customer name
    agg: dict[str, dict] = {}
    for c in customers:
        if c["name"] in agg:
            agg[c["name"]]["mrr"] += c["mrr"]
        else:
            agg[c["name"]] = dict(c)
    customers = list(agg.values())

    customers.sort(key=lambda c: c["mrr"], reverse=True)

    if not customers:
        st.info(f"No active customers in {mrr_periods[bridge_start]['lbl']} → {mrr_periods[bridge_end]['lbl']}.")
        return

    # Toggle
    view = st.radio("View", ["By Customer", "By Industry"],
                     horizontal=True, key="conc_view")

    if view == "By Industry":
        by_ind: dict[str, float] = {}
        for c in customers:
            by_ind[c["industry"]] = by_ind.get(c["industry"], 0) + c["mrr"]
        entries = sorted(by_ind.items(), key=lambda e: e[1], reverse=True)
        labels = [e[0] for e in entries]
        values = [e[1] * mult for e in entries]
        chart_title = "Revenue by Industry"
        chart_sub = f"{lbl} — {mrr_periods[bridge_start]['lbl']} → {mrr_periods[bridge_end]['lbl']} · avg per period · all industries"
    else:
        top = customers[:25]
        labels = [c["name"] for c in top]
        values = [c["mrr"] * mult for c in top]
        chart_title = "Revenue per Customer"
        chart_sub = f"{lbl} — {mrr_periods[bridge_start]['lbl']} → {mrr_periods[bridge_end]['lbl']} · avg per period · top 25"

    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]

    fig = go.Figure(go.Bar(
        y=labels, x=values,
        orientation="h",
        marker_color=[_hex_to_rgba(c, 0.73) for c in colors],
        marker_line_color=colors,
        marker_line_width=1,
        hovertemplate="%{y}: %{customdata}<extra></extra>",
        customdata=[format_currency(v, sym) for v in values],
    ))
    fig.update_layout(
        title=dict(text=f"<b>{chart_title}</b><br><sup>{chart_sub}</sup>",
                   font=dict(size=14, color="#dde3f0")),
        plot_bgcolor="#0c0e14", paper_bgcolor="#0c0e14",
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=max(350, len(labels) * 22),
        margin=dict(l=150, r=30, t=70, b=40),
        xaxis=dict(gridcolor="#1a2030", tickfont=dict(size=10), side="top"),
        yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    total = sum(c["mrr"] for c in customers)
    if total > 0 and customers:
        top1 = customers[0]["mrr"] / total * 100
        top3 = sum(c["mrr"] for c in customers[:3]) / total * 100
        top10 = sum(c["mrr"] for c in customers[:10]) / total * 100

        cols = st.columns(4)
        cols[0].metric("#1 customer", f"{top1:.1f}%")
        cols[1].metric("Top 3", f"{top3:.1f}%")
        cols[2].metric("Top 10", f"{top10:.1f}%")
        cols[3].metric("Active", len(customers))

    # Export table
    import pandas as pd_conc
    with st.expander("📊 Data Table", expanded=False):
        tbl_rows = []
        for c in customers:
            tbl_rows.append({
                "Customer": c["name"],
                "Industry": c["industry"],
                f"Avg {lbl}": format_currency(c["mrr"] * mult, sym),
                "% of Total": f"{c['mrr'] / total * 100:.1f}%" if total > 0 else "—",
            })
        st.dataframe(pd_conc.DataFrame(tbl_rows), use_container_width=True, hide_index=True)
