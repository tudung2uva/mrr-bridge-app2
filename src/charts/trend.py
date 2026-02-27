# ── TREND & COMPONENTS CHARTS ──────────────────────────────
"""MRR Trend line chart + Growth Components stacked bar.

Mirrors JS ``drawTrendChart`` and ``drawComponentsChart``.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from utils.helpers import format_currency


_DARK_BG = "#0c0e14"
_GRID    = "#1a2030"


def render_trend(monthly: list[dict]) -> None:
    """MRR / ARR trend line chart."""
    sym = st.session_state.get("currency", "€")
    mult = 12 if st.session_state.get("show_arr", False) else 1
    lbl = "ARR" if st.session_state.get("show_arr", False) else "MRR"

    labels = [b["end_period"]["lbl"] for b in monthly]
    values = [b["closing"] * mult for b in monthly]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=values,
        mode="lines+markers",
        line=dict(color="#00c8f0", width=2, shape="spline"),
        marker=dict(size=4, color="#00c8f0"),
        fill="tozeroy",
        fillcolor="rgba(0,200,240,0.07)",
        name=lbl,
        hovertemplate="%{x}<br>" + lbl + ": %{customdata}<extra></extra>",
        customdata=[format_currency(v, sym) for v in values],
    ))
    fig.update_layout(
        title=dict(text=f"<b>{lbl} Trend</b><br><sup>Total {lbl} over all periods</sup>",
                   font=dict(size=14, color="#dde3f0")),
        plot_bgcolor=_DARK_BG, paper_bgcolor=_DARK_BG,
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=350, margin=dict(l=50, r=30, t=70, b=40),
        yaxis=dict(gridcolor=_GRID, tickfont=dict(size=10)),
        xaxis=dict(gridcolor=_GRID, tickfont=dict(size=10)),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_components(monthly: list[dict]) -> None:
    """Growth Components stacked bar chart + summary stats."""
    sym = st.session_state.get("currency", "€")
    mult = 12 if st.session_state.get("show_arr", False) else 1
    lbl = "ARR" if st.session_state.get("show_arr", False) else "MRR"

    labels = [b["end_period"]["lbl"] for b in monthly]
    components = [
        ("New Logo",     [b["new_logo"] * mult for b in monthly], "rgba(0,223,160,0.8)"),
        ("Upsell",       [b["upsell"]   * mult for b in monthly], "rgba(0,200,128,0.8)"),
        ("Reactivation", [b["react"]    * mult for b in monthly], "rgba(255,176,32,0.8)"),
        ("Downsell",     [b["downsell"] * mult for b in monthly], "rgba(200,34,68,0.8)"),
        ("Churn",        [b["churn"]    * mult for b in monthly], "rgba(255,61,90,0.8)"),
    ]

    fig = go.Figure()
    for name, vals, color in components:
        fig.add_trace(go.Bar(
            x=labels, y=vals, name=name,
            marker_color=color,
            hovertemplate="%{x}<br>" + name + ": %{customdata}<extra></extra>",
            customdata=[format_currency(v, sym) for v in vals],
        ))

    fig.update_layout(
        barmode="relative",
        hovermode="x unified",
        title=dict(text="<b>Growth Components</b><br><sup>Monthly movements across all periods</sup>",
                   font=dict(size=14, color="#dde3f0")),
        plot_bgcolor=_DARK_BG, paper_bgcolor=_DARK_BG,
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=380, margin=dict(l=50, r=30, t=70, b=40),
        yaxis=dict(gridcolor=_GRID, tickfont=dict(size=10)),
        xaxis=dict(gridcolor=_GRID, tickfont=dict(size=10)),
        legend=dict(
                    font=dict(size=10, color="#fff"),
                    orientation="h",
                    y=1.05,   # move above the plot
                    x=1,      # right align
                    xanchor="right",
                    yanchor="bottom"
                ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary stats row
    tot_nl = sum(b["new_logo"] for b in monthly)
    tot_up = sum(b["upsell"]   for b in monthly)
    tot_dn = abs(sum(b["downsell"] for b in monthly))
    tot_ch = abs(sum(b["churn"]    for b in monthly))

    nn = [b for b in monthly if b.get("nrr") is not None and b.get("opening", 0) > 0]
    ng = [b for b in monthly if b.get("grr") is not None and b.get("opening", 0) > 0]
    wtd_nrr = (
        round(sum(b["nrr"] * b["opening"] for b in nn) /
              sum(b["opening"] for b in nn), 1)
        if nn else None
    )
    wtd_grr = (
        round(sum(b["grr"] * b["opening"] for b in ng) /
              sum(b["opening"] for b in ng), 1)
        if ng else None
    )

    cols = st.columns(6)
    cols[0].metric("Total New Logo", format_currency(tot_nl, sym, short=True))
    cols[1].metric("Total Upsell",   format_currency(tot_up, sym, short=True))
    cols[2].metric("Total Downsell", format_currency(tot_dn, sym, short=True))
    cols[3].metric("Total Churn",    format_currency(tot_ch, sym, short=True))
    cols[4].metric("Wtd NRR",        f"{wtd_nrr}%" if wtd_nrr else "—")
    cols[5].metric("Wtd GRR",        f"{wtd_grr}%" if wtd_grr else "—")
