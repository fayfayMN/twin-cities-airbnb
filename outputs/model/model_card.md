# Host Optimizer — model card

## Price model (the reliable engine)
- Predicts **nightly price** from structural features. Test log-R² = **0.74**, MAE = **$78**.
- Use: 'listings like yours charge ~$X' — a fair-price / positioning guide.

## Revenue model (directional only)
- Predicts `estimated_revenue_l365d`. Test log-R² = **0.48**, MAE = **$13,926** — shown as a RANGE, never a promise.

## Honesty notes
- Target revenue is Airbnb's own estimate, not audited income.
- Occupancy (R²≈0.16) is too noisy to model per-listing — we don't.
- Features are host-controllable only; review counts/availability excluded so every lever is something a host can actually change.