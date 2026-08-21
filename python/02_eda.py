"""
TRACK A - STEP 3/4: Python-only EDA (univariate -> bivariate) with saved charts.

Reads the SHARED cleaned files and produces figures in ../outputs/figures/.
This is the "let the data propose questions" stage: distributions first, then
relationships, each chart annotated with the question it answers.

Run:  python 02_eda.py
Needs: pandas, matplotlib, seaborn   (pip install -r ../requirements.txt)
"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")            # write files, no interactive window
import matplotlib.pyplot as plt
import seaborn as sns
import config as C

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sns.set_theme(style="whitegrid")
FIG = C.FIGURES


def save(fig, name):
    path = FIG / name
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {path.name}")


def main():
    df = pd.read_csv(C.LISTINGS_CLEAN)
    daily = pd.read_csv(C.CALENDAR_DAILY, parse_dates=["date"])
    price = df["price"].dropna()

    # ---- Q1: what does price look like? (always log-scale Airbnb price) ----
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    sns.histplot(price.clip(upper=price.quantile(0.99)), bins=50, ax=axes[0])
    axes[0].set_title("Nightly price (raw, 99th-pct clipped)")
    sns.histplot(np.log10(price[price > 0]), bins=50, ax=axes[1], color="darkorange")
    axes[1].set_title("log10(price) — the distribution is right-skewed")
    save(fig, "01_price_distribution.png")

    # ---- Q2: price by room type ----
    fig, ax = plt.subplots(figsize=(9, 5))
    order = df.groupby("room_type")["price"].median().sort_values().index
    sns.boxplot(data=df[df["price"] < price.quantile(0.98)],
                x="room_type", y="price", order=order, ax=ax)
    ax.set_title("Price by room type (median-ordered, outliers trimmed)")
    ax.tick_params(axis="x", rotation=20)
    save(fig, "02_price_by_roomtype.png")

    # ---- Q3: which counties are most expensive / most listed? ----
    by_area = (df.groupby("neighbourhood_cleansed")
                 .agg(n=("listing_id", "count"),
                      median_price=("price", "median"),
                      median_rev=("estimated_revenue_l365d", "median"))
                 .sort_values("n", ascending=False).head(12))
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=by_area.reset_index(), y="neighbourhood_cleansed",
                x="median_price", ax=ax, color="steelblue")
    ax.set_title("Median nightly price by county (top 12 by listing count)")
    save(fig, "03_price_by_county.png")

    # ---- Q4: the Superhost effect on estimated revenue ----
    fig, ax = plt.subplots(figsize=(8, 5))
    sub = df.dropna(subset=["host_is_superhost", "estimated_revenue_l365d"])
    sns.boxplot(data=sub[sub["estimated_revenue_l365d"] < sub["estimated_revenue_l365d"].quantile(0.97)],
                x="host_is_superhost", y="estimated_revenue_l365d", ax=ax)
    ax.set_title("Estimated annual revenue: Superhost vs not")
    save(fig, "04_superhost_revenue.png")
    med = sub.groupby("host_is_superhost")["estimated_revenue_l365d"].median()
    print(f"  Superhost median rev: {med.to_dict()}")

    # ---- Q5: the amenity premium (does a workspace out-earn free parking?) ----
    amen_cols = [c for c in df.columns if c.startswith("amen_")]
    rows = []
    for c in amen_cols:
        g = df.dropna(subset=["estimated_revenue_l365d"]).groupby(c)["estimated_revenue_l365d"].median()
        if {True, False} <= set(g.index):
            rows.append({"amenity": c.replace("amen_", ""),
                         "lift": g[True] - g[False]})
    lift = pd.DataFrame(rows).sort_values("lift")
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(data=lift, y="amenity", x="lift", ax=ax,
                palette=["crimson" if v < 0 else "seagreen" for v in lift["lift"]])
    ax.set_title("Median revenue lift when a listing HAS each amenity ($/yr)")
    ax.axvline(0, color="black", lw=0.8)
    save(fig, "05_amenity_premium.png")

    # ---- Q6: forward seasonality — availability over the calendar window ----
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(daily["date"], 1 - daily["available_rate"], color="purple")
    ax.set_title("Share of listings BLOCKED/booked by date (upper-bound demand)")
    ax.set_ylabel("blocked share")
    save(fig, "06_seasonality.png")

    # ---- correlation heatmap of the numeric core ----
    num = ["price", "accommodates", "bedrooms", "bathrooms", "minimum_nights",
           "number_of_reviews_ltm", "review_scores_rating",
           "estimated_occupancy_l365d", "estimated_revenue_l365d"]
    num = [c for c in num if c in df.columns]
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(df[num].corr(numeric_only=True), annot=True, fmt=".2f",
                cmap="RdBu_r", center=0, ax=ax)
    ax.set_title("Correlation of core numeric features")
    save(fig, "07_correlation.png")

    print("\nDone. Figures in outputs/figures/. Questions these RAISE:")
    print("  - Is the Superhost revenue gap causal, or just listing-quality mix?")
    print("  - Does workspace beat parking post-COVID? (see 05)")
    print("  - Which county has best revenue-per-dollar-price? (see by_area)")


if __name__ == "__main__":
    main()
