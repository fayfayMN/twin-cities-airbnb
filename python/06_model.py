"""
STEP 6: Models for the HOST OPTIMIZER.

Honest design, verified by cross-validation:
  - PRICE is predictable from structural features (CV R2 ~ 0.72) -> the reliable
    engine. Powers a "fair price / are you under-priced?" positioning tool.
  - REVENUE is only directional (CV R2 ~ 0.42 in log space) -> shown as a RANGE,
    clearly caveated, never a point promise.
  - OCCUPANCY (R2 ~ 0.16) is too noisy to model per-listing; we DON'T pretend to.

Evaluation is done in LOG space (stable) and MAE is reported in dollars
(interpretable). Earlier raw-dollar R2 was dominated by a few mega outliers.

Features = host-controllable only (price is a feature for the revenue model,
the TARGET for the price model). Review counts / availability excluded.

Outputs (../outputs/model/):
  price_model.joblib, revenue_model.joblib
  feature_spec.json, price_drivers.csv, amenity_price_premium.csv, model_card.md

Run with the project venv:  .venv\\Scripts\\python.exe python\\06_model.py
"""
import json
import sys
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import joblib
import config as C

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CATEG = ["room_type", "neighbourhood_cleansed"]
BOOLS = ["host_is_superhost", "is_entire_home"]
MODEL_DIR = C.OUT / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def make_pipe(cat_cols):
    pre = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)],
        remainder="passthrough")
    gb = HistGradientBoostingRegressor(max_depth=4, learning_rate=0.08,
                                       max_iter=400, l2_regularization=1.0,
                                       random_state=0)
    return Pipeline([("pre", pre), ("gb", gb)])


def prep(df, target, amen):
    """Return X, y(log), feature list for a given target."""
    numeric = ["price", "accommodates", "bedrooms", "bathrooms",
               "minimum_nights", "n_amenities"]
    if target == "price":
        numeric = [c for c in numeric if c != "price"]   # can't use target as feature
    feats = numeric + CATEG + BOOLS + amen
    d = df.dropna(subset=[target]).copy()
    d = d[d[target] > 0]
    d = d[d[target] < d[target].quantile(0.99)]
    for c in numeric:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(d[c].median())
    for c in BOOLS + amen:
        d[c] = d[c].fillna(False).astype(int)
    d[CATEG] = d[CATEG].fillna("Unknown")
    return d[feats], np.log1p(d[target]), feats


def fit_report(df, target, amen, label):
    X, ylog, feats = prep(df, target, amen)
    Xtr, Xte, ytr, yte = train_test_split(X, ylog, test_size=0.2, random_state=0)
    pipe = make_pipe(CATEG)
    pipe.fit(Xtr, ytr)
    r2 = r2_score(yte, pipe.predict(Xte))                    # log-space R2 (stable)
    mae = mean_absolute_error(np.expm1(yte), np.expm1(pipe.predict(Xte)))
    print(f"  [{label}] log-R2={r2:.3f}  MAE=${mae:,.0f}  n={len(X):,}")
    pipe.fit(X, ylog)                                        # refit on all data
    return pipe, feats, r2, mae


def main():
    df = pd.read_csv(C.LISTINGS_CLEAN)
    amen = [c for c in df.columns if c.startswith("amen_")]

    print("Training models...")
    price_pipe, price_feats, price_r2, price_mae = fit_report(df, "price", amen, "PRICE")
    rev_pipe, rev_feats, rev_r2, rev_mae = fit_report(df, "estimated_revenue_l365d", amen, "REVENUE")

    joblib.dump({"pipeline": price_pipe, "features": price_feats, "log": True},
                MODEL_DIR / "price_model.joblib")
    joblib.dump({"pipeline": rev_pipe, "features": rev_feats, "log": True},
                MODEL_DIR / "revenue_model.joblib")

    # --- price drivers (permutation importance) ---
    Xp, yp, _ = prep(df, "price", amen)
    perm = permutation_importance(price_pipe, Xp, yp, n_repeats=6,
                                  random_state=0, scoring="r2")
    drivers = (pd.DataFrame({"feature": price_feats, "importance": perm.importances_mean})
                 .sort_values("importance", ascending=False))
    drivers.to_csv(MODEL_DIR / "price_drivers.csv", index=False)
    print("\n  Top price drivers:")
    for _, r in drivers.head(8).iterrows():
        print(f"    {r.feature:22s} {r.importance:.3f}")

    # --- amenity price premium: median price with vs without each amenity ---
    prem = []
    base = df[df["price"] > 0]
    for a in amen:
        g = base.groupby(a)["price"].median()
        if {0, 1} <= set(g.index.astype(int)) or {False, True} <= set(g.index):
            gt = g.get(True, g.get(1)); gf = g.get(False, g.get(0))
            if gt is not None and gf is not None:
                prem.append({"amenity": a.replace("amen_", ""),
                             "price_with": gt, "price_without": gf,
                             "premium": gt - gf,
                             "prevalence": base[a].mean()})
    prem = pd.DataFrame(prem).sort_values("premium", ascending=False)
    prem.to_csv(MODEL_DIR / "amenity_price_premium.csv", index=False)

    # --- feature spec for the app form ---
    numeric_all = ["accommodates", "bedrooms", "bathrooms", "minimum_nights", "n_amenities"]
    spec = {
        "numeric": {c: {"min": float(pd.to_numeric(df[c], errors="coerce").min()),
                        "max": float(pd.to_numeric(df[c], errors="coerce").quantile(0.99)),
                        "median": float(pd.to_numeric(df[c], errors="coerce").median())}
                    for c in numeric_all},
        "categorical": {c: sorted(df[c].dropna().unique().tolist()) for c in CATEG},
        "bools": BOOLS,
        "amenities": amen,
        "price_features": price_feats,
        "revenue_features": rev_feats,
    }
    (MODEL_DIR / "feature_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

    card = [
        "# Host Optimizer — model card", "",
        "## Price model (the reliable engine)",
        f"- Predicts **nightly price** from structural features. Test log-R² = "
        f"**{price_r2:.2f}**, MAE = **${price_mae:,.0f}**.",
        "- Use: 'listings like yours charge ~$X' — a fair-price / positioning guide.",
        "",
        "## Revenue model (directional only)",
        f"- Predicts `estimated_revenue_l365d`. Test log-R² = **{rev_r2:.2f}**, "
        f"MAE = **${rev_mae:,.0f}** — shown as a RANGE, never a promise.",
        "",
        "## Honesty notes",
        "- Target revenue is Airbnb's own estimate, not audited income.",
        "- Occupancy (R²≈0.16) is too noisy to model per-listing — we don't.",
        "- Features are host-controllable only; review counts/availability excluded "
        "so every lever is something a host can actually change.",
    ]
    (MODEL_DIR / "model_card.md").write_text("\n".join(card), encoding="utf-8")
    print(f"\n  Wrote 2 models + spec + drivers + premium + card to {MODEL_DIR}")


if __name__ == "__main__":
    main()
