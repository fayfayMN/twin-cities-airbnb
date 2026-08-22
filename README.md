# Twin Cities Airbnb — EDA Playbook (Python vs. Python→R)
https://airbnb-real-world-eda-playbook.streamlit.app/
A **reusable, portfolio-quality template** for exploring any raw dataset with no
business question given up front — applied to the 2026 Inside Airbnb data for the
Twin Cities (Minneapolis–St. Paul).

It deliberately runs the analysis **two ways on identical cleaned data** so you
can feel where each toolchain wins:

- **Track A — Python only** (`python/02–04`)
- **Track B — Python cleans → R analyzes** (`R/01–02`)

The cleaning stage is shared and runs **once in Python**, so any difference you
see between tracks is the *language*, not the data.

---

## The standard EDA method (works on ANY raw dataset)

This is the real-world sequence. Do them in order; don't skip 0–2.

| Step | Name | What you actually do | Script |
|---|---|---|---|
| 0 | **Grain & provenance** | For each table: what is *one row*? key? date range? how collected? | `00_profile.py` |
| 1 | **Profile before plotting** | Every column: dtype, % missing, cardinality, examples, red flags | `00_profile.py` |
| 2 | **Clean to tidy** | numeric price, parsed amenities, one clean table per grain | `01_clean.py` |
| 3 | **Univariate → bivariate → multivariate** | distributions → pairs → interactions | `02_eda.py` / `R/01_eda.R` |
| 4 | **Let patterns become questions** | each chart *raises* the next question | (same) |
| 5 | **Geo + text** | map on polygons; mine review language | `03_geo_map.py`, `04_review_nlp.py`, `R/02_review_nlp.R` |

> **Key idea:** you don't need a business question to start. EDA *generates* the
> questions. "County X is 2× the median price" → *is that room-type mix or a real
> location premium?* → the next chart. That loop is the whole job.

---

## Data — download

