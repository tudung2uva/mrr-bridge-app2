# ── SIDEBAR ────────────────────────────────────────────────
"""Sidebar with currency, MRR/ARR toggle, and dimension filters.

Mirrors JS ``buildSidebar()``, ``setCurrency()``, ``setMRRMode()``.
"""
from __future__ import annotations

import streamlit as st

from utils.constants import CURRENCY_SYMBOLS
from components.formula_panel import render_formula_panel


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

        # ── Column Mapping ─────────────────────────────────
        options = st.session_state.get("_col_map_options", [])
        meta_keys = st.session_state.get("_meta_keys", [])
        meta_labels = st.session_state.get("_meta_labels", {})
        extra_candidates = st.session_state.get("_extra_candidates", [])
        skip = "— skip —"

        if options and meta_keys:
            with st.expander("📋 Column Mapping", expanded=False):
                current_map = st.session_state.get("col_map", {})
                col_map: dict[str, str] = {}
                for mk in meta_keys:
                    current_val = current_map.get(mk, "")
                    default_idx = options.index(current_val) if current_val in options else 0
                    chosen = st.selectbox(
                        meta_labels.get(mk, mk), options, index=default_idx,
                        key=f"map_{mk}",
                    )
                    col_map[mk] = "" if chosen == skip else chosen

                extra_dim_cols: list[str] = []
                if extra_candidates:
                    current_extra = st.session_state.get("extra_dim_cols", extra_candidates[:5])
                    extra_dim_cols = st.multiselect(
                        "Additional filter dimensions",
                        extra_candidates,
                        default=[e for e in current_extra if e in extra_candidates],
                        key="extra_dims",
                    )

                st.session_state["col_map"] = col_map
                st.session_state["extra_dim_cols"] = extra_dim_cols

        # ── Formula Inspector (in sidebar) ─────────────────
        from data.engine import all_monthly_bridges
        _mrr = st.session_state.get("mrr_periods", [])
        if _mrr:
            _monthly = all_monthly_bridges(df, _mrr)
            render_formula_panel(_monthly)

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
                default=[],
                placeholder="All (no filter)",
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
            if 0 < len(f["selected"]) < len(f["vals"])
        )
        if active:
            st.info(f"{active} filter{'s' if active > 1 else ''} active")

    return filters
