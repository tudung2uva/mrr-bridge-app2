# ── PRODUCT MIX ────────────────────────────────────────────
"""Products-per-customer distribution + product-line revenue breakdown.

Provides:
  render_product_mix(df, mrr_periods, col_map)
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.engine import get_mrr
from utils.constants import PALETTE
from utils.helpers import format_currency


def render_product_mix(df: pd.DataFrame, mrr_periods: list[dict],
                       col_map: dict[str, str]) -> None:
    """Render product-mix analytics: products per customer + revenue split."""
    prod_col = col_map.get("productLine", "")
    name_col = col_map.get("companyName", "")
    sym = st.session_state.get("currency", "€")
    mult = 12 if st.session_state.get("show_arr", False) else 1
    lbl = "ARR" if st.session_state.get("show_arr", False) else "MRR"
    ei = st.session_state.get("bridge_end", len(mrr_periods) - 1)
    last_key = mrr_periods[ei]["key"]

    if not prod_col or prod_col not in df.columns:
        st.info(
            "Map a **Product Line** column in the Column Mapping section "
            "to enable product-mix analytics."
        )
        return

    if not name_col or name_col not in df.columns:
        st.info("Map a **Company Name** column to enable product-mix analytics.")
        return

    # Only active customers (MRR > 0 in last selected period)
    active = df[df.apply(lambda r: get_mrr(r, last_key) > 0, axis=1)].copy()
    if active.empty:
        st.info("No active customers in the selected period.")
        return

    active["_mrr"] = active.apply(lambda r: get_mrr(r, last_key), axis=1)
    active["_product"] = active[prod_col].fillna("—").astype(str).str.strip()
    active["_company"] = active[name_col].fillna("Unknown").astype(str).str.strip()

    # ── Products per customer ─────────────────────────────
    st.subheader("Products per Customer")
    cust_prods = (
        active.groupby("_company")["_product"]
        .nunique()
        .reset_index()
        .rename(columns={"_product": "n_products"})
    )
    dist = cust_prods["n_products"].value_counts().sort_index()

    fig_dist = go.Figure(go.Bar(
        x=[f"{n} product{'s' if n > 1 else ''}" for n in dist.index],
        y=dist.values,
        text=dist.values,
        textposition="outside",
        textfont=dict(size=11, family="IBM Plex Mono"),
        marker_color="rgba(0,200,240,0.7)",
        marker_line_color="#00c8f0",
        marker_line_width=1,
    ))
    fig_dist.update_layout(
        title=dict(
            text=f"<b>Distribution of Products per Customer</b><br>"
                 f"<sup>{len(cust_prods)} active customers · {active['_product'].nunique()} products</sup>",
            font=dict(size=14, color="#dde3f0"),
        ),
        plot_bgcolor="#0c0e14", paper_bgcolor="#0c0e14",
        font=dict(color="#6a7a9a", family="IBM Plex Mono"),
        height=350, margin=dict(l=50, r=30, t=70, b=40),
        yaxis=dict(gridcolor="#1a2030", title="Customers"),
        xaxis=dict(title=""),
        showlegend=False,
    )
    st.plotly_chart(fig_dist, use_container_width=True)

    # Summary stats
    avg_prods = cust_prods["n_products"].mean()
    multi = (cust_prods["n_products"] > 1).sum()
    cols = st.columns(4)
    cols[0].metric("Active Customers", len(cust_prods))
    cols[1].metric("Avg Products/Customer", f"{avg_prods:.1f}")
    cols[2].metric("Multi-Product Customers", multi)
    cols[3].metric("Multi-Product %", f"{multi / len(cust_prods) * 100:.1f}%"
                   if len(cust_prods) > 0 else "—")

    st.markdown("---")

    # ── Revenue by product line ───────────────────────────
    st.subheader(f"{lbl} by Product Line")
    prod_rev = (
        active.groupby("_product")
        .agg(customers=("_company", "nunique"), total_mrr=("_mrr", "sum"))
        .reset_index()
        .sort_values("total_mrr", ascending=False)
    )
    prod_rev["total_display"] = prod_rev["total_mrr"] * mult

    c1, c2 = st.columns(2)

    with c1:
        fig_pie = go.Figure(go.Pie(
            labels=prod_rev["_product"],
            values=prod_rev["total_display"],
            hole=0.45,
            marker=dict(colors=PALETTE[:len(prod_rev)]),
            textinfo="label+percent",
            textfont=dict(size=11, family="IBM Plex Mono"),
            hovertemplate=(
                "%{label}: " + sym + "%{value:,.0f} (%{percent})<extra></extra>"
            ),
        ))
        fig_pie.update_layout(
            title=dict(text=f"<b>{lbl} Share by Product</b>",
                       font=dict(size=13, color="#dde3f0")),
            plot_bgcolor="#0c0e14", paper_bgcolor="#0c0e14",
            font=dict(color="#6a7a9a", family="IBM Plex Mono"),
            height=350, margin=dict(l=20, r=20, t=50, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        fig_bar = go.Figure(go.Bar(
            x=prod_rev["_product"],
            y=prod_rev["total_display"],
            text=[format_currency(v, sym, short=True) for v in prod_rev["total_display"]],
            textposition="outside",
            textfont=dict(size=10, family="IBM Plex Mono"),
            marker_color=[f"rgba({int(c.lstrip('#')[0:2],16)},{int(c.lstrip('#')[2:4],16)},{int(c.lstrip('#')[4:6],16)},0.73)"
                          for c in PALETTE[:len(prod_rev)]],
            marker_line_color=PALETTE[:len(prod_rev)],
            marker_line_width=1,
        ))
        fig_bar.update_layout(
            title=dict(text=f"<b>{lbl} by Product</b>",
                       font=dict(size=13, color="#dde3f0")),
            plot_bgcolor="#0c0e14", paper_bgcolor="#0c0e14",
            font=dict(color="#6a7a9a", family="IBM Plex Mono"),
            height=350, margin=dict(l=50, r=30, t=50, b=40),
            yaxis=dict(gridcolor="#1a2030"),
            showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Detail table
    tbl = prod_rev.copy()
    tbl[f"{lbl}"] = tbl["total_display"].apply(
        lambda v: format_currency(v, sym, short=False)
    )
    tbl["Share %"] = (tbl["total_display"] / tbl["total_display"].sum() * 100).apply(
        lambda v: f"{v:.1f}%"
    )
    display = tbl.rename(columns={"_product": "Product Line", "customers": "Customers"})
    st.dataframe(
        display[["Product Line", "Customers", f"{lbl}", "Share %"]],
        use_container_width=True,
        hide_index=True,
    )
