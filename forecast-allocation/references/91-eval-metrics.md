# Evaluation metrics

Load when entering **Phase 5 (EVALUATE)** or when the mode is EVALUATE.

## The two-table rule

Every eval reports **two tables**, always:

1. **Forecast metrics** — measured on the forecast alone, on a held-out test window.
2. **Planner metrics** — measured on the joint forecast + planner system, in simulation (`15-simulation.md`).

A new forecast can win Table 1 and lose Table 2 — that's the planner-coupling effect this skill exists to surface. **The planner table picks the winner.**

## Table 1: Forecast metrics

### Point metrics

| Metric | Formula | Use when |
|---|---|---|
| **RMSE** | `√(mean((ŷ−y)²))` | Symmetric cost, point forecast. Magnitudes interpretable. Penalizes outliers heavily. |
| **MAE** | `mean(|ŷ−y|)` | Symmetric cost, more robust to outliers than RMSE. |
| **MAPE** | `mean(|ŷ−y|/|y|)` | Reporting only — biased downward, blows up near zero. Don't train on this. |
| **wMAPE** | `Σ|ŷ−y| / Σ|y|` | Reporting; more stable than MAPE; still biased. |
| **Bias** | `mean(ŷ−y)` | Always report. Systematic over/under-forecasting matters for the planner. |
| **Per-quantile error** | Same as above on `ŷ_q` | When a specific quantile is what the planner consumes. |

### Probabilistic metrics

| Metric | Formula | Use when |
|---|---|---|
| **Pinball loss** at quantile q | `mean(max(q(y−ŷ_q), (q−1)(y−ŷ_q)))` | Forecast emits quantiles. The right loss for quantile training. |
| **CRPS** | `∫(F̂(z) − 1{y≤z})² dz` | Forecast emits a full predictive distribution. Strictly proper. |
| **Coverage at level α** | `P(y ∈ [ŷ_low, ŷ_high])` | Verify prediction intervals are calibrated. Should equal `1−α`. |
| **PIT histogram** | distribution of `F̂(y)` | Visualizes calibration shape. Uniform = calibrated. |
| **Reliability curves** | empirical vs predicted quantiles | Per-quantile calibration. |

### Reporting cuts

Don't just report aggregate — slice by:

- **Per-cohort decile** (head, body, tail). Tail-cohort error is where most production failures live.
- **Per-horizon.** Multi-horizon forecasts often degrade with horizon; the table shows where.
- **Seen vs unseen cohort.** Unseen-cohort metric on a held-out set is the generalization measurement.
- **By regime / time-of-day.** Forecasts often work great in normal hours and break at peak.

## Table 2: Planner metrics

These come from the simulator (`15-simulation.md`), not from offline forecast evaluation.

| Metric | Definition | Use when |
|---|---|---|
| **Underdelivery %** | `(D − delivered) / D` per commitment, then summary stats (mean, p95) | Always. The primary SLA in guaranteed-delivery problems. |
| **Underdelivery rate** | Fraction of commitments missing target by > X% | Always — tail behavior matters more than the mean. |
| **Pacing smoothness** | `var(α_t) / mean(α_t)²` or `Σ(α_t − α_{t-1})²` | When smoothness is in the SLO or downstream amplifies variance. |
| **Replan churn** | replans per cohort × magnitude of allocation change per replan | When churn has downstream cost (caching, behavioral effects). |
| **Allocation stability** | `‖α_{plan t} − α_{plan t-1}‖ / ‖α_{plan t-1}‖` averaged over replans | Same purpose as churn, framed per-replan. |
| **Planner regret** | `(opt cost under truth) − (planner cost under forecast)` | When the system has an oracle benchmark; quantifies how much forecast error costs. |
| **SLA violations** | count or rate of commitments missing by > X% | Hard contract; tail not mean. |
| **Fairness metric** | per the design (proportional fairness, max ratio, min-floor violation) | Multi-commitment systems. |
| **Revenue / cost** | per the planner's objective | When economic outcome is the metric. |

### Reporting cuts

- Across the **forecast-error perturbation grid** (0%, 5%, 10%, 20%, 50%). Where does the planner break?
- Across **drift scenarios** (stationary, gradual, regime shift).
- Across **traffic shocks** (1×, 2×, 5× spike).
- Per **commitment tier / priority class** (premium vs standard).

## Comparison rules

### Baselines (mandatory)

- **Production system** (or stated current state). The thing being improved.
- **Even-pacing / naive baseline.** The floor; if the new system doesn't beat this, abandon.
- **Oracle planner** (knows ground-truth supply, optimal allocation). Upper bound; the regret denominator.

### Significance

For paired comparisons (same traffic, two planners), use:

- **Paired bootstrap** (resample by cohort, recompute the metric difference, 95% CI). Robust to non-normal metric distributions.
- **Permutation test** when sample size is small.

Don't report a "the new system wins" without a CI that excludes zero.

### Effect size

Statistical significance is necessary, not sufficient. Report **effect size in operational units**: "0.4% absolute reduction in underdelivery, $X revenue impact at production scale." A statistically significant 0.001% improvement is not a ship signal.

## Cross-table reading

Common patterns:

| Table 1 | Table 2 | What it means |
|---|---|---|
| New forecast wins RMSE | New forecast wins planner metrics | Clean win; ship. |
| New forecast wins RMSE | New forecast loses planner metrics | Forecast variance went up or bias shifted; planner can't hedge. Investigate calibration. |
| New forecast loses RMSE | New forecast wins planner metrics | Common when new forecast has better calibration; planner cares about that more than RMSE. **Ship anyway** — the planner table picks. |
| New forecast wins calibration | Planner metric unchanged | Planner isn't actually consuming the uncertainty. Wire the uncertainty in or stop measuring calibration. |

## Ablations (in EVALUATE mode)

- Model component ablations (cohort embedding, factorized, calendar features).
- Planner component ablations (with/without uncertainty input, with/without replan-churn control).
- Hyperparameter sensitivity (replan cadence, dual-update step size, smoothness penalty).
- Forecast-horizon ablation (which horizons does the planner actually use?).

## Reporting format

Two markdown tables (Table 1, Table 2), one perturbation-grid heatmap if EVALUATE mode, a paragraph naming the binding finding. **Lead with the planner table** — that's what picks the winner.

## Anti-patterns (cross-ref `93-anti-patterns.md`)

- RMSE-only reporting.
- Forecast-only reporting (no planner table).
- Aggregate-only reporting (no per-cohort-tail or per-perturbation slice).
- "X% better" without CI or effect size.
- A/B tests using different traffic (counterfactual planner replacement requires fixed traffic).
- Reporting MAPE on demand with frequent zero values (blows up).
