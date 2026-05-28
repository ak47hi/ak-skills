# Forecasting

Load when the prompt mentions forecasting, demand prediction, supply prediction, hierarchical forecasts, or factorized representations.

## Math framing

Forecast `ŷ_{c,t+h}` for cohort `c` at horizon `h` given history `y_{c,≤t}` and features `x_{c,t}`. Three things to fix before picking a model:

- **Output shape.** Point (`ŷ ∈ ℝ`), quantiles (`ŷ_q for q ∈ {0.1, 0.5, 0.9}`), or full predictive distribution. The planner's needs decide this.
- **Loss.** Squared error, absolute, quantile (pinball), CRPS, or planner-coupled (e.g. asymmetric pinball weighted by the planner's underdelivery cost).
- **Conditioning.** Per-cohort independent, hierarchical (cohort within parent), or global model with cohort features.

A forecast minimizing the wrong loss is worse than a worse model on the right loss. Settle the loss first.

## Model ladder (climb only when the rung below is justified to fail)

1. **Seasonal-naive / simple exponential smoothing.** The baseline. Always fit it. Beating it on the planner metric, not just RMSE, is the bar.
2. **ETS / ARIMA / Theta.** Classical statistical methods. Strong on individual short series with clean seasonality. Per-cohort fitting; doesn't share signal across cohorts.
3. **Prophet.** Strong default for medium-sparsity series with holiday/seasonality structure. Robust to missing data. Weak on highly noisy or very short series.
4. **GBDT (LightGBM, XGBoost, CatBoost) with lag/calendar/cohort features.** The strongest default for hierarchical forecasting at modest scale. Trains one global model, conditions on cohort features, scales to 10⁵-10⁶ cohorts. M5 competition winning approach. Use quantile loss directly (`objective=quantile, alpha=q`) for quantile outputs.
5. **DeepAR / N-BEATS / TFT (Temporal Fusion Transformer).** Justified when (a) you need long-range dependencies a tree can't capture, (b) you need cross-cohort attention, (c) you have rich exogenous features (text, image, graph). Cost: training pipeline, GPU, harder to debug.
6. **Bayesian state-space / hierarchical Bayes.** Justified when (a) you genuinely need posterior uncertainty (not just intervals), (b) hierarchical structure is load-bearing and sample size per cohort is small, (c) interpretable shrinkage matters. Cost: inference time, expertise.
7. **Ensemble.** Combine 2-3 of the above. Almost always wins on point + calibration, almost always loses on infra cost.

**Default the design at level 4 (GBDT) unless an explicit constraint forces a climb.** Most teams pick level 5/6 prematurely.

## Hierarchical forecasting

When cohorts have a hierarchy (region > city > zip, brand > product > SKU, campaign > line-item > ad-group):

- **Bottom-up.** Forecast leaves, aggregate. Lossy on noisy leaves; loses cross-leaf signal.
- **Top-down.** Forecast roots, disaggregate by historical proportions. Loses leaf-specific signal; struggles with new leaves.
- **MinT / reconciliation.** Forecast every level independently, reconcile so children sum to parents. The classical choice; needs covariance estimation.
- **Global hierarchical model.** One model trained with hierarchy as features. The modern default.

If the planner consumes only at the leaf level, **forecast at the leaf level** and tolerate the noise — aggregation hides errors but doesn't fix them.

## Factorized forecasting

When cohort count is combinatorial (e.g. cohorts are sets of ad-groups eligible for an impression), do not forecast `2^N` cohorts directly. Factorize:

```
impression_volume(segment, slot, t) = base_supply(segment, slot, t) × eligibility(adgroup, segment, slot, t)
cohort_supply(adgroup, t) = Σ_{segments × slots} impression_volume(s, l, t) · eligibility(adgroup, s, l, t)
```

Forecast the **base supply per (segment, slot, time)** — a tractable cardinality. Compute cohort-level supply at query time by summing over the eligible (segment, slot) combinations.

This is the load-bearing trick for guaranteed-ad-delivery systems: it converts a combinatorial forecasting problem into a tractable one without losing accuracy.

## Loss functions

| Loss | Use when |
|---|---|
| MSE (`(ŷ-y)²`) | Symmetric cost, point forecast, no quantile downstream. Rarely the right choice for allocation. |
| MAE (`|ŷ-y|`) | Symmetric cost, more robust to outliers than MSE, point forecast. |
| Pinball / quantile loss (`max(q(y-ŷ), (q-1)(y-ŷ))`) | Planner consumes quantiles. The default for any allocation that hedges against under- or over-delivery. |
| Asymmetric pinball (different `q` for under vs over) | Planner has asymmetric cost (under-delivery >> over-delivery). |
| CRPS | Continuous predictive distribution; planner consumes the full distribution. Strictly proper. |
| MAPE / wMAPE | Reporting only — biased estimators, unstable near zero. Never train on these. |
| Planner-coupled loss | Backprop through the planner (differentiable LP / barrier method). Justified when planner cost is the metric and the joint system is trainable. |

## Calendar, regimes, exogenous features

- Day-of-week, holiday, payday, promotional calendar — first-order signal in nearly every forecast.
- Regime indicators (launch, peak season, market-wide events) — usually beats trying to model the regime implicitly.
- Lag features (`y_{t-1}, y_{t-7}, y_{t-28}`) — the bread and butter of GBDT-based forecasts.
- Cohort embeddings — see `12-cohort.md`.

## Multi-horizon

Two approaches:

- **Direct.** One model per horizon (or multi-output model). No error accumulation; expensive to train if horizons are many.
- **Recursive.** One model, feed predictions back. Error accumulates; cheap.

The planner usually consumes multiple horizons simultaneously (full forward curve over the pacing horizon). Direct multi-output with shared trunk is the modern default.

## Online vs batch

- **Batch retrain** (daily/weekly): the default. Simpler to operate, fine for drift on the order of days.
- **Online learning** (incremental updates per batch of observations): justified when (a) drift is faster than retrain cadence, (b) label lag is short, (c) team has the infrastructure to operate it. Adds debugging surface; reject by default.

## Evaluation hand-off

`91-eval-metrics.md` carries the metric table. Two non-negotiables for a forecast that feeds a planner:

1. Report **both** forecast metrics (point + calibration) and planner metrics from a sim run (`15-simulation.md`).
2. The forecast that wins on planner metrics ships, even if a different model wins on RMSE.

## Anti-patterns (cross-ref `93-anti-patterns.md`)

- One model per cohort at high cohort count + sparse history (data-efficiency failure).
- Cohort ID as a categorical feature (`12-cohort.md` for the right approach).
- RMSE-only training when the planner consumes quantiles.
- MAPE/wMAPE as a training loss (biased, unstable near zero).
- Stationary assumption with no drift monitor.
- Climbing the model ladder past level 4 (GBDT) without naming the constraint that forces it.
