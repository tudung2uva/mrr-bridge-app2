# ── COHORT ANALYSIS ────────────────────────────────────────
"""Cohort retention heatmap tables (logo / GRR / NRR) +
NRR line chart by cohort.

Mirrors JS ``buildAndRenderCohortTable``, ``cohortColor``,
``renderCohortPane``, ``drawNRRChart``.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from data.engine import build_cohorts
from utils.constants import PALETTE
from utils.helpers import format_currency


def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert '#RRGGBB' to 'rgba(r,g,b,a)'."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Heatmap colour logic ──────────────────────────────────

def _cohort_color(val: float | None, ctype: str, empty_cohort: bool = False) -> str:
    """Return a CSS background‑color string for a cohort cell.

    Mirrors JS ``cohortColor``.
    If *empty_cohort* is True, the cell belongs to a month with no new
    customers — render as grey.
    """
    if empty_cohort:
        return "background-color:#12151d;color:#4a5a7a;font-style:italic"
    if val is None:
        return "background-color:#080a0f;color:#1a2030"
    if ctype == "nrr":
        if val >= 120:
            return "background-color:rgba(0,220,130,0.35);color:#00dfa0;font-weight:600"
        if val >= 100:
            return "background-color:rgba(0,220,130,0.18);color:#00c890"
        if val >= 80:
            return "background-color:rgba(255,176,32,0.15);color:#ffb020"
        return "background-color:rgba(255,61,90,0.15);color:#ff3d5a"
    # logo or grr
    if val >= 95:
        return "background-color:rgba(0,220,130,0.35);color:#00dfa0;font-weight:600"
    if val >= 85:
        return "background-color:rgba(0,220,130,0.18);color:#00c890"
    if val >= 70:
        return "background-color:rgba(255,176,32,0.15);color:#ffb020"
    if val >= 50:
        return "background-color:rgba(255,100,50,0.15);color:#ff8050"
    return "background-color:rgba(255,61,90,0.15);color:#ff3d5a"


def _build_cohort_html(cohorts: list[dict], ctype: str, gran: str) -> str:
    """Build an HTML heatmap table for a given retention type."""
    sym = st.session_state.get("currency", "€")
    ret_key = {"logo": "logo_ret", "grr": "grr_ret", "nrr": "nrr_ret"}[ctype]
    max_offset = max((len(c[ret_key]) for c in cohorts), default=0)

    # Pad every cohort's retention array to max_offset so all rows
    # have the same width (younger cohorts get trailing None cells).
    for c in cohorts:
        arr = c[ret_key]
        if len(arr) < max_offset:
            c[ret_key] = arr + [None] * (max_offset - len(arr))

    prefix = "Y" if gran == "yearly" else "M"
    mh = [f"{prefix}{i}" for i in range(max_offset)]

    # Weighted average row
    wavg: list[float | None] = []
    for offset in range(max_offset):
        tw, ws = 0.0, 0.0
        for c in cohorts:
            if c.get("_empty"):
                continue
            v = c[ret_key][offset] if offset < len(c[ret_key]) else None
            if v is not None:
                w = c["init_mrr"] if ctype in ("grr", "nrr") else c["size"]
                ws += v * w
                tw += w
        wavg.append(round(ws / tw, 1) if tw > 0 else None)

    size_label = "Init MRR" if ctype in ("grr", "nrr") else "Customers"

    html = '<div style="overflow-x:auto;font-family:IBM Plex Mono,monospace;font-size:11px">'
    html += '<table style="border-collapse:collapse;width:100%">'
    html += '<thead><tr style="color:#6a7a9a">'
    html += f'<th style="text-align:left;padding:4px 8px;min-width:90px;font-weight:700">Cohort</th>'
    html += f'<th style="padding:4px 8px;min-width:80px;font-weight:700">{size_label}</th>'
    for h in mh:
        html += f'<th style="padding:4px 6px;font-weight:700">{h}</th>'
    html += '</tr></thead><tbody>'

    for c in cohorts:
        is_empty = c.get("_empty", False)
        sv = format_currency(c["init_mrr"], sym, short=True) if ctype in ("grr", "nrr") else str(c["size"])
        row_style = "color:#3a4560" if is_empty else ""
        html += f'<tr><td style="padding:4px 8px;font-weight:700;color:{"#3a4560" if is_empty else "#dde3f0"}">{c["label"]}</td>'
        html += f'<td style="padding:4px 8px;color:{"#3a4560" if is_empty else "#6a7a9a"}">{sv}</td>'
        for i in range(max_offset):
            v = c[ret_key][i] if i < len(c[ret_key]) else None
            if is_empty:
                style = _cohort_color(0, ctype, empty_cohort=True)
                txt = "N/A"
            else:
                style = _cohort_color(v, ctype)
                txt = f"{v:.1f}%" if v is not None else "N/A"
            if v is None and not is_empty:
                style = "background-color:#12151d;color:#4a5a7a;font-style:italic"
            html += f'<td style="padding:3px 5px;text-align:center;{style}">{txt}</td>'
        html += '</tr>'

    # Weighted avg row
    html += '<tr style="border-top:2px solid #2a3050"><td style="padding:4px 8px;color:#ffb020;font-weight:700">Weighted avg</td><td></td>'
    for v in wavg:
        style = _cohort_color(v, ctype) + ";font-weight:700"
        txt = f"{v:.1f}%" if v is not None else ""
        html += f'<td style="padding:3px 5px;text-align:center;{style}">{txt}</td>'
    html += '</tr></tbody></table></div>'

    wt_lbl = "initial MRR" if ctype in ("nrr", "grr") else "cohort size"
    html += f'<div style="font-size:9px;color:#4a5a7a;margin-top:6px">Weighted by {wt_lbl} · M0=sign-up month · GRR uses running minimum per customer</div>'
    return html


# ── Public render functions ────────────────────────────────

def render_cohort_table(df, mrr_periods, ctype: str) -> None:
    """Render a single cohort retention heatmap table.

    *ctype* is ``"logo"``, ``"grr"``, or ``"nrr"``.
    """
    titles = {
        "logo": "Logo Retention by Cohort",
        "grr":  "Gross Revenue Retention by Cohort",
        "nrr":  "Net Revenue Retention by Cohort",
    }
    subs = {
        "logo": "% of customers still active",
        "grr":  "% of initial MRR retained — running minimum, can only fall",
        "nrr":  "Cohort MRR vs initial — above 100% = net expansion",
    }
    bmarks = {
        "logo": "Benchmarks: >95% enterprise · >80% SMB",
        "grr":  "Benchmarks: >90% enterprise · >80% SMB",
        "nrr":  "Benchmarks: >120% enterprise · >100% SMB",
    }

    gran = st.radio(
        "Granularity", ["Monthly", "Yearly"], horizontal=True,
        key=f"cohort_gran_{ctype}",
    ).lower()
    st.markdown(f"**{titles[ctype]}**")

    cohorts = build_cohorts(df, mrr_periods, gran)
    if not cohorts:
        st.info("No cohort data available.")
        return

    # Fill in missing periods so every month/year has a row
    if gran == "yearly":
        existing = {c["label"] for c in cohorts}
        all_years = sorted({str(p["year"]) for p in mrr_periods})
        for yr_lbl in all_years:
            if yr_lbl not in existing:
                cohorts.append({
                    "label": yr_lbl, "start_idx": 0, "size": 0,
                    "init_mrr": 0, "logo_ret": [], "grr_ret": [], "nrr_ret": [],
                    "_empty": True,
                })
        cohorts.sort(key=lambda c: c["label"])
    else:
        existing = {c["label"] for c in cohorts}
        for p in mrr_periods:
            if p["lbl"] not in existing:
                cohorts.append({
                    "label": p["lbl"], "start_idx": 0, "size": 0,
                    "init_mrr": 0, "logo_ret": [], "grr_ret": [], "nrr_ret": [],
                    "_empty": True,
                })
        # Sort by period order
        lbl_order = {p["lbl"]: i for i, p in enumerate(mrr_periods)}
        cohorts.sort(key=lambda c: lbl_order.get(c["label"], 9999))

    html = _build_cohort_html(cohorts, ctype, gran)
    st.markdown(html, unsafe_allow_html=True)

    # Explainer text below the table
    st.caption(f"{subs[ctype]}  ·  {bmarks[ctype]}")


def render_nrr_chart(df, mrr_periods) -> None:
    """NRR by cohort line chart with year filter.

    Mirrors JS ``drawNRRChart``.
    """
    gran = st.radio(
        "Granularity", ["Monthly", "Yearly"], horizontal=True,
        key="cohort_gran_nrr_chart",
    ).lower()
    cohorts = build_cohorts(df, mrr_periods, gran)
    if not cohorts:
        st.info("No cohort data available.")
        return

    # Year filter
    years = sorted({str(p["year"]) for p in mrr_periods})
    year_opts = ["All"] + years
    nrr_year = st.selectbox("Cohort Year Filter", year_opts,
                             index=0, key="nrr_year_filter")

    if nrr_year != "All":
        cohorts = [c for c in cohorts if nrr_year in str(c["label"])]

    if not cohorts:
        st.warning(f"No cohorts for {nrr_year}")
        return

    max_len = max(len(c["nrr_ret"]) for c in cohorts)
    prefix = "Y" if gran == "yearly" else "M"
    x_labels = [f"{prefix}{i}" for i in range(max_len)]

    fig = go.Figure()

    # Individual cohort lines — limit legend to newest 11 + weighted avg
    show_in_legend_limit = 11
    legend_start = max(0, len(cohorts) - show_in_legend_limit)
    for i, c in enumerate(cohorts):
        fig.add_trace(go.Scatter(
            x=x_labels[:len(c["nrr_ret"])],
            y=c["nrr_ret"],
            mode="lines",
            name=c["label"],
            line=dict(color=_hex_to_rgba(PALETTE[i % len(PALETTE)], 0.53), width=1.5),
            hovertemplate=c["label"] + ": %{y}%<extra></extra>",
            showlegend=(i >= legend_start),
        ))

    # Weighted average line
    avg_line: list[float | None] = []
    for offset in range(max_len):
        ws, wt = 0.0, 0.0
        for c in cohorts:
            v = c["nrr_ret"][offset] if offset < len(c["nrr_ret"]) else None
            if v is not None:
                ws += v * c["init_mrr"]
                wt += c["init_mrr"]
        avg_line.append(round(ws / wt, 1) if wt > 0 else None)

    fig.add_trace(go.Scatter(
        x=x_labels, y=avg_line,
        mode="lines+markers",
        name="Weighted Avg",
        line=dict(color="#ffb020", width=3),
        marker=dict(size=3, color="#ffb020"),
        fill="tozeroy", fillcolor="rgba(255,176,32,0.06)",
    ))

    # 100% reference line
    fig.add_hline(y=100, line_dash="dash", line_color="#3a4560",
                  annotation_text="100% = break-even",
                  annotation_font_color="#4a5a7a",
                  annotation_font_size=9)

    fig.update_layout(
        title=dict(text="<b>NRR by Cohort</b><br><sup>Cumulative NRR since cohort start</sup>",
                   font=dict(size=14, color="#dde3f0")),
        plot_bgcolor="#0c0e14", paper_bgcolor="#0c0e14",
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=500, margin=dict(l=50, r=30, t=70, b=60),
        hovermode="x unified",
        yaxis=dict(gridcolor="#1a2030", ticksuffix="%", title="NRR %",
                   nticks=8, showgrid=True),
        xaxis=dict(gridcolor="#1a2030", title="Months since cohort start",
                   nticks=12, showgrid=True),
        legend=dict(font=dict(size=9, color="#dde3f0"),
                    orientation="v", x=1.02, y=1, xanchor="left",
                    yanchor="top", bgcolor="rgba(0,0,0,0)"),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    a12 = avg_line[12] if len(avg_line) > 12 else None
    a24 = avg_line[24] if len(avg_line) > 24 else None
    a36 = avg_line[36] if len(avg_line) > 36 else None
    cols = st.columns(6)
    cols[0].metric("12M NRR",  f"{a12:.1f}%" if a12 is not None else "—")
    cols[1].metric("24M NRR",  f"{a24:.1f}%" if a24 is not None else "—")
    cols[2].metric("36M NRR",  f"{a36:.1f}%" if a36 is not None else "—")
    cols[3].metric("Cohorts",  len(cohorts))
    avg_init = sum(c["init_mrr"] for c in cohorts) / len(cohorts) if cohorts else 0
    sym = st.session_state.get("currency", "€")
    cols[4].metric("Avg Init MRR", format_currency(avg_init, sym, short=True))
    valid_12 = [c for c in cohorts if len(c["nrr_ret"]) > 12 and c["nrr_ret"][12] is not None]
    best_12 = max((c["nrr_ret"][12] for c in valid_12), default=None)
    cols[5].metric("Best 12M", f"{best_12:.1f}%" if best_12 is not None else "—")
