"""Shared constants for options agents."""

DTE_BUCKETS = [
    {"label": "Short-term (0-5 DTE)", "min": 0, "max": 5, "tag": "SHORT"},
    {"label": "Weekly (5-14 DTE)", "min": 5, "max": 14, "tag": "WEEKLY"},
    {"label": "Monthly (14-45 DTE)", "min": 14, "max": 45, "tag": "MONTHLY"},
    {"label": "Longer-term (45-90 DTE)", "min": 45, "max": 90, "tag": "LONGER"},
]
