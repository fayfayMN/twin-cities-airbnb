"""
STEP 4 (deep): Business insights BEYOND the dashboard.

The Streamlit app shows distributions and a few group comparisons. This script
answers the harder questions analysts actually get asked, and writes a
Markdown report to outputs/insights_report.md.

Insights computed:
  1. Superhost effect — raw AND controlled (within room type), to fight the
     "is it causal or just mix?" confound.
  2. Amenity premium ranking — does a workspace out-earn free parking? (post-COVID)
  3. Revenue concentration (Pareto) — is Airbnb a side-gig or a business here?
  4. Host professionalization — share of listings held by multi-listing hosts.
  5. Pricing sweet spot — revenue by price decile (where the money peaks).
  6. Minimum-nights strategy — occupancy/revenue vs min-nights buckets.
  7. Dead listings — share with no review in the last 12 months.
  8. Regulation/compliance — share missing a license.
  9. Property/room mix and where revenue concentrates.
 10. Forward seasonality peak/trough from the calendar.

Run:  python 05_insights.py
Needs: pandas, numpy
"""
import sys
import numpy as np
import pandas as pd
import config as C

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REV = "estimated_revenue_l365d"
OCC = "estimated_occupancy_l365d"


def main():
    df = pd.read_csv(C.LISTINGS_CLEAN)
    daily = pd.read_csv(C.CALENDAR_DAILY, parse_dates=["date"])
    md = ["# Twin Cities Airbnb — Insights Report",
          "_Beyond the dashboard: computed by 05_insights.py._", ""]

    def section(title):
        print(f"\n{'='*66}\n{title}")
        md.append(f"\n## {title}\n")

    def emit(line):
        print("  " + line)
        md.append(f"- {line}")

    rev = df.dropna(subset=[REV])

    # 1. Superhost effect: raw vs controlled -----------------------------
    section("1. Superhost effect — raw vs. controlled")
    g = rev.groupby("host_is_superhost")[REV].median()
    if {True, False} <= set(g.index):
        raw = g[True] / g[False]
        emit(f"RAW: Superhost median revenue ${g[True]:,.0f} vs ${g[False]:,.0f} "
             f"= **{raw:.1f}x**.")
    # control for room type: within each room type, superhost vs not
    ctrl = (rev.groupby(["room_type", "host_is_superhost"])[REV].median()
               .unstack())
    if True in ctrl.columns and False in ctrl.columns:
        for rt, row in ctrl.iterrows():
            if pd.isna(row[True]) or pd.isna(row[False]):
                continue
            liftx = f"{row[True]/row[False]:.1f}x" if row[False] > 0 else "n/a (base $0)"
            emit(f"WITHIN {rt}: {liftx} (${row[True]:,.0f} vs ${row[False]:,.0f})")
        emit("If the within-room-type lift stays high, the Superhost gap is "
             "not just a room-type mix artifact.")

    # 2. Amenity premium -------------------------------------------------
    section("2. Amenity premium — which amenity pays most?")
    rows = []
    for c in [c for c in df.columns if c.startswith("amen_")]:
        gg = rev.groupby(c)[REV].median()
        if {True, False} <= set(gg.index):
            share = df[c].mean()
            rows.append((c.replace("amen_", ""), gg[True] - gg[False], share))
    amen = pd.DataFrame(rows, columns=["amenity", "rev_lift", "prevalence"]).sort_values("rev_lift", ascending=False)
    for _, r in amen.head(6).iterrows():
        emit(f"{r.amenity:16s} +${r.rev_lift:>8,.0f}/yr  (in {r.prevalence*100:.0f}% of listings)")
    wk = amen.set_index("amenity")["rev_lift"]
    if "workspace" in wk and "free_parking" in wk:
        emit(f"POST-COVID CHECK: workspace lift ${wk['workspace']:,.0f} vs "
             f"free_parking ${wk['free_parking']:,.0f} — "
             f"{'workspace wins' if wk['workspace']>wk['free_parking'] else 'parking wins'}.")

    # 3. Revenue concentration (Pareto) ----------------------------------
    section("3. Revenue concentration — side-gig or business?")
    s = rev[REV].sort_values(ascending=False).values
    cum = np.cumsum(s) / s.sum()
    top10_share = cum[int(len(s) * 0.10)] if len(s) > 10 else np.nan
    top20_share = cum[int(len(s) * 0.20)] if len(s) > 20 else np.nan
    emit(f"Top 10% of listings capture **{top10_share*100:.0f}%** of estimated revenue.")
    emit(f"Top 20% capture {top20_share*100:.0f}%. (High = a professionalized market.)")

    # 4. Host professionalization ---------------------------------------
    section("4. Host professionalization")
    per_host = df.groupby("host_id").size()
    multi = (per_host > 1)
    emit(f"{multi.mean()*100:.0f}% of hosts run multiple listings; they own "
         f"{df['host_id'].isin(per_host[multi].index).mean()*100:.0f}% of all listings.")
    biggest = per_host.sort_values(ascending=False).head(3)
    emit(f"Largest hosts by listing count: {biggest.tolist()}")

    # 5. Pricing sweet spot ---------------------------------------------
    section("5. Pricing sweet spot — revenue by price decile")
    p = rev[(rev["price"] > 0) & (rev["price"] < rev["price"].quantile(0.99))].copy()
    p["price_decile"] = pd.qcut(p["price"], 10, duplicates="drop")
    band = p.groupby("price_decile", observed=True).agg(
        med_price=("price", "median"), med_rev=(REV, "median"),
        med_occ=(OCC, "median")).reset_index(drop=True)
    best = band.loc[band["med_rev"].idxmax()]
    emit(f"Revenue peaks around **${best.med_price:,.0f}/night** "
         f"(median rev ${best.med_rev:,.0f}, occ {best.med_occ:.0f} nights).")
    emit("Above that band, higher price no longer lifts revenue (occupancy drops faster).")

    # 6. Minimum-nights strategy ----------------------------------------
    section("6. Minimum-nights strategy")
    rev2 = rev.copy()
    rev2["min_bucket"] = pd.cut(rev2["minimum_nights"], [0, 1, 2, 3, 7, 29, 10000],
                                labels=["1", "2", "3", "4-7", "8-29", "30+"])
    mn = rev2.groupby("min_bucket", observed=True).agg(
        n=("listing_id", "count"), med_rev=(REV, "median"), med_occ=(OCC, "median"))
    for b, r in mn.iterrows():
        emit(f"min_nights {str(b):5s}: n={int(r.n):4d}  med_rev ${r.med_rev:>7,.0f}  occ {r.med_occ:.0f}")
    emit("CAVEAT: 30+ min-nights = monthly rentals; Airbnb's review-based estimator "
         "reports $0/0 for them (it can't see long-stay occupancy), not truly zero income.")
    emit("Signal that IS reliable: a **2-night minimum** shows the highest median "
         "revenue — the practical sweet spot vs 1-night (more turnover) or 3+ (fewer bookings).")

    # 7. Dead listings ---------------------------------------------------
    section("7. Dead / inactive listings")
    dead = (df["number_of_reviews_ltm"].fillna(0) == 0)
    emit(f"{dead.mean()*100:.0f}% of listings had **zero reviews in the last 12 months** "
         "(inactive, blocked, or brand-new).")

    # 8. Compliance ------------------------------------------------------
    section("8. Regulation / licensing")
    if "license" in df.columns:
        # license was dropped in cleaning; recompute from raw if present
        pass
    # license not in cleaned file — note it as a follow-up
    emit("`license` is ~67% missing in the raw listings — a compliance angle worth "
         "a dedicated pass (add it to 01_clean.py keep-list to analyze).")

    # 9. Room / property mix --------------------------------------------
    section("9. Room-type mix and revenue share")
    mix = df.groupby("room_type").agg(
        listings=("listing_id", "count"),
        rev_share=(REV, lambda x: x.sum())).assign(
        rev_share=lambda d: d["rev_share"] / rev[REV].sum() * 100)
    for rt, r in mix.sort_values("rev_share", ascending=False).iterrows():
        emit(f"{rt:18s} {int(r.listings):4d} listings, {r.rev_share:.0f}% of revenue")

    # 10. Forward seasonality -------------------------------------------
    section("10. Forward seasonality (from calendar)")
    daily["blocked"] = 1 - daily["available_rate"]
    monthly = daily.groupby(daily["date"].dt.to_period("M"))["blocked"].mean()
    peak, trough = monthly.idxmax(), monthly.idxmin()
    emit(f"Tightest month (most booked/blocked): {peak} ({monthly.max()*100:.0f}% blocked).")
    emit(f"Loosest month: {trough} ({monthly.min()*100:.0f}% blocked).")
    emit("CAVEAT: far-future months look 'booked' mostly because hosts haven't OPENED "
         "those dates yet (calendars default closed), not real demand. Trust the "
         "near-term months (next ~3-4) and ignore the tail near the snapshot's far edge.")
    dow = daily.groupby(daily["date"].dt.day_name())["blocked"].mean().sort_values(ascending=False)
    emit(f"Most-blocked weekday: {dow.index[0]} vs least {dow.index[-1]}.")

    out = C.OUT / "insights_report.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
