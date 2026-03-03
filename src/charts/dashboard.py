# ── DASHBOARD TAB ──────────────────────────────────────────
"""High-level dashboard view: key KPIs + mini charts.

Shows the most important metrics at a glance with clickable
mini-charts for MRR/ARR Yearly Bridge, Logo Yearly Bridge, and ACV Trend.
"""
from __future__ import annotations

import collections

import plotly.graph_objects as go
import streamlit as st

from data.engine import build_bridge_range
from utils.constants import (CLR_OPENING, CLR_NEW_LOGO, CLR_UPSELL,
                              CLR_REACT, CLR_DOWNSELL, CLR_CHURN, CLR_CLOSING)
from utils.helpers import format_currency


_DARK_BG = "#0c0e14"
_GRID    = "#1a2030"


def _hex_to_rgba(hex_color: str, alpha: float = 0.73) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _wf_bars(values, measures):
    """Compute base/top pairs for a manual waterfall."""
    bases, heights = [], []
    run = 0.0
    for v, m in zip(values, measures):
        if m in ("absolute", "total"):
            bases.append(0)
            heights.append(v)
            run = v
        else:
            if v >= 0:
                bases.append(run)
                heights.append(v)
            else:
                bases.append(run + v)
                heights.append(abs(v))
            run += v
    return bases, heights


def _mini_yearly_bridge(df, mrr_periods, si, ei, sym, mult, lbl) -> go.Figure:
    """Build a compact yearly MRR/ARR bridge waterfall."""
    year_groups: dict[int, list[int]] = collections.OrderedDict()
    for idx in range(si, ei + 1):
        yr = mrr_periods[idx]["year"]
        year_groups.setdefault(yr, []).append(idx)

    labels, values, measures, colors, texts = [], [], [], [], []
    prev_yr_ei = None

    for yi, (yr, idxs) in enumerate(year_groups.items()):
        yr_si, yr_ei = idxs[0], idxs[-1]
        if yi == 0:
            if yr_si == yr_ei:
                b = build_bridge_range(df, mrr_periods, yr_si, yr_si)
                opening = b["opening"] * mult
                labels.append(mrr_periods[yr_si]["lbl"])
                values.append(opening)
                measures.append("absolute")
                colors.append(CLR_OPENING)
                texts.append(format_currency(opening, sym, short=True))
                prev_yr_ei = yr_ei
                continue
            b = build_bridge_range(df, mrr_periods, yr_si, yr_ei)
            opening = b["opening"] * mult
            labels.append(mrr_periods[yr_si]["lbl"])
            values.append(opening)
            measures.append("absolute")
            colors.append(CLR_OPENING)
            texts.append(format_currency(opening, sym, short=True))
        else:
            bridge_from = prev_yr_ei if prev_yr_ei is not None else yr_si
            b = build_bridge_range(df, mrr_periods, bridge_from, yr_ei)
            opening = b["opening"] * mult

        for name, val, color in [
            ("New", b["new_logo"] * mult, CLR_NEW_LOGO),
            ("Up",  b["upsell"] * mult,   CLR_UPSELL),
            ("Re",  b["react"] * mult,    CLR_REACT),
            ("Dn",  b["downsell"] * mult, CLR_DOWNSELL),
            ("Ch",  b["churn"] * mult,    CLR_CHURN),
        ]:
            if abs(val) < 0.01:
                continue
            labels.append(name)
            values.append(val)
            measures.append("relative")
            colors.append(color)
            pct = val / opening * 100 if opening else 0
            texts.append(f"{pct:+.0f}%")

        closing = b["closing"] * mult
        is_last = yi == len(year_groups) - 1
        labels.append(mrr_periods[yr_ei]["lbl"])
        values.append(closing)
        measures.append("total")
        colors.append(CLR_CLOSING if is_last else CLR_OPENING)
        texts.append(format_currency(closing, sym, short=True))
        prev_yr_ei = yr_ei

    if not labels:
        return None

    bases, heights = _wf_bars(values, measures)
    fig = go.Figure(go.Bar(
        x=list(range(len(labels))), y=heights, base=bases,
        text=texts, textposition="outside",
        textfont=dict(size=9, family="IBM Plex Mono"),
        marker_color=[_hex_to_rgba(c) for c in colors],
        marker_line_color=colors, marker_line_width=1,
        hovertemplate="%{customdata}<extra></extra>",
        customdata=[f"{l}: {t}" for l, t in zip(labels, texts)],
    ))
    fig.update_layout(
        title=dict(text=f"<b>{lbl} Bridge – Yearly</b>",
                   font=dict(size=12, color="#dde3f0")),
        plot_bgcolor=_DARK_BG, paper_bgcolor=_DARK_BG,
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=300, margin=dict(l=30, r=20, t=50, b=40),
        yaxis=dict(gridcolor=_GRID, tickfont=dict(size=9), showticklabels=False),
        xaxis=dict(tickmode="array", tickvals=list(range(len(labels))),
                   ticktext=labels, tickfont=dict(size=8)),
        showlegend=False, bargap=0.25,
    )
    return fig


