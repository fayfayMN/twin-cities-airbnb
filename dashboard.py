"""
Twin Cities Airbnb — HOST OPTIMIZER (Streamlit).

The pro-host counterpart to Inside Airbnb: instead of "is Airbnb harming
housing?", it answers "how should I price and configure MY listing?"

Powered by python/06_model.py:
  - price_model  (log-R²≈0.74) -> fair nightly price + positioning
  - revenue_model (directional) -> a revenue RANGE, clearly caveated
  - price-model counterfactuals -> the top levers a host can actually pull

Run with the project venv:
    .venv\\Scripts\\streamlit.exe run dashboard.py
"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import joblib

sys.path.insert(0, str(Path(__file__).parent / "python"))
import fees  # host-only Airbnb fee math (default 15.5%, overridable)

st.set_page_config(page_title="Twin Cities Airbnb — Host Optimizer",
                   page_icon="🏠", layout="wide")

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
MODEL = OUT / "model"


@st.cache_resource
def load_models():
    price = joblib.load(MODEL / "price_model.joblib")
    rev = joblib.load(MODEL / "revenue_model.joblib")
    spec = json.loads((MODEL / "feature_spec.json").read_text(encoding="utf-8"))
    drivers = pd.read_csv(MODEL / "price_drivers.csv")
    prem = pd.read_csv(MODEL / "amenity_price_premium.csv")
    return price, rev, spec, drivers, prem


@st.cache_data
def load_listings():
    df = pd.read_csv(OUT / "listings_clean.csv")
    df["occupancy_pct"] = (df["estimated_occupancy_l365d"] / 365 * 100).round(1)
    return df


for need in [MODEL / "price_model.joblib", OUT / "listings_clean.csv"]:
    if not need.exists():
        st.error(f"Missing {need}. Run `python/01_clean.py` then `python/06_model.py` first.")
        st.stop()

price_m, rev_m, spec, drivers, prem = load_models()
df = load_listings()
AMEN = spec["amenities"]


def build_row(features, inputs):
    """One-row DataFrame in the exact column order a model was trained on."""
    return pd.DataFrame([{f: inputs.get(f, 0) for f in features}])[features]


def predict(model_obj, inputs):
    row = build_row(model_obj["features"], inputs)
    yhat = model_obj["pipeline"].predict(row)[0]
    return float(np.expm1(yhat)) if model_obj.get("log") else float(yhat)


# =====================================================================
st.title("🏠 Twin Cities Airbnb — Host Optimizer")
st.caption("Score a listing, find its fair price, and see the top levers. "
           "The pro-host complement to Inside Airbnb's housing-policy view.")

left, right = st.columns([1, 2])

with left:
    st.subheader("① Describe the listing")
    room_type = st.selectbox("Room type", spec["categorical"]["room_type"],
                             index=0)
    county = st.selectbox("County", spec["categorical"]["neighbourhood_cleansed"],
                          index=spec["categorical"]["neighbourhood_cleansed"].index("Hennepin")
                          if "Hennepin" in spec["categorical"]["neighbourhood_cleansed"] else 0)
    accommodates = st.slider("Accommodates", 1, 16, 4)
    bedrooms = st.slider("Bedrooms", 0, 8, 2)
    bathrooms = st.slider("Bathrooms", 0.5, 6.0, 1.0, step=0.5)
    min_nights = st.slider("Minimum nights", 1, 30, 2)
    superhost = st.checkbox("Superhost", value=False)
    chosen_amen = st.multiselect(
        "Amenities", [a.replace("amen_", "") for a in AMEN],
        default=["wifi", "kitchen", "heating"])
    your_price = st.number_input("Your current nightly price ($, optional)",
                                 min_value=0, value=0, step=10)

# assemble the feature dict
inp = {
    "accommodates": accommodates, "bedrooms": bedrooms, "bathrooms": bathrooms,
    "minimum_nights": min_nights, "n_amenities": len(chosen_amen),
    "room_type": room_type, "neighbourhood_cleansed": county,
    "host_is_superhost": int(superhost),
    "is_entire_home": int(room_type == "Entire home/apt"),
}
for a in AMEN:
    inp[a] = int(a.replace("amen_", "") in chosen_amen)

fair_price = predict(price_m, inp)
inp_with_price = {**inp, "price": your_price or fair_price}
pred_rev = predict(rev_m, inp_with_price)

with right:
    st.subheader("② Fair price & positioning")
    comps = df[(df["room_type"] == room_type) &
               (df["neighbourhood_cleansed"] == county) & (df["price"] > 0)]["price"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Model fair price", f"${fair_price:,.0f}/night")
    if len(comps) >= 5:
        c2.metric("Comparable median", f"${comps.median():,.0f}",
                  help=f"{len(comps)} listings, same room type & county")
        if your_price:
            pctile = (comps < your_price).mean() * 100
            c3.metric("Your price percentile", f"{pctile:.0f}th",
                      delta=f"{your_price - comps.median():+,.0f} vs median")
    # positioning distribution
    if len(comps) >= 5:
        fig = px.histogram(comps[comps < comps.quantile(0.98)], nbins=40,
                           title="Where you sit among comparable listings")
        fig.add_vline(x=fair_price, line_color="green", annotation_text="fair price")
        if your_price:
            fig.add_vline(x=your_price, line_color="crimson", annotation_text="your price")
        st.plotly_chart(fig, use_container_width=True)

    # directional revenue range
    st.subheader("③ Revenue potential (directional)")
    lo, hi = pred_rev * 0.6, pred_rev * 1.5
    st.info(f"Estimated annual revenue ≈ **${pred_rev:,.0f}** "
            f"(range ${lo:,.0f}–${hi:,.0f}). "
            "The revenue model is weaker (log-R²≈0.48) — treat as a ballpark, "
            "not a promise. Price above is the reliable output (R²≈0.74).")

# =====================================================================
st.divider()
st.subheader("④ Net income after Airbnb fees (host-only model)")
st.caption("Airbnb's 'simplified pricing' puts the full service fee on the host. "
           "The fee applies to your accommodation + cleaning subtotal (not taxes, "
           "which Airbnb collects & remits separately). VERIFY the exact % on your "
           "own Airbnb payout settings — it varies by region/listing.")

fc1, fc2, fc3, fc4 = st.columns(4)
fee_pct = fc1.number_input("Host service fee (%)", 0.0, 30.0, 15.5, step=0.5) / 100
cleaning = fc2.number_input("Cleaning fee ($/booking)", 0, 1000, 75, step=5)
# sensible default booked-nights from comparable occupancy
comp_occ = df[(df["room_type"] == room_type) &
              (df["neighbourhood_cleansed"] == county)]["estimated_occupancy_l365d"]
default_nights = int(comp_occ.median()) if len(comp_occ) >= 5 and comp_occ.median() > 0 else 120
booked_nights = fc3.slider("Expected booked nights/yr", 0, 365, min(default_nights, 365))
op_cost = fc4.number_input("Your cost per night ($, optional)", 0, 500, 0, step=5,
                           help="Cleaner pay, supplies, utilities. 0 = Airbnb-only view.")

nightly_used = your_price or fair_price
a = fees.annual_net(nightly_used, booked_nights, avg_stay=max(min_nights, 1),
                    cleaning=cleaning, fee_rate=fee_pct,
                    operating_cost_per_night=op_cost)

n1, n2, n3, n4 = st.columns(4)
n1.metric("Annual gross", f"${a['gross']:,.0f}")
n2.metric("Airbnb fee", f"−${a['service_fee']:,.0f}", delta=f"{fee_pct*100:.1f}%",
          delta_color="inverse")
n3.metric("Net payout", f"${a['net_payout']:,.0f}",
          help="After Airbnb's fee, before your own costs")
if op_cost:
    n4.metric("Take-home", f"${a['take_home']:,.0f}", help="After your costs too")
else:
    n4.metric("Net per night", f"${a['net_per_night']:,.0f}")

# gross-up helper — the actionable pricing insight
target = st.number_input("If you want to TAKE HOME this much per night ($)…",
                         0, 2000, int(nightly_used * (1 - fee_pct)), step=5)
list_at = fees.gross_up_nightly(target, fee_pct)
st.success(f"…list at **${list_at:,.0f}/night** so that after the {fee_pct*100:.1f}% "
           f"host fee you keep ${target:,.0f}. (The fee is why your list price must "
           "exceed your target take-home.)")

# =====================================================================
st.divider()
st.subheader("⑤ Levers that raise your nightly RATE")
st.caption("Each row re-runs the price model changing ONE thing, holding the rest "
           "fixed. Note: Superhost usually shows ~$0 here because it lifts *bookings*, "
           "not your nightly rate — separately, Superhosts earn ~5× the median revenue.")

levers = []
# superhost lever
alt = {**inp, "host_is_superhost": 1 - inp["host_is_superhost"]}
levers.append(("Become a Superhost" if not superhost else "Lose Superhost status",
               predict(price_m, alt) - fair_price))
# add each not-yet-selected amenity
for a in AMEN:
    name = a.replace("amen_", "")
    if inp[a] == 0:
        alt = {**inp, a: 1, "n_amenities": inp["n_amenities"] + 1}
        levers.append((f"Add {name.replace('_',' ')}", predict(price_m, alt) - fair_price))
# capacity lever
alt = {**inp, "accommodates": accommodates + 2}
levers.append(("Sleep 2 more guests", predict(price_m, alt) - fair_price))

lev = (pd.DataFrame(levers, columns=["lever", "price_delta"])
         .sort_values("price_delta", ascending=False).head(10))
fig = px.bar(lev, x="price_delta", y="lever", orientation="h",
             color=lev["price_delta"] > 0,
             color_discrete_map={True: "seagreen", False: "crimson"},
             labels={"price_delta": "$ change in fair nightly price"})
fig.update_layout(showlegend=False, yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig, use_container_width=True)

# =====================================================================
st.divider()
colA, colB = st.columns(2)
with colA:
    st.subheader("Amenity price premium (market)")
    st.caption("Median nightly price with vs without each amenity, across all listings.")
    fig = px.bar(prem.sort_values("premium").tail(10), x="premium", y="amenity",
                 orientation="h", labels={"premium": "$/night premium"})
    st.plotly_chart(fig, use_container_width=True)
with colB:
    st.subheader("What drives nightly price")
    st.caption("Permutation importance from the price model (R²≈0.74).")
    fig = px.bar(drivers.head(8).sort_values("importance"),
                 x="importance", y="feature", orientation="h")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
with st.expander("Model honesty / caveats"):
    st.markdown((MODEL / "model_card.md").read_text(encoding="utf-8"))
