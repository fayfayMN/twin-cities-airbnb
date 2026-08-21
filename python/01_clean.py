"""
STEP 2: CLEAN the raw data into tidy, analysis-ready files.

This is the SHARED stage. It runs once, in Python, and writes clean CSVs that
feed BOTH analysis tracks:
    - Track A: Python-only EDA (02_eda.py, 03_geo_map.py, 04_review_nlp.py)
    - Track B: R analysis (R/01_eda.R, R/02_review_nlp.R)

Holding the cleaning constant is what makes "Python vs R" a fair comparison:
same inputs, only the analysis language changes.

Outputs (to ../outputs/):
    listings_clean.csv      one row per listing, tidy columns + amenity booleans
    calendar_by_listing.csv one row per listing: forward availability stats
    calendar_daily.csv      one row per date: % of listings available (seasonality)
    reviews_clean.csv        reviews + year/month + text length

Run:  python 01_clean.py
Needs: pandas, openpyxl
"""
import ast
import re
import sys
import pandas as pd
import config as C

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Amenities we care about (post-COVID / Twin-Cities relevant). Each becomes a
# boolean column amen_<name>. Extend this list freely.
AMENITY_FLAGS = {
    "wifi": ["wifi"],
    "free_parking": ["free parking", "free residential garage", "free driveway"],
    "air_conditioning": ["air conditioning", "central air"],
    "heating": ["heating"],
    "workspace": ["dedicated workspace", "workspace"],
    "kitchen": ["kitchen"],
    "washer": ["washer"],
    "dryer": ["dryer"],
    "pool": ["pool"],
    "hot_tub": ["hot tub"],
    "ev_charger": ["ev charger"],
    "self_checkin": ["self check-in", "self check in", "keypad", "lockbox", "smart lock"],
    "pets_allowed": ["pets allowed"],
}


def clean_price(series: pd.Series) -> pd.Series:
    """Return price as float, whether it arrives as '$1,200.00' text or numeric.
    Works on the raw .csv (text, possibly arrow-string dtype in pandas 3.x) and
    the .xlsx (already numeric). Use is_numeric_dtype, NOT `== object`, because
    pandas 3.0 reads text columns as an arrow 'string' dtype, not object."""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    return (series.astype(str)
                  .str.replace(r"[$,]", "", regex=True)
                  .replace({"": None, "nan": None, "None": None})
                  .astype(float))


def parse_amenities(cell) -> list:
    """Amenities arrive as a JSON-ish string: '["Wifi", "Kitchen", ...]'.
    Parse robustly and lowercase for matching."""
    if pd.isna(cell):
        return []
    try:
        items = ast.literal_eval(cell) if isinstance(cell, str) else cell
        return [str(x).lower() for x in items]
    except (ValueError, SyntaxError):
        # fall back to a loose split if the string is malformed
        return [t.strip().lower() for t in re.split(r'[",\[\]]', str(cell)) if t.strip()]


def bathrooms_to_number(row) -> float:
    """bathrooms_text is messy free text: '1 bath', 'Private half-bath', '2.5 baths'.
    Prefer the numeric `bathrooms` column; fall back to parsing the text."""
    if pd.notna(row.get("bathrooms")):
        return float(row["bathrooms"])
    txt = str(row.get("bathrooms_text", "")).lower()
    if "half" in txt:
        return 0.5
    m = re.search(r"(\d+\.?\d*)", txt)
    return float(m.group(1)) if m else None


