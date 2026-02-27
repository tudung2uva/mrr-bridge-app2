# ── HELPERS ────────────────────────────────────────────────
"""Currency formatting and small utility functions."""
from __future__ import annotations


def format_currency(value: float | None, symbol: str = "€", short: bool = False) -> str:
    """Format *value* as a currency string.

    Parameters
    ----------
    value : numeric or None
        The amount to format.  ``None`` → ``"—"``.
    symbol : str
        Currency symbol (``€``, ``$``, ``£``).
    short : bool
        If *True*, use shorter format (no decimals for K, one decimal for M).

    Mirrors JS ``fmtC`` / ``fmtCS``.
    """
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    a = abs(value)
    if short:
        if a >= 1e6:
            return f"{sign}{symbol}{a / 1e6:.1f}M"
        if a >= 1e3:
            return f"{sign}{symbol}{a / 1e3:.1f}K"
        return f"{sign}{symbol}{a:,.2f}"
    else:
        if a >= 1e6:
            return f"{sign}{symbol}{a / 1e6:.2f}M"
        if a >= 1e3:
            return f"{sign}{symbol}{a / 1e3:.1f}K"
        return f"{sign}{symbol}{a:,.2f}"


def bench_color(metric: str, value: float | None) -> str:
    """Return a CSS‐friendly colour string for a KPI benchmark value.

    ``metric`` is one of ``nrr``, ``grr``, ``qr``, ``churn``.
    Returns ``green`` / ``orange`` / ``red``.
    """
    from .constants import BENCH

    if value is None:
        return "gray"
    t = BENCH.get(metric)
    if t is None:
        return "gray"

    if metric == "churn":
        # Lower is better
        if value <= t["good"]:
            return "green"
        if value <= t["amber"]:
            return "orange"
        return "red"
    else:
        if value >= t["good"]:
            return "green"
        if value >= t["amber"]:
            return "orange"
        return "red"


def bench_label(metric: str, value: float | None) -> str:
    """Human‐readable benchmark label for KPI cards."""
    if value is None:
        return ""
    if metric == "nrr":
        if value >= 120:
            return "▲ Best-in-class (>120%)"
        if value >= 100:
            return "▲ Above break-even"
        return "▼ Below 100% benchmark"
    if metric == "grr":
        if value >= 90:
            return "▲ Best-in-class (>90%)"
        if value >= 80:
            return "⚠ Benchmark: >90%"
        return "▼ Below benchmark"
    if metric == "churn":
        if value <= 2:
            return "▲ Low churn (<2%)"
        if value <= 5:
            return "⚠ Moderate churn"
        return "▼ High churn (>5%)"
    return ""


def period_label(year: int, month: int) -> str:
    """Return e.g. ``'Jan 2024'``."""
    from .constants import MONTH_NAMES
    return f"{MONTH_NAMES[month - 1]} {year}"


def trailing_weighted(monthly: list[dict], metric: str, n: int) -> float | None:
    """Trailing weighted average over last *n* months.

    Weighted by *opening* MRR so early small‐base months don't skew.
    Mirrors JS ``trailingWtd``.
    """
    valid = [b for b in monthly if b.get(metric) is not None and b.get("opening", 0) > 0]
    valid = valid[-n:]
    if not valid:
        return None
    ws = sum(b[metric] * b["opening"] for b in valid)
    wt = sum(b["opening"] for b in valid)
    return round(ws / wt, 1) if wt > 0 else None