def _mini_yearly_logo_bridge(df, mrr_periods, si, ei) -> go.Figure:
    """Build a compact yearly logo count bridge waterfall."""
    year_groups: dict[int, list[int]] = collections.OrderedDict()
    for idx in range(si, ei + 1):
        yr = mrr_periods[idx]["year"]
        year_groups.setdefault(yr, []).append(idx)

    labels, values, measures, colors, texts = [], [], [], [], []
    prev_yr_ei = None

    for yi, (yr, idxs) in enumerate(year_groups.items()):
        yr_si, yr_ei = idxs[0], idxs[-1]
        if yi == 0:
            if yr_si == yr_ei:
                b = build_bridge_range(df, mrr_periods, yr_si, yr_si)
                labels.append(mrr_periods[yr_si]["lbl"])
                values.append(b["cust_opening"])
                measures.append("absolute")
                colors.append(CLR_OPENING)
                texts.append(str(b["cust_opening"]))
                prev_yr_ei = yr_ei
                continue
            b = build_bridge_range(df, mrr_periods, yr_si, yr_ei)
            labels.append(mrr_periods[yr_si]["lbl"])
            values.append(b["cust_opening"])
            measures.append("absolute")
            colors.append(CLR_OPENING)
            texts.append(str(b["cust_opening"]))
        else:
            bridge_from = prev_yr_ei if prev_yr_ei is not None else yr_si
            b = build_bridge_range(df, mrr_periods, bridge_from, yr_ei)

        opening = b["cust_opening"]
        for name, val, color in [
            ("New",    b["cust_new"],    CLR_NEW_LOGO),
            ("Re",     b["cust_react"],  CLR_REACT),
            ("Churn", -b["cust_churn"],  CLR_CHURN),
        ]:
            if val == 0:
                continue
            labels.append(name)
            values.append(val)
            measures.append("relative")
            colors.append(color)
            texts.append(f"{val:+d}")

        closing = b["cust_closing"]
        is_last = yi == len(year_groups) - 1
        labels.append(mrr_periods[yr_ei]["lbl"])
        values.append(closing)
        measures.append("total")
        colors.append(CLR_CLOSING if is_last else CLR_OPENING)
        texts.append(str(closing))
        prev_yr_ei = yr_ei

    if not labels:
        return None

    bases, heights = _wf_bars(values, measures)
    fig = go.Figure(go.Bar(
        x=list(range(len(labels))), y=heights, base=bases,
        text=texts, textposition="outside",
        textfont=dict(size=9, family="IBM Plex Mono"),
        marker_color=[_hex_to_rgba(c) for c in colors],
        marker_line_color=colors, marker_line_width=1,
        hovertemplate="%{customdata}<extra></extra>",
        customdata=[f"{l}: {t}" for l, t in zip(labels, texts)],
    ))
    fig.update_layout(
        title=dict(text="<b>Logo Bridge – Yearly</b>",
                   font=dict(size=12, color="#dde3f0")),
        plot_bgcolor=_DARK_BG, paper_bgcolor=_DARK_BG,
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=300, margin=dict(l=30, r=20, t=50, b=40),
        yaxis=dict(gridcolor=_GRID, tickfont=dict(size=9), showticklabels=False),
        xaxis=dict(tickmode="array", tickvals=list(range(len(labels))),
                   ticktext=labels, tickfont=dict(size=8)),
        showlegend=False, bargap=0.25,
    )
    return fig


