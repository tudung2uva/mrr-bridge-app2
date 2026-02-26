# ── BRIDGE CHARTS ──────────────────────────────────────────
"""MRR Bridge waterfall + Logo Count Bridge waterfall.

Mirrors JS ``drawBridgeChart`` and ``drawLogosChart``.
Uses Plotly ``go.Waterfall`` for proper stacking.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from data.engine import build_bridge_range
from utils.constants import (CLR_OPENING, CLR_NEW_LOGO, CLR_UPSELL,
                              CLR_REACT, CLR_DOWNSELL, CLR_CHURN, CLR_CLOSING)
from utils.helpers import format_currency


def _wf_bars(values: list[float], measures: list[str]):
    """Compute base/top pairs for a manual waterfall using go.Bar.

    Mirrors JS ``wfBars``: running sum gives the bar base;
    'absolute'/'total' bars start from 0.
    """
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


def _waterfall_chart(
    labels: list[str],
    values: list[float],
    measures: list[str],
    colors: list[str],
    title: str,
    subtitle: str,
    fmt_fn=None,
    height: int = 380,
) -> go.Figure:
    """Generic waterfall built with go.Bar for per-bar colour control.

    Plotly's go.Waterfall does not support per-bar marker colours,
    so we emulate the waterfall manually (same approach as the JS
    ``wfBars`` helper).
    """
    bases, heights = _wf_bars(values, measures)

    text_labels = [fmt_fn(v) if fmt_fn else str(round(v)) for v in values]

    def _hex_to_rgba(hex_color: str, alpha: float = 0.73) -> str:
        """Convert '#RRGGBB' to 'rgba(r,g,b,a)'."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    fig = go.Figure(go.Bar(
        x=labels,
        y=heights,
        base=bases,
        text=text_labels,
        textposition="outside",
        textfont=dict(size=10, family="IBM Plex Mono"),
        marker_color=[_hex_to_rgba(c) for c in colors],
        marker_line_color=colors,
        marker_line_width=1,
        hovertemplate="%{x}: %{text}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"<b>{title}</b><br><sup>{subtitle}</sup>",
                   font=dict(size=14, color="#dde3f0")),
        plot_bgcolor="#0c0e14",
        paper_bgcolor="#0c0e14",
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=height,
        margin=dict(l=50, r=30, t=70, b=40),
        yaxis=dict(gridcolor="#1a2030", tickfont=dict(size=10)),
        xaxis=dict(tickfont=dict(size=10)),
        showlegend=False,
        bargap=0.3,
    )
    return fig


# ── Period selector helpers (shared by bridge + logo panes) ─

