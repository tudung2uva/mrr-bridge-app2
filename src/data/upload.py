# ── UPLOAD & COLUMN MAPPING ────────────────────────────────
"""File upload, MRR column detection, and column‐mapping UI.

Faithfully mirrors upload.js:
- isMRR / parsePeriod  → auto-detect MRR period columns
- guessCol             → auto-guess meta dimension columns
- detectExtraDims      → find additional categorical columns
- Column-mapping form  → Streamlit expander instead of modal
"""
from __future__ import annotations

import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st

from utils.constants import COLUMN_HINTS, MONTH_NAMES


# ── MRR column detection ──────────────────────────────────

def is_mrr(col: str) -> bool:
    """Return True if *col* looks like an MRR period column.

    Mirrors JS ``isMRR``: must contain a 4‑digit year **and** one of
    ``mrr / arr / revenue`` (case‑insensitive).
    """
    return bool(re.search(r"\d{4}", col) and re.search(r"(?i)(mrr|arr|revenue)", col))


def parse_period(col: str) -> dict | None:
    """Extract year/month from a column name.

    Supports formats like ``MRR_2023_01``, ``01_2024_MRR``,
    ``MRR_Jan_2024``, etc.  Mirrors JS ``parsePeriod``.
    """
    # Format: YYYY-MM or YYYY_MM
    m = re.search(r"(\d{4})[-_\s](\d{1,2})", col)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return {"key": col, "year": y, "month": mo,
                    "lbl": f"{MONTH_NAMES[mo - 1]} {y}", "sk": y * 100 + mo}

    # Format: MM-YYYY or MM_YYYY
    m = re.search(r"(\d{1,2})[-_\s](\d{4})", col)
    if m:
        mo, y = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return {"key": col, "year": y, "month": mo,
                    "lbl": f"{MONTH_NAMES[mo - 1]} {y}", "sk": y * 100 + mo}

    # Named month: Jan, Feb, …
    mn = ["jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec"]
    lo = col.lower()
    for i, name in enumerate(mn):
        if name in lo:
            yr_match = re.search(r"\d{4}", col)
            if yr_match:
                y = int(yr_match.group(0))
                return {"key": col, "year": y, "month": i + 1,
                        "lbl": f"{MONTH_NAMES[i]} {y}", "sk": y * 100 + (i + 1)}
    return None


def _guess_col(headers: list[str], hints: list[str]) -> str:
    """Find the first header that contains any of *hints* (case‑insensitive)."""
    for h in hints:
        for c in headers:
            if h.lower() in c.lower():
                return c
    return ""


def detect_extra_dims(df: pd.DataFrame, headers: list[str],
                      mrr_keys: set[str], mapped_cols: set[str]) -> list[str]:
    """Find additional categorical columns suitable for sidebar filters.

    Mirrors JS ``detectExtraDims``.
    """
    candidates: list[str] = []
    n = len(df)
    for h in headers:
        if h in mrr_keys or h in mapped_cols:
            continue
        vals = df[h].dropna()
        vals = vals[vals.astype(str).str.strip() != ""]
        if len(vals) < n * 0.3:
            continue
        uniq = vals.astype(str).str.strip().nunique()
        if uniq < 2 or uniq > 60:
            continue
        # Skip mostly‑numeric columns
        num_count = pd.to_numeric(vals, errors="coerce").notna().sum()
        if num_count / len(vals) > 0.7:
            continue
        candidates.append(h)
    return candidates


# ── Public upload UI ───────────────────────────────────────

def render_upload() -> bool:
    """Render file uploader + column mapping form.

    Stores results in ``st.session_state``:
        raw_data, headers, mrr_periods, col_map,
        extra_dim_cols, import_datetime, import_filename

    Returns ``True`` when data is ready.
    """
    uploaded = st.file_uploader(
        "Upload MRR data (CSV or Excel)",
        type=["csv", "xlsx", "xls"],
        key="mrr_file_upload",
    )

    if uploaded is None:
        if "raw_data" in st.session_state:
            return True  # already loaded
        return False

    # Detect if a new file was uploaded (different name or size)
    fname = uploaded.name
    if (st.session_state.get("import_filename") == fname
            and "raw_data" in st.session_state):
        return True  # same file, already processed

    # ── Load file ──────────────────────────────────────────
    ext = fname.rsplit(".", 1)[-1].lower()
    try:
        if ext == "csv":
            content = uploaded.read().decode("utf-8-sig", errors="replace")
            # auto-detect delimiter
            first_line = content.split("\n", 1)[0]
            delim = ";" if first_line.count(";") > first_line.count(",") else ","
            df = pd.read_csv(io.StringIO(content), sep=delim, skipinitialspace=True)
        else:
            # Excel — read first sheet by default
            xls = pd.ExcelFile(uploaded)
            sheet = xls.sheet_names[0]
            if len(xls.sheet_names) > 1:
                sheet = st.selectbox("Select sheet", xls.sheet_names, key="sheet_sel")
            df = pd.read_excel(xls, sheet_name=sheet)
    except Exception as e:
        st.error(f"Failed to load file: {e}")
        return False

    if df.empty:
        st.warning("The uploaded file is empty.")
        return False

    headers = list(df.columns)

    # ── Detect MRR columns ─────────────────────────────────
    mrr_periods = sorted(
        filter(None, (parse_period(c) for c in headers if is_mrr(c))),
        key=lambda p: p["sk"],
    )

    if not mrr_periods:
        st.error(
            "⚠ No MRR columns detected.  "
            "Expected column names containing a year and 'MRR', 'ARR', or 'Revenue' "
            "(e.g. `MRR_2023_01`)."
        )
        return False

    st.success(
        f"✓ **{len(mrr_periods)} MRR columns** detected · "
        f"{mrr_periods[0]['lbl']} → {mrr_periods[-1]['lbl']}"
    )

    # ── Column mapping — auto-detect defaults, store for sidebar UI ──
    mrr_keys = {p["key"] for p in mrr_periods}
    meta_keys = list(COLUMN_HINTS.keys())
    meta_labels = {"companyName": "Company Name", "industry": "Industry",
                   "country": "Country", "firstContract": "First Contract Date",
                   "productLine": "Product Line"}
    skip = "— skip —"
    options = [skip] + headers

    # Auto-guess defaults (only on first load)
    col_map: dict[str, str] = {}
    for mk in meta_keys:
        default = _guess_col(headers, COLUMN_HINTS[mk])
        col_map[mk] = default if default else ""

    # Extra dimension candidates
    mapped_cols = {v for v in col_map.values() if v}
    extra_candidates = detect_extra_dims(df, headers, mrr_keys, mapped_cols)
    extra_dim_cols: list[str] = extra_candidates[:5] if extra_candidates else []

    # ── Store in session state ─────────────────────────────
    st.session_state["raw_data"]         = df
    st.session_state["headers"]          = headers
    st.session_state["mrr_periods"]      = mrr_periods
    st.session_state["col_map"]          = col_map
    st.session_state["extra_dim_cols"]   = extra_dim_cols
    st.session_state["_col_map_options"] = options
    st.session_state["_meta_keys"]       = meta_keys
    st.session_state["_meta_labels"]     = meta_labels
    st.session_state["_extra_candidates"]= extra_candidates
    st.session_state["import_datetime"]  = datetime.now()
    st.session_state["import_filename"]  = fname
    st.session_state["bridge_start"]     = max(0, len(mrr_periods) - 13)
    st.session_state["bridge_end"]       = len(mrr_periods) - 1

    return True