def _mini_acv_trend(monthly, sym, mult, lbl) -> go.Figure:
    """Build a compact ACV trend line chart."""
    labels_x = [b["end_period"]["lbl"] for b in monthly]
    acv_vals = []
    for b in monthly:
        if b["cust_closing"] > 0:
            acv_vals.append(b["closing"] * mult / b["cust_closing"])
        else:
            acv_vals.append(0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels_x, y=acv_vals,
        mode="lines+markers",
        line=dict(color="#a070ff", width=2, shape="spline"),
        marker=dict(size=3, color="#a070ff"),
        fill="tozeroy", fillcolor="rgba(160,112,255,0.07)",
        hovertemplate="%{x}<br>ACV: %{customdata}<extra></extra>",
        customdata=[format_currency(v, sym) for v in acv_vals],
    ))
    fig.update_layout(
        title=dict(text=f"<b>ACV Trend ({lbl})</b>",
                   font=dict(size=12, color="#dde3f0")),
        plot_bgcolor=_DARK_BG, paper_bgcolor=_DARK_BG,
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=300, margin=dict(l=30, r=20, t=50, b=40),
        yaxis=dict(gridcolor=_GRID, tickfont=dict(size=9)),
        xaxis=dict(gridcolor=_GRID, tickfont=dict(size=8)),
        showlegend=False,
    )
    return fig


def _mini_active_customers(monthly) -> go.Figure | None:
    """Build a compact active-customers trend line chart."""
    if not monthly:
        return None
    labels_x = [b["end_period"]["lbl"] for b in monthly]
    cust_vals = [b["cust_closing"] for b in monthly]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels_x, y=cust_vals,
        mode="lines+markers",
        line=dict(color="#00dfa0", width=2, shape="spline"),
        marker=dict(size=3, color="#00dfa0"),
        fill="tozeroy", fillcolor="rgba(0,223,160,0.07)",
        hovertemplate="%{x}<br>Customers: %{y}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Active Customers</b>",
                   font=dict(size=12, color="#dde3f0")),
        plot_bgcolor=_DARK_BG, paper_bgcolor=_DARK_BG,
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=300, margin=dict(l=30, r=20, t=50, b=40),
        yaxis=dict(gridcolor=_GRID, tickfont=dict(size=9)),
        xaxis=dict(gridcolor=_GRID, tickfont=dict(size=8)),
        showlegend=False,
    )
    return fig


# ── PUBLIC ─────────────────────────────────────────────────

