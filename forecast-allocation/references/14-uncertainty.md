# Uncertainty

Load when the prompt mentions uncertainty, quantiles, calibration, confidence intervals, Bayesian, conformal prediction, drift detection, or propagating uncertainty into the planner.

## Why this matters

A planner that consumes a point forecast as if it were ground truth is brittle to forecast error. The whole reason to have probabilistic forecasts is that the planner can hedge — pace conservatively when forecast is wide, aggressively when it's tight. This requires (a) the forecast to produce usable uncertainty, and (b) the planner to consume it.

Both halves often fail in practice. The forecast produces uncalibrated intervals, or the planner ignores them. The fix is to evaluate calibration as a first-class metric (`91-eval-metrics.md`) and to wire uncertainty into the planner explicitly (`13-allocation.md`).

## Three things "uncertainty" can mean

1. **Aleatoric.** Irreducible noise in the data-generating process. Same input, different outcomes. Setting a tight interval here is a calibration error.
2. **Epistemic.** What we don't know because we have limited data. Sparse-cohort forecasts have huge epistemic uncertainty. Reducible by more data.
3. **Distributional / drift.** The future doesn't come from the same distribution as the training data. Not reducible by more historical data; reducible by monitoring + adaptation.

Most production failures are (3) silently misclassified as (1) or (2). Drift monitoring is a first-class system component, not an afterthought.

## Producing usable uncertainty

### Quantile regression

Train K models, one per target quantile, each with pinball loss `L_q(ŷ, y) = max(q(y−ŷ), (q−1)(y−ŷ))`. GBDT (`LightGBM` with `objective=quantile, alpha=q`) is the strongest default. Cheap, calibrated empirically with enough data, no distributional assumption.

Output: per-cohort, per-horizon quantile predictions `ŷ_q ∀ q ∈ Q`. The planner can consume any quantile directly.

### Bayesian / probabilistic models

Output a posterior over forecasts. Bayesian state-space (BSTS), hierarchical Bayes, deep Bayesian (DeepAR, MC dropout, deep ensembles). Strong when:

- Sample size per cohort is small (Bayesian shrinkage matters).
- Interpretable posterior decomposition matters.
- Downstream planner consumes samples (stochastic LP).

Cost: inference time, debugging surface, expertise.

### Ensembles

Train N models (different seeds, splits, hyperparameters); use the ensemble distribution as the predictive distribution. Strong empirically; computationally expensive at inference time. Approximations: deep ensembles, snapshot ensembles, multi-quantile single model.

### Conformal prediction

Wraps any point forecaster to produce intervals with finite-sample coverage guarantees. Split-conformal is the simplest:

1. Train point forecast on training set.
2. Compute residuals `e_i = |ŷ_i − y_i|` on a held-out calibration set.
3. Predictive interval for new x: `ŷ ± Quantile_{1−α}(e)`.

Adaptivity in tabular forecasting often needs CQR (conformalized quantile regression) — start with quantile predictions, conformalize them. Strong when calibration on out-of-distribution is critical.

Caveat: conformal coverage is *marginal* (averaged over all inputs) — per-cohort coverage can still be miscalibrated. CQR + cohort-conditional calibration helps; verify per-cohort.

## Calibration

A 90% predictive interval is calibrated if `P(y ∈ [ŷ_low, ŷ_high]) = 0.90` over the relevant population. Production forecasts are usually miscalibrated; check explicitly.

### Diagnostics

- **PIT (probability integral transform) histogram.** For each test point, compute `PIT = F̂(y)` (CDF of the forecast evaluated at the truth). PITs should be Uniform[0, 1]. Histogram bin frequencies reveal miscalibration shape (over-confident: U-shape; biased: skewed).
- **Reliability diagrams.** For each predicted quantile `q`, plot the empirical coverage. Calibrated forecasts lie on the diagonal.
- **CRPS** (continuous ranked probability score). Strictly proper scoring rule for the full predictive distribution. Lower is better. Compares distributional forecasts apples-to-apples.

### Recalibration

If calibration is off but the rank-ordering is right, recalibrate post-hoc. Isotonic regression on PIT values. Cheap; recover calibration without retraining.

## Drift detection + adaptation

Drift is the dominant failure mode of production forecasts. Three monitors:

- **Feature drift.** PSI, KS test on input features vs training distribution. Cheap; catches the easy cases.
- **Prediction drift.** Distribution of `ŷ` vs training-time `ŷ`. Catches changes in input that don't fail feature-drift checks.
- **Performance drift.** Forecast metric (calibration, CRPS, planner-metric proxy) drifting from baseline. Requires labels; lagged by label-availability delay.

Adaptation:

- **Trigger retraining** on drift signal.
- **Exponential weighting** of recent observations during training.
- **Online learning** (with care — see `10-forecast.md`).

## Propagating uncertainty into the planner

Three patterns:

1. **Quantile-plan.** Planner consumes a single conservative quantile (e.g. p25 of supply, p75 of demand). Cheapest; asymmetric; loses information.
2. **Scenario-based.** Sample K trajectories from the predictive distribution; planner solves a stochastic LP over scenarios. Highest fidelity; expensive.
3. **Chance-constrained.** Reformulate constraints in probability. Tractable for Gaussian forecasts; less so otherwise.

`13-allocation.md` covers the solver side.

## Loss asymmetry

If the planner penalizes under-delivery 5× more than over-delivery, the forecast should be biased low. Two ways:

- **Asymmetric quantile loss.** Use a high quantile (e.g. q=0.8) instead of the median to bias upward (so over-delivery becomes more likely than under).
- **Planner-coupled loss.** Backprop through a differentiable planner. Justified when the loss asymmetry varies across cohorts and time and the planner is differentiable.

## Anti-patterns (cross-ref `93-anti-patterns.md`)

- Point forecast consumed as ground truth by a brittle planner.
- Reporting "we have intervals" without measuring calibration.
- Bayesian posterior summarized to a point estimate before the planner sees it (defeats the purpose).
- Stationary assumption with no drift monitor.
- Per-cohort coverage assumed equal to marginal coverage (often false).
- RMSE used to compare a probabilistic forecast vs a deterministic one (apples-oranges; use CRPS).