The raw data is **not committed** (it's large and is public data). Download the
four files below and drop them in a local `Datasets/` folder before running the
pipeline.

| File | Size | Download |
|---|---|---|
| `listings.csv` | ~16 MB | [Google Drive](https://drive.google.com/file/d/1OtEkj7AnnS_Rnyseeb3mLQYETjOa1X5C/view?usp=sharing) |
| `reviews.csv` | ~91 MB | [Google Drive](https://drive.google.com/file/d/14bK45iDPD7ZkdGJr0K3Je0phLEOBQxam/view?usp=sharing) |
| `calendar.csv` | ~70 MB | [Google Drive](https://drive.google.com/file/d/1YYzoedTNKAtkeHPVzatfaH41wO4Mmofm/view?usp=sharing) |
| `neighbourhoods.geojson` | ~0.7 MB | [Google Drive](https://drive.google.com/file/d/1o57TRRQ5IEzGHxJSTo0sm_YTB53LZj6Y/view?usp=drive_link) |

**Original source:** [Inside Airbnb — Get the Data](https://insideairbnb.com/get-the-data/)
(Twin Cities MSA). The Drive links above are a convenience mirror of that public dataset.

> The pipeline reads `listings` as `.xlsx` by default (`python/config.py`); the
> Drive copy is `.csv`. Either works — `01_clean.py` handles both price formats.

---

## What the raw data actually is (verified, not assumed)

| File | Grain | Notes |
|---|---|---|
| `listings.xlsx` | one listing (5,349) | 90 cols. Current schema — **already includes `estimated_occupancy_l365d` and `estimated_revenue_l365d`**. |
| `calendar.csv` | one listing-night (1.95M) | ✅ **Use this.** ISO dates, full IDs, all 5,353 listings. **No price column.** Forward window 2026-06-28 → 2027-07-02. |
| `reviews.csv` | one review (319K) | `listing_id, id, date, reviewer_id, reviewer_name, comments`. |
| `neighbourhoods.geojson` | 16 **county** polygons | join key = `neighbourhood` (= listings' `neighbourhood_cleansed`). |

### ⚠️ Data traps found while profiling (the real lesson)

1. **The calendar has no price.** Price lives *only* in listings. You cannot
   compute ADR/revenue from the calendar (a common outdated tutorial assumes you
   can). Use the calendar for **forward seasonality** instead.
2. **Occupancy is already provided.** `estimated_occupancy_l365d` /
   `estimated_revenue_l365d` ship in listings — no manual calendar math needed.
3. **Calendar is forward-looking, not history.** `available='f'` = booked **or**
   host-blocked → calendar "occupancy" is an **upper bound**, call it *blocked*.
4. **Neighborhoods are counties.** Hennepin = all of Minneapolis, Ramsey = St.
   Paul. You **cannot** do "North Loop vs Uptown" from this field — only county
   level, or lat/long clustering.
5. **`instant_bookable` is 100% empty** in this export — don't build on it.
6. **Don't open these CSVs in Excel.** Excel truncates at 1,048,576 rows and
   mangles big `listing_id`s into scientific notation — process them only in
   Python/R.

---

## How to run

```bash
# 0. one-time setup
pip install -r requirements.txt

# 1. shared: profile + clean (writes outputs/*.csv)  — always run these first
cd python
python 00_profile.py      # -> outputs/data_dictionary.md
python 01_clean.py        # -> outputs/listings_clean.csv, calendar_*.csv, reviews_clean.csv

# 2a. TRACK A — Python only
python 02_eda.py          # -> outputs/figures/01–07*.png
python 03_geo_map.py      # -> outputs/map_price.html
python 04_review_nlp.py   # -> outputs/figures/08–09*.png

# 2b. TRACK B — R (reads the SAME cleaned csvs)
cd ..
Rscript R/01_eda.R        # -> outputs/figures/R_01–06*.png
Rscript R/02_review_nlp.R # -> outputs/figures/R_08–10*.png
```

Then compare `01_price_by_roomtype.png` vs `R_02_price_by_roomtype.png`, etc.

---

## Python vs. R — what you'll actually learn

| Task | Python (pandas/seaborn) | R (tidyverse/ggplot2) | Verdict |
|---|---|---|---|
| Reading messy Excel / big CSVs | pandas, `openpyxl` | readr/readxl | **Python** — more robust I/O |
| Parsing amenities JSON, regex on text | `ast`, `re` | stringr | **Python** — general-purpose |
| Group-by + summarise | `df.groupby().agg()` | `group_by() |> summarise()` | tie |
| Faceted, publication charts | seaborn (ok) | ggplot2 (`facet_wrap`, `reorder_within`) | **R** — cleaner grammar |
| Text mining / sentiment | VADER + Counter (manual) | **tidytext** (4-line pipe + lexicons) | **R** — clearly easier |
| Interactive map | folium (great) | leaflet | tie |

**Takeaway you're testing:** Python is the better *engine room* (I/O, wrangling,
parsing); R is the better *finishing shop* (ggplot2 charts, tidytext NLP). For a
5K-row dataset either language does the whole job — the split matters more at
scale, and for how polished the final charts/NLP look.

---

## Business questions this dataset *can* answer

- **Superhost effect** — do Superhosts earn more est. revenue? (confounded by
  listing quality — note it, don't overclaim causation)
- **Amenity premium** — post-COVID, does a *dedicated workspace* out-earn *free
  parking*? (`05_amenity_premium.png`)
- **County pricing** — highest median price and revenue-per-dollar by county
- **Min-nights strategy** — is there a sweet spot vs. blocked rate?
- **Seasonality** — when does forward availability tighten? (`06_seasonality.png`)
- **Twin-Cities review themes** — snow / parking / lakes / noise, and whether
  winter reviews score lower (`08`, `09`, R `10`)

## Layout

```
twin-cities-airbnb/
├── README.md                 # this playbook
├── requirements.txt
├── python/
│   ├── config.py             # single source of paths
│   ├── 00_profile.py         # Step 0–1  (verified ✓)
│   ├── 01_clean.py           # Step 2 — shared cleaning  (verified ✓)
│   ├── 02_eda.py             # Track A EDA
│   ├── 03_geo_map.py         # Track A map
│   └── 04_review_nlp.py      # Track A NLP
├── R/
│   ├── 01_eda.R              # Track B EDA
│   └── 02_review_nlp.R       # Track B NLP (tidytext)
└── outputs/                  # generated; git-ignored
```
