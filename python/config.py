"""Shared paths and constants for the Twin Cities Airbnb project.

Every script imports from here so there is ONE place that knows where the raw
data lives and where outputs go. This is a real-world habit: never hard-code a
path in five different scripts.
"""
from pathlib import Path

# --- Raw data (read-only; never write here, never open these in Excel) ---
# Portable default: a `Datasets/` folder next to the project (download the files
# from the links in README.md). Override by setting the AIRBNB_DATA env var.
import os
_DEFAULT = Path(__file__).resolve().parent.parent / "Datasets"
DATA = Path(os.environ.get("AIRBNB_DATA", _DEFAULT))


def _listings_path():
    """Accept listings as .csv OR .xlsx (the Inside Airbnb download is .csv;
    an Excel re-save is .xlsx). Prefer whichever exists."""
    for name in ("listings.csv", "listings.xlsx"):
        if (DATA / name).exists():
            return DATA / name
    return DATA / "listings.csv"   # sensible default for error messages


LISTINGS      = _listings_path()
LISTINGS_XLSX = LISTINGS                        # back-compat alias
CALENDAR_CSV  = DATA / "calendar.csv"          # the INTACT calendar (use this)
REVIEWS_CSV   = DATA / "reviews.csv"
GEOJSON       = DATA / "neighbourhoods.geojson"


def read_listings(**kwargs):
    """Read the listings file whether it's .csv (Inside Airbnb) or .xlsx."""
    import pandas as pd
    if str(LISTINGS).lower().endswith(".xlsx"):
        return pd.read_excel(LISTINGS, **kwargs)
    return pd.read_csv(LISTINGS, low_memory=False, **kwargs)

# NOTE: use calendar.csv (the full, intact export). Never open it in Excel —
# Excel truncates at 1,048,576 rows and mangles big listing_ids into scientific
# notation. Always read listing_id as str.

# --- Outputs (safe to delete / regenerate; git-ignored) ---
OUT     = Path(__file__).resolve().parent.parent / "outputs"
FIGURES = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

# Cleaned intermediate files — these are the "contract" between the shared
# cleaning stage and BOTH analysis tracks (Python-only and R).
LISTINGS_CLEAN = OUT / "listings_clean.csv"
CALENDAR_DAILY = OUT / "calendar_daily.csv"      # availability aggregated to day
CALENDAR_BYLISTING = OUT / "calendar_by_listing.csv"
REVIEWS_CLEAN  = OUT / "reviews_clean.csv"
