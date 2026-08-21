"""Shared paths and constants for the Twin Cities Airbnb project.

Every script imports from here so there is ONE place that knows where the raw
data lives and where outputs go. This is a real-world habit: never hard-code a
path in five different scripts.
"""
from pathlib import Path

# --- Raw data (read-only; never write here, never open these in Excel) ---
DATA = Path(r"C:\Users\GPU\Documents\Twin Cities Airbnb DATASETS")

LISTINGS_XLSX = DATA / "listings.xlsx"
CALENDAR_CSV  = DATA / "calendar.csv"          # the INTACT calendar (use this)
REVIEWS_CSV   = DATA / "reviews.csv"
GEOJSON       = DATA / "neighbourhoods.geojson"

# NOTE: "Calendar 2026.csv" is deliberately NOT referenced. Excel corrupted it:
# truncated to 1,048,576 rows, mangled dates, and destroyed listing_id into
# scientific notation. calendar.csv is the complete, uncorrupted export.

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
