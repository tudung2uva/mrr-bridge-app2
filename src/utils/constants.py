# ── CONSTANTS ─────────────────────────────────────────────
"""Shared colours, benchmark thresholds, and palette for charts."""

# Chart colour palette (matches JS version)
PALETTE = [
    "#00c8f0", "#00dfa0", "#a070ff", "#ffb020", "#ff3d5a",
    "#f0d060", "#4488ff", "#00c880", "#ff8050", "#cc88ff",
    "#60d0c0", "#ff6688", "#88aaff", "#ffcc44", "#44ffcc",
]

# Bridge‐segment colours
CLR_OPENING   = "#4488ff"
CLR_NEW_LOGO  = "#00dfa0"
CLR_UPSELL    = "#00c880"
CLR_REACT     = "#ffb020"
CLR_DOWNSELL  = "#cc2244"
CLR_CHURN     = "#ff3d5a"
CLR_CLOSING   = "#00c8f0"

# Benchmark colour thresholds  ──  (good, amber) — anything below is red
BENCH = {
    "nrr":   {"good": 120, "amber": 100},
    "grr":   {"good": 90,  "amber": 80},
    "churn": {"good": 2,   "amber": 5},   # ≤ good → green, ≤ amber → amber
}

# Month abbreviations
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Hint words used to auto‐guess dimension columns during column mapping
COLUMN_HINTS = {
    "companyName":   ["company", "name", "customer", "client", "account"],
    "industry":      ["industry", "sector", "vertical"],
    "country":       ["country", "region", "geo", "market", "location"],
    "firstContract": ["first", "start", "date", "joined"],
    "productLine":   ["product", "line", "sku", "service", "package", "plan"],
}

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£"}