def render_period_selector(prefix: str = "") -> tuple[int, int]:
    """Render FROM/TO selectors + shortcut buttons. Return (start, end).

    This is a *public* function — called from ``app.py`` so the selector
    appears above the tabs (visible on every tab, not just MRR Bridge).
    """
    mrr_periods = st.session_state["mrr_periods"]
    n = len(mrr_periods)
    opts = {p["lbl"]: i for i, p in enumerate(mrr_periods)}
    labels = list(opts.keys())

    c1, c2, c3 = st.columns([2, 2, 6])
    start_lbl = c1.selectbox(
        "FROM", labels,
        index=st.session_state.get("bridge_start", 0),
        key=f"{prefix}sel_start",
    )
    end_lbl = c2.selectbox(
        "TO", labels,
        index=st.session_state.get("bridge_end", n - 1),
        key=f"{prefix}sel_end",
    )
    si, ei = opts[start_lbl], opts[end_lbl]
    if ei <= si:
        ei = min(si + 1, n - 1)

    # Shortcut buttons
    with c3:
        st.write("")  # spacer
        cols = st.columns(6)
        shortcuts = {
            "Last 1M": max(0, n - 2),
            "Last 3M": max(0, n - 4),
            "Last 6M": max(0, n - 7),
            "Last 12M": max(0, n - 13),
            "YTD": None,
            "All": 0,
        }
        for idx, (lbl, start_val) in enumerate(shortcuts.items()):
            if cols[idx].button(lbl, key=f"{prefix}sc_{lbl}", use_container_width=True):
                if lbl == "YTD":
                    last_yr = mrr_periods[n - 1]["year"]
                    jan_idx = next(
                        (i for i, p in enumerate(mrr_periods)
                         if p["year"] == last_yr and p["month"] == 1),
                        max(0, n - 13),
                    )
                    si = jan_idx
                elif lbl == "All":
                    si = 0
                else:
                    si = start_val  # type: ignore[assignment]
                ei = n - 1
                # Sync selectbox widget keys so they reflect the new range
                st.session_state["bridge_start"] = si
                st.session_state["bridge_end"] = ei
                for k in [f"{prefix}sel_start", f"{prefix}sel_end"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

    st.session_state["bridge_start"] = si
    st.session_state["bridge_end"] = ei
    return si, ei


# ── Public render functions ────────────────────────────────

def render_mrr_bridge(df, mrr_periods) -> None:
    """Render MRR Bridge waterfall chart with monthly/yearly toggle."""
    si = st.session_state.get("bridge_start", 0)
    ei = st.session_state.get("bridge_end", len(mrr_periods) - 1)

    view_mode = st.radio("View", ["Monthly", "Yearly"], horizontal=True,
                         key="bridge_view_mode")

    if view_mode == "Yearly":
        _render_yearly_bridge(df, mrr_periods, si, ei)
        return

    b = build_bridge_range(df, mrr_periods, si, ei)
    sym = st.session_state.get("currency", "€")
    mult = 12 if st.session_state.get("show_arr", False) else 1
    lbl = "ARR" if st.session_state.get("show_arr", False) else "MRR"

    labels   = ["Opening", "New Logo", "Upsell", "Reactivation", "Downsell", "Churn", "Closing"]
    raw_vals = [b["opening"], b["new_logo"], b["upsell"], b["react"],
                b["downsell"], b["churn"], b["closing"]]
    values   = [v * mult for v in raw_vals]
    measures = ["absolute", "relative", "relative", "relative",
                "relative", "relative", "total"]
    colors   = [CLR_OPENING, CLR_NEW_LOGO, CLR_UPSELL, CLR_REACT,
                CLR_DOWNSELL, CLR_CHURN, CLR_CLOSING]

    fig = _waterfall_chart(
        labels, values, measures, colors,
        f"{lbl} Bridge",
        f"Aggregated monthly movements · {mrr_periods[si]['lbl']} → {mrr_periods[ei]['lbl']}",
        fmt_fn=lambda v: format_currency(v, sym, short=True),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Percentage row
    if b["opening"] > 0:
        pcts = {
            "New Logo": b["new_logo"] / b["opening"] * 100,
            "Upsell":   b["upsell"]   / b["opening"] * 100,
            "React":    b["react"]    / b["opening"] * 100,
            "Downsell": b["downsell"] / b["opening"] * 100,
            "Churn":    b["churn"]    / b["opening"] * 100,
        }
        cols = st.columns(len(pcts))
        for i, (k, v) in enumerate(pcts.items()):
            cols[i].metric(k, f"{v:+.1f}%")


def _render_yearly_bridge(df, mrr_periods, si, ei) -> None:
    """Continuous waterfall bridge aggregated by calendar year.

    Like the monthly waterfall: movement bars stack on the running sum,
    opening/closing bars start from 0 (x-axis).  Movement bars show
    %-of-opening text; opening/closing bars show currency values.
    KPI summary (CMGR, NRR, GRR, QR) appears above the chart.
    """
    import collections

    sym = st.session_state.get("currency", "€")
    mult = 12 if st.session_state.get("show_arr", False) else 1
    lbl = "ARR" if st.session_state.get("show_arr", False) else "MRR"

    # ── group selected period indices by year ──────────────
    year_groups: dict[int, list[int]] = collections.OrderedDict()
    for idx in range(si, ei + 1):
        yr = mrr_periods[idx]["year"]
        year_groups.setdefault(yr, []).append(idx)

    all_labels: list[str] = []
    all_values: list[float] = []
    all_measures: list[str] = []
    all_colors: list[str] = []
    all_texts: list[str] = []

    prev_yr_ei: int | None = None

    for yi, (yr, idxs) in enumerate(year_groups.items()):
        yr_si = idxs[0]
        yr_ei = idxs[-1]

        if yi == 0:
            # First year
            if yr_si == yr_ei:
                # Only one month — just show opening, skip movements
                b = build_bridge_range(df, mrr_periods, yr_si, yr_si)
                opening = b["opening"] * mult
                all_labels.append(mrr_periods[yr_si]["lbl"])
                all_values.append(opening)
                all_measures.append("absolute")
                all_colors.append(CLR_OPENING)
                all_texts.append(format_currency(opening, sym, short=True))
                prev_yr_ei = yr_ei
                continue
            b = build_bridge_range(df, mrr_periods, yr_si, yr_ei)
            opening = b["opening"] * mult
            # Opening bar
            all_labels.append(mrr_periods[yr_si]["lbl"])
            all_values.append(opening)
            all_measures.append("absolute")
            all_colors.append(CLR_OPENING)
            all_texts.append(format_currency(opening, sym, short=True))
        else:
            # Subsequent years: bridge from previous year-end
            bridge_from = prev_yr_ei if prev_yr_ei is not None else yr_si
            b = build_bridge_range(df, mrr_periods, bridge_from, yr_ei)
            opening = b["opening"] * mult

        # Movement bars (skip zeros)
        movement_defs = [
            ("New Logo", b["new_logo"] * mult, CLR_NEW_LOGO),
            ("Upsell",   b["upsell"] * mult,   CLR_UPSELL),
            ("React",    b["react"] * mult,     CLR_REACT),
            ("Downsell", b["downsell"] * mult,  CLR_DOWNSELL),
            ("Churn",    b["churn"] * mult,     CLR_CHURN),
        ]
        for name, val, color in movement_defs:
            if abs(val) < 0.01:
                continue
            all_labels.append(name)
            all_values.append(val)
            all_measures.append("relative")
            all_colors.append(color)
            pct = val / opening * 100 if opening != 0 else 0
            all_texts.append(f"{pct:+.1f}%")

        # Closing / year-end bar
        closing = b["closing"] * mult
        is_last = (yi == len(year_groups) - 1)
        all_labels.append(mrr_periods[yr_ei]["lbl"])
        all_values.append(closing)
        all_measures.append("total")
        all_colors.append(CLR_CLOSING if is_last else CLR_OPENING)
        all_texts.append(format_currency(closing, sym, short=True))

        prev_yr_ei = yr_ei

    if not all_labels:
        st.info("Not enough data for a yearly view.")
        return

    # ── summary KPIs above chart ──────────────────────────
    b_total = build_bridge_range(df, mrr_periods, si, ei)
    kpi_cols = st.columns(4)
    cmgr_str = (
        f"{'+' if b_total['cmgr'] >= 0 else ''}{b_total['cmgr'] * 100:.2f}%/mo"
        if b_total.get("cmgr") is not None else "—"
    )
    kpi_cols[0].metric("CMGR", cmgr_str)
    kpi_cols[1].metric("Avg NRR", f"{b_total['nrr']:.1f}%" if b_total.get("nrr") else "—")
    kpi_cols[2].metric("Avg GRR", f"{b_total['grr']:.1f}%" if b_total.get("grr") else "—")
    kpi_cols[3].metric("Quick Ratio", f"{b_total['quick_ratio']}x" if b_total.get("quick_ratio") else "—")

    # ── build waterfall ───────────────────────────────────
    bases, heights = _wf_bars(all_values, all_measures)

    def _hex_to_rgba(hex_color: str, alpha: float = 0.73) -> str:
        h = hex_color.lstrip("#")
        r, g, b_c = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b_c},{alpha})"

    fig = go.Figure(go.Bar(
        x=list(range(len(all_labels))),
        y=heights,
        base=bases,
        text=all_texts,
        textposition="outside",
        textfont=dict(size=10, family="IBM Plex Mono"),
        marker_color=[_hex_to_rgba(c) for c in all_colors],
        marker_line_color=all_colors,
        marker_line_width=1,
        hovertemplate="%{customdata}<extra></extra>",
        customdata=[f"{l}: {t}" for l, t in zip(all_labels, all_texts)],
    ))

    fig.update_layout(
        title=dict(
            text=f"<b>{lbl} Bridge – Yearly</b><br>"
                 f"<sup>{mrr_periods[si]['lbl']} → {mrr_periods[ei]['lbl']}</sup>",
            font=dict(size=14, color="#dde3f0"),
        ),
        plot_bgcolor="#0c0e14",
        paper_bgcolor="#0c0e14",
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=440,
        margin=dict(l=50, r=30, t=70, b=50),
        yaxis=dict(gridcolor="#1a2030", tickfont=dict(size=10)),
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(len(all_labels))),
            ticktext=all_labels,
            tickfont=dict(size=10),
        ),
        showlegend=False,
        bargap=0.3,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_logo_bridge(df, mrr_periods) -> None:
    """Render Logo Count Bridge waterfall chart with monthly/yearly toggle."""
    si = st.session_state.get("bridge_start", 0)
    ei = st.session_state.get("bridge_end", len(mrr_periods) - 1)

    view_mode = st.radio("View", ["Monthly", "Yearly"], horizontal=True,
                         key="logo_bridge_view_mode")

    if view_mode == "Yearly":
        _render_yearly_logo_bridge(df, mrr_periods, si, ei)
        return

    b = build_bridge_range(df, mrr_periods, si, ei)

    labels   = ["Opening #", "New Logos", "Reactivations", "Churned", "Closing #"]
    values   = [b["cust_opening"], b["cust_new"], b["cust_react"],
                -b["cust_churn"], b["cust_closing"]]
    measures = ["absolute", "relative", "relative", "relative", "total"]
    colors   = [CLR_OPENING, CLR_NEW_LOGO, CLR_REACT, CLR_CHURN, CLR_CLOSING]

    fig = _waterfall_chart(
        labels, values, measures, colors,
        "Logo Count Bridge",
        f"Customer movements · {mrr_periods[si]['lbl']} → {mrr_periods[ei]['lbl']}",
        fmt_fn=lambda v: str(round(v)),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    if b["cust_opening"] > 0:
        cols = st.columns(5)
        cols[0].metric("Opening #", b["cust_opening"])
        cols[1].metric("New Logos", f"+{b['cust_new']}",
                       f"+{b['cust_new'] / b['cust_opening'] * 100:.1f}%")
        cols[2].metric("Reactivations", f"+{b['cust_react']}",
                       f"+{b['cust_react'] / b['cust_opening'] * 100:.1f}%")
        cols[3].metric("Churned", f"-{b['cust_churn']}",
                       f"-{b['cust_churn'] / b['cust_opening'] * 100:.1f}%")
        net = b["cust_closing"] - b["cust_opening"]
        cols[4].metric("Closing #", b["cust_closing"],
                       f"net {'+' if net >= 0 else ''}{net}")


def _render_yearly_logo_bridge(df, mrr_periods, si, ei) -> None:
    """Continuous waterfall for logo counts aggregated by calendar year."""
    import collections

    year_groups: dict[int, list[int]] = collections.OrderedDict()
    for idx in range(si, ei + 1):
        yr = mrr_periods[idx]["year"]
        year_groups.setdefault(yr, []).append(idx)

    all_labels: list[str] = []
    all_values: list[float] = []
    all_measures: list[str] = []
    all_colors: list[str] = []
    all_texts: list[str] = []

    prev_yr_ei: int | None = None

    for yi, (yr, idxs) in enumerate(year_groups.items()):
        yr_si = idxs[0]
        yr_ei = idxs[-1]

        if yi == 0:
            if yr_si == yr_ei:
                b = build_bridge_range(df, mrr_periods, yr_si, yr_si)
                all_labels.append(mrr_periods[yr_si]["lbl"])
                all_values.append(b["cust_opening"])
                all_measures.append("absolute")
                all_colors.append(CLR_OPENING)
                all_texts.append(str(b["cust_opening"]))
                prev_yr_ei = yr_ei
                continue
            b = build_bridge_range(df, mrr_periods, yr_si, yr_ei)
            all_labels.append(mrr_periods[yr_si]["lbl"])
            all_values.append(b["cust_opening"])
            all_measures.append("absolute")
            all_colors.append(CLR_OPENING)
            all_texts.append(str(b["cust_opening"]))
        else:
            bridge_from = prev_yr_ei if prev_yr_ei is not None else yr_si
            b = build_bridge_range(df, mrr_periods, bridge_from, yr_ei)

        opening = b["cust_opening"]
        movement_defs = [
            ("New Logos",      b["cust_new"],    CLR_NEW_LOGO),
            ("Reactivations",  b["cust_react"],  CLR_REACT),
            ("Churned",       -b["cust_churn"],  CLR_CHURN),
        ]
        for name, val, color in movement_defs:
            if val == 0:
                continue
            all_labels.append(name)
            all_values.append(val)
            all_measures.append("relative")
            all_colors.append(color)
            pct = val / opening * 100 if opening != 0 else 0
            all_texts.append(f"{val:+d} ({pct:+.1f}%)" if isinstance(val, int) else f"{val:+.0f}")

        closing = b["cust_closing"]
        is_last = (yi == len(year_groups) - 1)
        all_labels.append(mrr_periods[yr_ei]["lbl"])
        all_values.append(closing)
        all_measures.append("total")
        all_colors.append(CLR_CLOSING if is_last else CLR_OPENING)
        all_texts.append(str(closing))

        prev_yr_ei = yr_ei

    if not all_labels:
        st.info("Not enough data for a yearly view.")
        return

    bases, heights = _wf_bars(all_values, all_measures)

    def _hex_to_rgba(hex_color: str, alpha: float = 0.73) -> str:
        h = hex_color.lstrip("#")
        r, g, b_c = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b_c},{alpha})"

    fig = go.Figure(go.Bar(
        x=list(range(len(all_labels))),
        y=heights,
        base=bases,
        text=all_texts,
        textposition="outside",
        textfont=dict(size=10, family="IBM Plex Mono"),
        marker_color=[_hex_to_rgba(c) for c in all_colors],
        marker_line_color=all_colors,
        marker_line_width=1,
        hovertemplate="%{customdata}<extra></extra>",
        customdata=[f"{l}: {t}" for l, t in zip(all_labels, all_texts)],
    ))

    fig.update_layout(
        title=dict(
            text="<b>Logo Count Bridge – Yearly</b><br>"
                 f"<sup>{mrr_periods[si]['lbl']} → {mrr_periods[ei]['lbl']}</sup>",
            font=dict(size=14, color="#dde3f0"),
        ),
        plot_bgcolor="#0c0e14",
        paper_bgcolor="#0c0e14",
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=400,
        margin=dict(l=50, r=30, t=70, b=50),
        yaxis=dict(gridcolor="#1a2030", tickfont=dict(size=10)),
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(len(all_labels))),
            ticktext=all_labels,
            tickfont=dict(size=10),
        ),
        showlegend=False,
        bargap=0.3,
    )
    st.plotly_chart(fig, use_container_width=True)
