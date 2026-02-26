# ── NEW LOGOS DRILL-DOWN ───────────────────────────────────
"""New-logo detail table + product-line composition for new customers.

Provides:
  render_new_logos(df, mrr_periods, col_map)
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.engine import get_new_logo_details
from utils.constants import PALETTE
from utils.helpers import format_currency


def render_new_logos(df: pd.DataFrame, mrr_periods: list[dict],
                    col_map: dict[str, str]) -> None:
    """Render new-logo drill-down: table + product composition chart."""
    si = st.session_state.get("bridge_start", 0)
    ei = st.session_state.get("bridge_end", len(mrr_periods) - 1)
    sym = st.session_state.get("currency", "€")
    mult = 12 if st.session_state.get("show_arr", False) else 1
    lbl = "ARR" if st.session_state.get("show_arr", False) else "MRR"

    logos = get_new_logo_details(df, mrr_periods, si, ei, col_map)

    if not logos:
        st.info("No new logos in the selected period.")
        return

    st.markdown(
        f"**{len(logos)} new customer{'s' if len(logos) != 1 else ''}** "
        f"acquired {mrr_periods[si]['lbl']} → {mrr_periods[ei]['lbl']}"
    )

    # ── Detail table ──────────────────────────────────────
    tbl = pd.DataFrame(logos)
    tbl[f"First {lbl}"] = tbl["first_mrr"].apply(
        lambda v: format_currency(v * mult, sym, short=False)
    )
    display_cols = {"company": "Company", "product_line": "Product Line",
                    f"First {lbl}": f"First {lbl}", "first_period": "First Period"}
    tbl_display = tbl.rename(columns=display_cols)[list(display_cols.values())]
    tbl_display = tbl_display.sort_values(f"First {lbl}", ascending=False,
                                           key=lambda s: tbl["first_mrr"] * mult)
    st.dataframe(tbl_display, use_container_width=True, hide_index=True)

    # ── Product-line composition ──────────────────────────
    prod_col = col_map.get("productLine", "")
    has_products = prod_col and any(l["product_line"] != "—" for l in logos)

    if has_products:
        st.subheader("New Customers by Product Line")
        prod_df = pd.DataFrame(logos)
        agg = prod_df.groupby("product_line").agg(
            count=("company", "count"),
            total_mrr=("first_mrr", "sum"),
        ).reset_index().sort_values("total_mrr", ascending=False)

        c1, c2 = st.columns(2)

        # Count pie
        with c1:
            fig_count = go.Figure(go.Pie(
                labels=agg["product_line"],
                values=agg["count"],
                hole=0.45,
                marker=dict(colors=PALETTE[:len(agg)]),
                textinfo="label+percent",
                textfont=dict(size=11, family="IBM Plex Mono"),
                hovertemplate="%{label}: %{value} customers (%{percent})<extra></extra>",
            ))
            fig_count.update_layout(
                title=dict(text="<b>By Customer Count</b>",
                           font=dict(size=13, color="#dde3f0")),
                plot_bgcolor="#0c0e14", paper_bgcolor="#0c0e14",
                font=dict(color="#6a7a9a", family="IBM Plex Mono"),
                height=350, margin=dict(l=20, r=20, t=50, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig_count, use_container_width=True)

        # MRR pie
        with c2:
            fig_mrr = go.Figure(go.Pie(
                labels=agg["product_line"],
                values=agg["total_mrr"] * mult,
                hole=0.45,
                marker=dict(colors=PALETTE[:len(agg)]),
                textinfo="label+percent",
                textfont=dict(size=11, family="IBM Plex Mono"),
                hovertemplate=(
                    "%{label}: " + sym + "%{value:,.0f} (%{percent})<extra></extra>"
                ),
            ))
            fig_mrr.update_layout(
                title=dict(text=f"<b>By {lbl} Volume</b>",
                           font=dict(size=13, color="#dde3f0")),
                plot_bgcolor="#0c0e14", paper_bgcolor="#0c0e14",
                font=dict(color="#6a7a9a", family="IBM Plex Mono"),
                height=350, margin=dict(l=20, r=20, t=50, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig_mrr, use_container_width=True)

    # ── Summary KPIs ──────────────────────────────────────
    total_mrr = sum(l["first_mrr"] for l in logos) * mult
    avg_mrr = total_mrr / len(logos) if logos else 0
    cols = st.columns(3)
    cols[0].metric("New Logos", len(logos))
    cols[1].metric(f"Total New {lbl}", format_currency(total_mrr, sym, short=True))
    cols[2].metric(f"Avg New {lbl}", format_currency(avg_mrr, sym, short=True))
