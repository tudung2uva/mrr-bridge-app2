# ── DATA ENGINE ────────────────────────────────────────────
"""Core MRR Bridge computation — faithfully ported from data.js.

Public API
----------
get_mrr(row, key)             – safe numeric extraction
filtered_data(df, filters)    – apply sidebar filters
build_bridge_range(df, mrr_periods, start_idx, end_idx)
all_monthly_bridges(df, mrr_periods)
build_cohorts(df, mrr_periods, gran)
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd


# ── helpers ────────────────────────────────────────────────

def get_mrr(row: pd.Series, key: str) -> float:
    """Safe numeric extraction for a single MRR cell.

    Mirrors JS ``getMRR``: returns 0 for null / blank / dash / negative.
    """
    v = row.get(key)
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 0.0
    if isinstance(v, str):
        v = v.strip()
        if v in ("", "-"):
            return 0.0
        v = v.replace("$", "").replace(",", "").replace(" ", "")
        try:
            v = float(v)
        except ValueError:
            return 0.0
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    return v if (not math.isnan(v) and v >= 0) else 0.0


def filtered_data(
    df: pd.DataFrame,
    filters: dict[str, dict],
) -> pd.DataFrame:
    """Apply sidebar dimension filters.

    *filters* is ``{key: {"col": str, "selected": set}}``.
    Mirrors JS ``filteredData()``.
    """
    mask = pd.Series(True, index=df.index)
    for _key, f in filters.items():
        sel = f.get("selected", set())
        if not sel:
            continue
        col = f["col"]
        if col not in df.columns:
            continue
        mask &= df[col].fillna("").astype(str).str.strip().isin(sel)
    return df.loc[mask].copy()


# ── BRIDGE ─────────────────────────────────────────────────

def build_bridge_range(
    df: pd.DataFrame,
    mrr_periods: list[dict],
    start_idx: int,
    end_idx: int,
) -> dict:
    """Aggregate monthly MRR movements between *start_idx* and *end_idx*.

    Faithfully mirrors JS ``buildBridgeRange()``.

    Parameters
    ----------
    df : DataFrame
        Customer‐level data (one row per customer/contract).
    mrr_periods : list[dict]
        Sorted list of ``{"key", "year", "month", "lbl", "sk"}``.
    start_idx, end_idx : int
        Indices into *mrr_periods*.

    Returns
    -------
    dict with keys:
        start_period, end_period, month_count,
        opening, new_logo, upsell, downsell, churn, react, closing,
        grr, nrr, cmgr, quick_ratio,
        cust_opening, cust_new, cust_churn, cust_react, cust_closing.
    """
    opening = 0.0
    new_logo = 0.0
    upsell = 0.0
    downsell = 0.0
    churn = 0.0
    react = 0.0
    cust_open = 0
    cust_new = 0
    cust_churn = 0
    cust_react = 0

    # Opening = MRR at start_idx period
    open_key = mrr_periods[start_idx]["key"]
    for _, row in df.iterrows():
        m_open = get_mrr(row, open_key)
        opening += m_open
        if m_open > 0:
            cust_open += 1

    # Aggregate each monthly step from start_idx+1 to end_idx
    for i in range(start_idx + 1, end_idx + 1):
        pa_key = mrr_periods[i - 1]["key"]
        pb_key = mrr_periods[i]["key"]
        for _, row in df.iterrows():
            m_a = get_mrr(row, pa_key)
            m_b = get_mrr(row, pb_key)
            delta = m_b - m_a

            if m_a == 0 and m_b > 0:
                # New or reactivated — check history before pA
                was_ever = any(
                    get_mrr(row, mrr_periods[p]["key"]) > 0
                    for p in range(0, i - 1)
                )
                if was_ever:
                    react += m_b
                    cust_react += 1
                else:
                    new_logo += m_b
                    cust_new += 1
            elif m_a > 0 and m_b == 0:
                churn -= m_a
                cust_churn += 1
            elif delta > 0:
                upsell += delta
            elif delta < 0:
                downsell += delta

    closing = opening + new_logo + upsell + downsell + churn + react

    grr = round((opening + downsell + churn) / opening * 100, 2) if opening > 0 else None
    nrr = round((opening + upsell + downsell + churn + react) / opening * 100, 2) if opening > 0 else None

    month_count = end_idx - start_idx
    if opening > 0 and closing > 0 and month_count > 0:
        cmgr = (closing / opening) ** (1 / month_count) - 1
    else:
        cmgr = None

    qr_num = new_logo + upsell + react
    qr_den = abs(churn) + abs(downsell)
    quick_ratio = round(qr_num / qr_den, 1) if qr_den > 0 else None

    return {
        "start_period": mrr_periods[start_idx],
        "end_period":   mrr_periods[end_idx],
        "month_count":  month_count,
        "opening":      opening,
        "new_logo":     new_logo,
        "upsell":       upsell,
        "downsell":     downsell,
        "churn":        churn,
        "react":        react,
        "closing":      closing,
        "grr":          grr,
        "nrr":          nrr,
        "cmgr":         cmgr,
        "quick_ratio":  quick_ratio,
        "cust_opening": cust_open,
        "cust_new":     cust_new,
        "cust_churn":   cust_churn,
        "cust_react":   cust_react,
        "cust_closing": cust_open + cust_new - cust_churn + cust_react,
    }


def all_monthly_bridges(
    df: pd.DataFrame,
    mrr_periods: list[dict],
) -> list[dict]:
    """Build a bridge for every consecutive month pair.

    Mirrors JS ``allMonthlyBridges()``.  The first entry is the
    "base" period with zero flows.
    """
    results: list[dict] = []
    for i, p in enumerate(mrr_periods):
        if i == 0:
            opening = 0.0
            cust_open = 0
            for _, row in df.iterrows():
                m = get_mrr(row, p["key"])
                opening += m
                if m > 0:
                    cust_open += 1
            results.append({
                "start_period": p, "end_period": p, "month_count": 0,
                "opening": opening, "new_logo": 0, "upsell": 0,
                "downsell": 0, "churn": 0, "react": 0, "closing": opening,
                "grr": None, "nrr": None, "cmgr": None, "quick_ratio": None,
                "cust_opening": cust_open, "cust_new": 0, "cust_churn": 0,
                "cust_react": 0, "cust_closing": cust_open,
            })
        else:
            results.append(build_bridge_range(df, mrr_periods, i - 1, i))
    return results


# ── COHORT ANALYSIS ────────────────────────────────────────


def get_new_logo_details(
    df: pd.DataFrame,
    mrr_periods: list[dict],
    start_idx: int,
    end_idx: int,
    col_map: dict[str, str],
) -> list[dict]:
    """Return a list of new-logo customers acquired in the selected range.

    Each entry has: company, product_line, first_mrr, first_period.
    """
    name_col = col_map.get("companyName", "")
    prod_col = col_map.get("productLine", "")
    results: list[dict] = []

    for _, row in df.iterrows():
        first_pos = -1
        for pi in range(len(mrr_periods)):
            if get_mrr(row, mrr_periods[pi]["key"]) > 0:
                first_pos = pi
                break
        if first_pos < 0:
            continue
        # New logo = first appearance is within (start_idx, end_idx]
        if start_idx < first_pos <= end_idx:
            company = str(row.get(name_col, "")).strip() if name_col and name_col in row.index else f"Row {row.name}"
            product = str(row.get(prod_col, "")).strip() if prod_col and prod_col in row.index else ""
            first_mrr = get_mrr(row, mrr_periods[first_pos]["key"])
            results.append({
                "company": company,
                "product_line": product if product and product.lower() not in ("nan", "") else "—",
                "first_mrr": first_mrr,
                "first_period": mrr_periods[first_pos]["lbl"],
            })
    return results


def build_cohorts(
    df: pd.DataFrame,
    mrr_periods: list[dict],
    gran: str = "monthly",
) -> list[dict]:
    """Build cohort retention data.

    Faithfully mirrors JS ``buildCohorts()``.

    Parameters
    ----------
    gran : ``"monthly"`` or ``"yearly"``

    Returns
    -------
    list of dicts with keys:
        label, start_idx, size, init_mrr, logo_ret, grr_ret, nrr_ret
    """
    cohort_map: dict[Any, list] = {}

    for _, row in df.iterrows():
        # Find the first period where customer has MRR > 0
        start_idx = -1
        for pi, p in enumerate(mrr_periods):
            if get_mrr(row, p["key"]) > 0:
                start_idx = pi
                break
        if start_idx < 0:
            continue
        key = mrr_periods[start_idx]["year"] if gran == "yearly" else start_idx
        cohort_map.setdefault(key, []).append({"row": row, "start_idx": start_idx})

    sorted_keys = sorted(cohort_map.keys())
    cohorts: list[dict] = []

    for key in sorted_keys:
        members = cohort_map[key]
        label = str(key) if gran == "yearly" else mrr_periods[key]["lbl"]
        size = len(members)

        # initMRR = sum at each member's own actual start month
        init_mrr = sum(
            get_mrr(m["row"], mrr_periods[m["start_idx"]]["key"])
            for m in members
        )

        earliest_start = (
            min(m["start_idx"] for m in members) if gran == "yearly" else key
        )
        max_offset = len(mrr_periods) - earliest_start - 1

        logo_ret: list[float | None] = []
        grr_ret:  list[float | None] = []
        nrr_ret:  list[float | None] = []

        for offset in range(max_offset + 1):
            active_count = 0
            grr_mrr = 0.0
            total_mrr = 0.0
            valid_init_mrr = 0.0
            valid_size = 0

            for m in members:
                member_offset = offset - (m["start_idx"] - earliest_start)
                if member_offset < 0:
                    continue
                p_idx = m["start_idx"] + member_offset
                if p_idx >= len(mrr_periods):
                    continue

                init_m = get_mrr(m["row"], mrr_periods[m["start_idx"]]["key"])
                valid_init_mrr += init_m
                valid_size += 1

                # GRR: running minimum per customer
                run_min = init_m
                for o2 in range(1, member_offset + 1):
                    p2 = m["start_idx"] + o2
                    if p2 >= len(mrr_periods):
                        break
                    val = get_mrr(m["row"], mrr_periods[p2]["key"])
                    if run_min == 0:
                        break
                    run_min = min(run_min, val)
                grr_mrr += run_min

                mrr_val = get_mrr(m["row"], mrr_periods[p_idx]["key"])
                if mrr_val > 0:
                    active_count += 1
                total_mrr += mrr_val

            logo_ret.append(round(active_count / valid_size * 100, 1) if valid_size > 0 else None)
            grr_ret.append(round(grr_mrr / valid_init_mrr * 100, 1) if valid_init_mrr > 0 else None)
            nrr_ret.append(round(total_mrr / valid_init_mrr * 100, 1) if valid_init_mrr > 0 else None)

        cohorts.append({
            "label":     label,
            "start_idx": earliest_start,
            "size":      size,
            "init_mrr":  init_mrr,
            "logo_ret":  logo_ret,
            "grr_ret":   grr_ret,
            "nrr_ret":   nrr_ret,
        })

    return cohorts
