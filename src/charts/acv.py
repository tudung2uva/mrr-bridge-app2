# ── ACV CHARTS ─────────────────────────────────────────────
"""ACV per Customer line + Active Customers line.

Mirrors JS ``drawACVChart``.
"""
from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from utils.helpers import format_currency

_DARK_BG = "#0c0e14"
_GRID    = "#1a2030"


def render_acv(monthly: list[dict]) -> None:
    """Render side‑by‑side ACV per customer + Active customer charts."""
    sym = st.session_state.get("currency", "€")
    mult = 12 if st.session_state.get("show_arr", False) else 1
    lbl = "ARR" if st.session_state.get("show_arr", False) else "MRR"

    labels = [b["end_period"]["lbl"] for b in monthly]
    acv_vals = [
        round(b["closing"] * mult / b["cust_closing"], 1) if b["cust_closing"] > 0 else 0
        for b in monthly
    ]
    cust_vals = [b["cust_closing"] for b in monthly]

    c1, c2 = st.columns(2)

    with c1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=labels, y=acv_vals,
            mode="lines+markers",
            line=dict(color="#a070ff", width=2, shape="spline"),
            marker=dict(size=4, color="#a070ff"),
            fill="tozeroy", fillcolor="rgba(160,112,255,0.07)",
            name="ACV",
            hovertemplate="%{x}<br>ACV: %{customdata}<extra></extra>",
            customdata=[format_currency(v, sym) for v in acv_vals],
        ))
        fig1.update_layout(
            title=dict(text=f"<b>ACV per Customer</b><br><sup>Average {lbl} per active customer</sup>",
                       font=dict(size=13, color="#dde3f0")),
            plot_bgcolor=_DARK_BG, paper_bgcolor=_DARK_BG,
            font=dict(color="#6a7a9a", family="IBM Plex Mono"),
            height=300, margin=dict(l=50, r=20, t=60, b=40),
            yaxis=dict(gridcolor=_GRID), xaxis=dict(gridcolor=_GRID),
            showlegend=False,
        )
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=labels, y=cust_vals,
            mode="lines+markers",
            line=dict(color="#f0d060", width=2, shape="spline"),
            marker=dict(size=4, color="#f0d060"),
            fill="tozeroy", fillcolor="rgba(240,208,96,0.07)",
            name="Customers",
            hovertemplate="%{x}<br>Customers: %{y}<extra></extra>",
        ))
        fig2.update_layout(
            title=dict(text="<b>Active Customers</b><br><sup>Count of paying customers</sup>",
                       font=dict(size=13, color="#dde3f0")),
            plot_bgcolor=_DARK_BG, paper_bgcolor=_DARK_BG,
            font=dict(color="#6a7a9a", family="IBM Plex Mono"),
            height=300, margin=dict(l=50, r=20, t=60, b=40),
            yaxis=dict(gridcolor=_GRID), xaxis=dict(gridcolor=_GRID),
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Export table ───────────────────────────────────────
    with st.expander("📊 Data Table", expanded=False):
        tbl_data = pd.DataFrame({
            "Period": labels,
            f"ACV ({lbl})": [format_currency(v, sym) for v in acv_vals],
            "Active Customers": cust_vals,
        })
        st.dataframe(tbl_data, use_container_width=True, hide_index=True)
