# ── SIDEBAR ────────────────────────────────────────────────
"""Sidebar with currency, MRR/ARR toggle, and dimension filters.

Mirrors JS ``buildSidebar()``, ``setCurrency()``, ``setMRRMode()``.
"""
from __future__ import annotations

import streamlit as st

from utils.constants import CURRENCY_SYMBOLS


def render_sidebar() -> dict[str, dict]:
    """Draw sidebar controls and return current filters dict.

    Reads ``raw_data``, ``col_map``, ``extra_dim_cols`` from session state.
    Writes ``currency``, ``show_arr``, ``cohort_gran`` to session state.
    Returns filters dict ``{key: {col, vals, selected}}``.
    """
    df = st.session_state["raw_data"]
    col_map = st.session_state.get("col_map", {})
    extra_dim_cols = st.session_state.get("extra_dim_cols", [])

    with st.sidebar:
        st.markdown("### ⚙️ Settings")

        # Currency
        cur_code = st.selectbox(
            "Currency",
            list(CURRENCY_SYMBOLS.keys()),
            index=0,
            key="cur_sel",
        )
        st.session_state["currency"] = CURRENCY_SYMBOLS[cur_code]

        # MRR / ARR toggle
        mode = st.radio(
            "Display mode",
            ["MRR", "ARR"],
            horizontal=True,
            key="mode_sel",
        )
        st.session_state["show_arr"] = mode == "ARR"

        # Cohort granularity
        gran = st.radio(
            "Cohort granularity",
            ["Monthly", "Yearly"],
            horizontal=True,
            key="cohort_gran_sel",
        )
        st.session_state["cohort_gran"] = gran.lower()

        st.markdown("---")
        st.markdown("### 🔍 Filters")

        # Build dimension list
        all_dims: list[dict] = []
        if col_map.get("industry"):
            all_dims.append({"key": "industry", "col": col_map["industry"]})
        if col_map.get("country"):
            all_dims.append({"key": "country", "col": col_map["country"]})
        for col in extra_dim_cols:
            all_dims.append({"key": col, "col": col})

        filters: dict[str, dict] = {}
        for dim in all_dims:
            col = dim["col"]
            if col not in df.columns:
                continue
            vals = sorted(
                df[col].fillna("").astype(str).str.strip()
                .loc[lambda s: s != ""].unique().tolist()
            )
            if not vals:
                continue
            selected = st.multiselect(
                col,
                vals,
                default=vals,
                key=f"filter_{dim['key']}",
            )
            filters[dim["key"]] = {
                "col": col,
                "vals": vals,
                "selected": set(selected),
            }

        # Active filter count badge
        active = sum(
            1 for f in filters.values()
            if len(f["selected"]) < len(f["vals"])
        )
        if active:
            st.info(f"{active} filter{'s' if active > 1 else ''} active")

    return filters
