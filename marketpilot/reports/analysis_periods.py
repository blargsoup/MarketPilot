"""
Reusable historical analysis periods.

These periods are deliberately defined in one place so the same
boundaries can later be used by the optimizer.
"""

ANALYSIS_PERIODS = {
    "FULL": {
        "start": "1993-01-01",
        "end": None,
    },

    "EARLY": {
        "start": "1993-01-01",
        "end": "2005-01-01",
    },

    "MODERN": {
        "start": "2005-01-01",
        "end": None,
    },

    "POST_GFC": {
        "start": "2010-01-01",
        "end": None,
    },
}