def render_dashboard(df, mrr_periods, col_map, monthly) -> None:
    """Render the high-level Dashboard tab."""
    sym = st.session_state.get("currency", "€")
    show_arr = st.session_state.get("show_arr", False)
    mult = 12 if show_arr else 1
    lbl = "ARR" if show_arr else "MRR"
    si = st.session_state.get("bridge_start", 0)
    ei = st.session_state.get("bridge_end", len(mrr_periods) - 1)

    b_selected = build_bridge_range(df, mrr_periods, si, ei)

    # Last-12M cumulative NRR/GRR (static trailing window, independent of selected range)
    if len(mrr_periods) > 1:
        global_ei = len(mrr_periods) - 1
        t12_si = max(0, global_ei - 12)
        b_last12 = build_bridge_range(df, mrr_periods, t12_si, global_ei)
        t12_nrr = b_last12.get("nrr")
        t12_grr = b_last12.get("grr")
    else:
        t12_nrr = None
        t12_grr = None

    # ── CAGR calculation ──────────────────────────────────
    closing_val = b_selected["closing"] * mult
    opening_val = b_selected["opening"] * mult
    n_years = b_selected["month_count"] / 12
    if opening_val > 0 and closing_val > 0 and n_years > 0:
        cagr = ((closing_val / opening_val) ** (1 / n_years) - 1) * 100
        cagr_str = f"CAGR {cagr:+.1f}%"
    else:
        cagr_str = None


    # ── Weighted averages by year segment (align with JS bridge chart) ──
    # Group indices by year
    year_groups = collections.OrderedDict()
    for idx in range(si, ei + 1):
        yr = mrr_periods[idx]["year"]
        year_groups.setdefault(yr, []).append(idx)

    # Build per-year bridge segments
    yearly_bridges = []
    prev_yr_ei = None
    for yi, (yr, idxs) in enumerate(year_groups.items()):
        yr_si, yr_ei = idxs[0], idxs[-1]
        if yi == 0:
            # Match bridge chart behavior: if first selected year has only one month,
            # treat it as an opening stub and exclude it from weighted KPI averages.
            if yr_si == yr_ei:
                prev_yr_ei = yr_ei
                continue
            b_year = build_bridge_range(df, mrr_periods, yr_si, yr_ei)
        else:
            bridge_from = prev_yr_ei if prev_yr_ei is not None else yr_si
            b_year = build_bridge_range(df, mrr_periods, bridge_from, yr_ei)
        yearly_bridges.append(b_year)
        prev_yr_ei = yr_ei

    # Weighted average NRR/GRR over year segments
    nrr_segs = [b for b in yearly_bridges if b.get("nrr") is not None and b.get("opening", 0) > 0]
    grr_segs = [b for b in yearly_bridges if b.get("grr") is not None and b.get("opening", 0) > 0]
    avg_nrr = (
        round(sum(b["nrr"] * b["opening"] for b in nrr_segs) / sum(b["opening"] for b in nrr_segs), 1)
        if nrr_segs else None
    )
    avg_grr = (
        round(sum(b["grr"] * b["opening"] for b in grr_segs) / sum(b["opening"] for b in grr_segs), 1)
        if grr_segs else None
    )

    # Weighted average churn over year segments
    churn_segs = [b for b in yearly_bridges if b.get("opening", 0) > 0]
    total_churn = sum(abs(b["churn"]) for b in churn_segs)
    total_opening = sum(b["opening"] for b in churn_segs)
    avg_churn_pct = (total_churn / total_opening * 100) if total_opening > 0 else None
    avg_monthly_churn_rate = (total_churn / total_opening) if total_opening > 0 else None

    # Active customers
    if col_map.get("companyName") and col_map["companyName"] in df.columns:
        total_customers = df[col_map["companyName"]].nunique()
    else:
        total_customers = len(df)
    net_cust = b_selected["cust_closing"] - b_selected["cust_opening"]

    # ARPA (Average Revenue Per Account)
    arpa = b_selected["closing"] * mult / b_selected["cust_closing"] if b_selected["cust_closing"] > 0 else None

    # ACL (Average Customer Lifetime) = 1 / monthly churn rate → months
    acl_months = 1 / avg_monthly_churn_rate if avg_monthly_churn_rate and avg_monthly_churn_rate > 0 else None

    # LTV (Customer Lifetime Value) = ARPA × ACL  (assumes 100% gross margin)
    ltv = arpa * (acl_months / 12 if show_arr else acl_months) if (arpa and acl_months) else None

    # ── KPI row ───────────────────────────────────────────
    cols = st.columns(7)
    with cols[0]:
        st.metric(
            f"Closing {lbl}",
            format_currency(closing_val, sym),
            delta=cagr_str,
        )
    with cols[1]:
        nrr_display = f"{avg_nrr}%" if avg_nrr is not None else "—"
        st.metric("Avg NRR", nrr_display)
        if t12_nrr:
            st.caption(f"Last 12M (cumulative): {t12_nrr}%")
    with cols[2]:
        grr_display = f"{avg_grr}%" if avg_grr is not None else "—"
        st.metric("Avg GRR", grr_display)
        if t12_grr:
            st.caption(f"Last 12M (cumulative): {t12_grr}%")
    with cols[3]:
        st.metric(
            "Active Customers",
            str(b_selected["cust_closing"]),
            delta=f"net {'+' if net_cust >= 0 else ''}{net_cust}" if b_selected["cust_opening"] > 0 else None,
        )
    with cols[4]:
        st.metric(
            "Avg Churn %",
            f"{avg_churn_pct:.1f}%" if avg_churn_pct is not None else "—",
        )
    with cols[5]:
        acl_display = f"{acl_months:.1f} mo" if acl_months is not None else "—"
        st.metric("ACL", acl_display)
        st.caption("1 / churn rate")
    with cols[6]:
        ltv_display = format_currency(ltv, sym) if ltv is not None else "—"
        st.metric("LTV", ltv_display)
        st.caption("ARPA × ACL (assumes 100% margin)")

    st.markdown("")  # spacer

    # ── Mini charts — 2×2 grid ────────────────────────────
    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        fig = _mini_yearly_bridge(df, mrr_periods, si, ei, sym, mult, lbl)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for yearly bridge.")
    with row1_c2:
        fig = _mini_yearly_logo_bridge(df, mrr_periods, si, ei)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for logo bridge.")

    row2_c1, row2_c2 = st.columns(2)
    with row2_c1:
        fig = _mini_acv_trend(monthly, sym, mult, lbl)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    with row2_c2:
        fig = _mini_active_customers(monthly)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
