# Twin Cities Airbnb — Insights Report
_Beyond the dashboard: computed by 05_insights.py._


## 1. Superhost effect — raw vs. controlled

- RAW: Superhost median revenue $23,076 vs $4,471 = **5.2x**.
- WITHIN Entire home/apt: 3.2x ($28,929 vs $9,074)
- WITHIN Hotel room: n/a (base $0) ($12,624 vs $0)
- WITHIN Private room: 7.9x ($4,892 vs $618)
- If the within-room-type lift stays high, the Superhost gap is not just a room-type mix artifact.

## 2. Amenity premium — which amenity pays most?

- hot_tub          +$  16,750/yr  (in 7% of listings)
- self_checkin     +$  13,966/yr  (in 75% of listings)
- heating          +$  13,810/yr  (in 92% of listings)
- dryer            +$  13,192/yr  (in 89% of listings)
- kitchen          +$  12,828/yr  (in 92% of listings)
- wifi             +$  11,376/yr  (in 98% of listings)
- POST-COVID CHECK: workspace lift $3,378 vs free_parking $5,568 — parking wins.

## 3. Revenue concentration — side-gig or business?

- Top 10% of listings capture **42%** of estimated revenue.
- Top 20% capture 62%. (High = a professionalized market.)

## 4. Host professionalization

- 25% of hosts run multiple listings; they own 58% of all listings.
- Largest hosts by listing count: [100, 90, 75]

## 5. Pricing sweet spot — revenue by price decile

- Revenue peaks around **$791/night** (median rev $33,792, occ 42 nights).
- Above that band, higher price no longer lifts revenue (occupancy drops faster).

## 6. Minimum-nights strategy

- min_nights 1    : n=1959  med_rev $ 12,684  occ 60
- min_nights 2    : n=1649  med_rev $ 19,890  occ 72
- min_nights 3    : n= 412  med_rev $ 11,064  occ 36
- min_nights 4-7  : n= 281  med_rev $  3,680  occ 28
- min_nights 8-29 : n= 171  med_rev $  5,151  occ 56
- min_nights 30+  : n= 358  med_rev $      0  occ 0
- CAVEAT: 30+ min-nights = monthly rentals; Airbnb's review-based estimator reports $0/0 for them (it can't see long-stay occupancy), not truly zero income.
- Signal that IS reliable: a **2-night minimum** shows the highest median revenue — the practical sweet spot vs 1-night (more turnover) or 3+ (fewer bookings).

## 7. Dead / inactive listings

- 21% of listings had **zero reviews in the last 12 months** (inactive, blocked, or brand-new).

## 8. Regulation / licensing

- `license` is ~67% missing in the raw listings — a compliance angle worth a dedicated pass (add it to 01_clean.py keep-list to analyze).

## 9. Room-type mix and revenue share

- Entire home/apt    4135 listings, 96% of revenue
- Private room       1084 listings, 4% of revenue
- Hotel room          126 listings, 0% of revenue
- Shared room           4 listings, 0% of revenue

## 10. Forward seasonality (from calendar)

- Tightest month (most booked/blocked): 2027-07 (86% blocked).
- Loosest month: 2026-11 (26% blocked).
- CAVEAT: far-future months look 'booked' mostly because hosts haven't OPENED those dates yet (calendars default closed), not real demand. Trust the near-term months (next ~3-4) and ignore the tail near the snapshot's far edge.
- Most-blocked weekday: Friday vs least Tuesday.