def clean_listings() -> pd.DataFrame:
    df = C.read_listings()

    keep = [
        "id", "host_id", "host_since", "host_is_superhost",
        "host_response_time", "host_response_rate", "host_acceptance_rate",
        "host_identity_verified", "host_listings_count",
        "neighbourhood_cleansed", "neighbourhood_group_cleansed",
        "latitude", "longitude", "property_type", "room_type",
        "accommodates", "bedrooms", "beds",
        "price", "minimum_nights", "maximum_nights",
        "availability_30", "availability_90", "availability_365",
        "number_of_reviews", "number_of_reviews_ltm", "reviews_per_month",
        "estimated_occupancy_l365d", "estimated_revenue_l365d",
        "review_scores_rating", "review_scores_cleanliness",
        "review_scores_location", "review_scores_value",
        "first_review", "last_review",
    ]
    keep = [c for c in keep if c in df.columns]
    out = df[keep].copy()
    out = out.rename(columns={"id": "listing_id"})
    out["listing_id"] = out["listing_id"].astype(str)

    out["price"] = clean_price(out["price"])
    out["bathrooms"] = df.apply(bathrooms_to_number, axis=1)

    # normalize the t/f superhost flag to boolean
    out["host_is_superhost"] = out["host_is_superhost"].map(
        {"t": True, "f": False, True: True, False: False})

    # percent strings -> float
    for col in ["host_response_rate", "host_acceptance_rate"]:
        if col in out and out[col].dtype == object:
            out[col] = (out[col].astype(str).str.replace("%", "", regex=False)
                        .replace({"nan": None}).astype(float))

    # amenity booleans
    amen_lists = df["amenities"].apply(parse_amenities)
    for flag, needles in AMENITY_FLAGS.items():
        out[f"amen_{flag}"] = amen_lists.apply(
            lambda lst: any(any(n in a for a in lst) for n in needles))
    out["n_amenities"] = amen_lists.apply(len)

    # a couple of derived analysis fields
    out["price_per_person"] = out["price"] / out["accommodates"].replace(0, pd.NA)
    out["is_entire_home"] = out["room_type"].eq("Entire home/apt")

    return out


def summarize_calendar() -> tuple[pd.DataFrame, pd.DataFrame]:
    # dtype=str on listing_id protects the huge IDs (the Calendar 2026.csv bug)
    cal = pd.read_csv(C.CALENDAR_CSV, parse_dates=["date"],
                      dtype={"listing_id": str})
    cal["is_available"] = cal["available"].eq("t")

    # Per LISTING: forward availability rate over the snapshot window.
    # NOTE: (1 - available_rate) is an UPPER-BOUND occupancy proxy — 'f' can mean
    # booked OR host-blocked. We name it 'blocked_rate' to stay honest.
    by_listing = (cal.groupby("listing_id")
                     .agg(cal_nights=("date", "count"),
                          available_rate=("is_available", "mean"),
                          median_min_nights=("minimum_nights", "median"))
                     .reset_index())
    by_listing["blocked_rate"] = 1 - by_listing["available_rate"]

    # Per DATE: what fraction of listings are available (seasonality curve).
    daily = (cal.groupby("date")
                .agg(available_rate=("is_available", "mean"),
                     n_listings=("listing_id", "nunique"))
                .reset_index())
    daily["dow"] = daily["date"].dt.day_name()
    daily["month"] = daily["date"].dt.to_period("M").astype(str)
    return by_listing, daily


def clean_reviews() -> pd.DataFrame:
    rev = pd.read_csv(C.REVIEWS_CSV, parse_dates=["date"],
                      dtype={"listing_id": str, "id": str, "reviewer_id": str})
    rev["year"] = rev["date"].dt.year
    rev["month"] = rev["date"].dt.month
    rev["comment_len"] = rev["comments"].astype(str).str.len()
    return rev


def main():
    print("Cleaning listings...")
    listings = clean_listings()
    listings.to_csv(C.LISTINGS_CLEAN, index=False)
    print(f"  -> {C.LISTINGS_CLEAN.name}: {listings.shape[0]:,} rows x {listings.shape[1]} cols")

    print("Summarizing calendar...")
    by_listing, daily = summarize_calendar()
    by_listing.to_csv(C.CALENDAR_BYLISTING, index=False)
    daily.to_csv(C.CALENDAR_DAILY, index=False)
    print(f"  -> {C.CALENDAR_BYLISTING.name}: {by_listing.shape[0]:,} listings")
    print(f"  -> {C.CALENDAR_DAILY.name}: {daily.shape[0]:,} dates")

    print("Cleaning reviews...")
    reviews = clean_reviews()
    reviews.to_csv(C.REVIEWS_CLEAN, index=False)
    print(f"  -> {C.REVIEWS_CLEAN.name}: {reviews.shape[0]:,} rows")

    # quick sanity peek
    print("\nSample cleaned listing:")
    cols = ["listing_id", "neighbourhood_cleansed", "room_type", "price",
            "bathrooms", "host_is_superhost", "amen_workspace", "n_amenities"]
    print(listings[cols].head().to_string(index=False))


if __name__ == "__main__":
    main()
