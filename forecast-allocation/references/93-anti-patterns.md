# Anti-patterns

Load during **Phase 6 (OUTPUT)**. Walk every pattern against the artifact; each one that fires is fixed in the artifact or called out as an Open Question.

Each entry: **symptom** (how it shows up), **why bad** (the failure mode), **ask instead** (the right question to redirect to).

## Modeling

### A1. One-model-per-cohort at scale

**Symptom.** Architecture diagram has "Train N forecast models, one per cohort/segment/ad-group" with N ≥ ~10³.

**Why bad.** Most cohorts have insufficient history for classical methods to converge. Cross-cohort signal is wasted. Operational cost (training, monitoring, rollback) scales linearly in N. Unseen cohorts have no model.

**Ask instead.** What is the cohort cardinality and what fraction has ≥ 30 observations? If sparse, use a global model with cohort features + cohort embeddings, or a factorized representation. See `12-cohort.md`.

### A2. Cohort ID as a categorical / one-hot / embedding-key feature

**Symptom.** A categorical encoder or embedding layer keyed on `cohort_id`.

**Why bad.** The model memorizes per-cohort offsets without exploiting cohort *structure*. Two cohorts differing in one attribute look unrelated. Cannot generalize to unseen cohort IDs.

**Ask instead.** Decompose the cohort into its constituent attributes (market, locale, device, audience, …) and condition the model on those. For genuine sets, use DeepSets or Set Transformer over member embeddings. See `12-cohort.md`.

### A3. Naive lookup table forecast

**Symptom.** "Forecast = historical average of this cohort's deliveries last N weeks, same day-of-week."

**Why bad.** No extrapolation, no drift handling, no uncertainty. Strong as a baseline; fails as a system. Will look fine until the regime shifts.

**Ask instead.** Use the lookup as the *baseline* in eval, not the forecast. Build a model with calendar / lag / cohort features that consistently beats the lookup on the planner metric. See `10-forecast.md`.

### A4. Climbing the model ladder without justification

**Symptom.** "We chose a transformer / DeepAR / Bayesian neural net." But the binding constraint doesn't demand it.

**Why bad.** Higher infrastructure cost, longer training, harder debugging, smaller pool of engineers who can operate it. GBDT is the M5-winning default for hierarchical forecasting; transformers usually don't win on these problems.

**Ask instead.** What constraint forces the climb past GBDT? Long-range dependencies that trees can't capture? Multi-modal features? If neither, default to GBDT. See `10-forecast.md` model ladder.

### A6. Foundation-model-skip without comparing zero-shot baseline

**Symptom.** ML team designs a custom GBDT / transformer; never benchmarks against a foundation model (Chronos / TimesFM / Moirai) for cold-start cohorts or unseen-cohort generalization.

**Why bad.** Time-series foundation models occasionally beat fine-tuned custom work on unseen cohorts and are *free to evaluate* — pretrained weights, zero-shot inference. Skipping the comparison leaves a known cheap baseline unmeasured; designs that climb the ladder past rung 4 without this check are claiming a benefit they haven't verified.

**Ask instead.** Run Chronos / TimesFM / Moirai zero-shot as a comparison baseline. Justify the custom-model investment only if it meaningfully beats the foundation model on the planner metric, not just RMSE. See `10-forecast.md` rung 6.5 and `99-citations.md`.

### A5. MAPE / wMAPE as training loss

**Symptom.** `loss=mape` in the trainer config.

**Why bad.** Biased downward (favors under-prediction), unstable near zero, not a proper scoring rule. Optimizing it produces a biased forecast.

**Ask instead.** Train on MAE / MSE / pinball; report wMAPE only if stakeholders demand it. See `91-eval-metrics.md`.

## Loss / objective alignment

### B1. RMSE-tuned forecast feeding a loss-asymmetric planner

**Symptom.** Forecast is trained on MSE; the planner penalizes under-delivery 3× more than over-delivery.

**Why bad.** Symmetric forecast loss optimizes for the wrong tradeoff. The forecast is "best" in a sense that doesn't matter for the planner.

**Ask instead.** Train with pinball loss at a quantile chosen to match the planner's asymmetry, or planner-coupled loss. See `10-forecast.md` and `14-uncertainty.md`.

### B2. Planner-unaware forecast development

**Symptom.** Forecast team and planner team work in isolation. Forecast ships when forecast metrics improve.

**Why bad.** Forecast improvements don't translate to system improvements. Planner amplification effects go undetected.

**Ask instead.** Co-design or at minimum co-evaluate. Every forecast PR shows planner metrics from a sim run. See `91-eval-metrics.md` cross-table rules.

### B3. Optimizing point forecast when planner consumes a distribution

**Symptom.** Probabilistic planner (stochastic LP, chance-constrained) downstream; forecast emits a point.

**Why bad.** Planner can't hedge. It either ignores its own uncertainty machinery or guesses uncertainty from elsewhere.

**Ask instead.** Match the forecast output shape to what the planner consumes. Quantile forecast for quantile planner; full distribution for stochastic LP. See `14-uncertainty.md`.

## Planner / allocation

### C1. Even-pacing with no justification

**Symptom.** "We pace evenly across the day."

**Why bad.** Defensible only when traffic is uniform or forecast variance is so high the forecast is useless. Otherwise it under-delivers in cheap-traffic windows and over-delivers in expensive ones.

**Ask instead.** What's the variance of traffic across the pacing window? If non-trivial, use forecast-proportional or dual-decomposed pacing. See `11-pacing.md`.

### C2. Per-tick LP re-solve from scratch under heavy load

**Symptom.** Planner re-solves a 10⁵-variable LP every minute.

**Why bad.** Latency blowout. No warm-start exploitation. Replan churn is uncontrolled.

**Ask instead.** Warm-start the LP. Trust-region replan. Or switch to dual-decomposed online pacer. See `11-pacing.md` and `13-allocation.md`.

### C3. No replan-churn control

**Symptom.** Per-tick re-solve. No smoothing on duals. No trust region. No hysteresis.

**Why bad.** Under noisy forecasts, allocation oscillates. Downstream caches invalidate. Behavioral effects (e.g., advertisers seeing wildly different delivery curves) emerge.

**Ask instead.** Measure replan churn as a first-class metric. Pick one of: dual-variable smoothing / hysteresis / batched replan / trust-region. See `11-pacing.md`.

### C4. MILP when LP-relaxation is fine

**Symptom.** "Decisions must be integer," so the planner is an MILP.

**Why bad.** NP-hard. Solve time can blow up unpredictably. LP relaxation + rounding usually within 1% of MILP on these problems.

**Ask instead.** Benchmark LP-relaxation + rounding vs MILP on a representative subset. If within tolerance, ship LP. See `13-allocation.md`.

### C5. RL planner without a calibrated sim

**Symptom.** "We trained an RL agent to allocate."

**Why bad.** RL can't be safely deployed without offline validation, which means a calibrated simulator, which is usually missing. Silent failures in production.

**Ask instead.** What's the analytical baseline (dual-decomposed LP)? RL must beat it meaningfully in a calibrated sim before deployment. See `13-allocation.md` and `15-simulation.md`.

## Uncertainty + drift

### D1. Point forecast consumed as ground truth

**Symptom.** Planner uses `ŷ` as if `y = ŷ`.

**Why bad.** Brittle to forecast error. Replan churn under noise. Mis-allocates against worst-case realizations.

**Ask instead.** Produce quantiles or distributional forecast. Have the planner hedge. See `14-uncertainty.md`.

### D2. "We have intervals" without measuring calibration

**Symptom.** Forecast emits 90% intervals. No PIT or coverage plot in the eval.

**Why bad.** Uncalibrated intervals are worse than no intervals — they create false confidence. Production planners trust the band and the band lies.

**Ask instead.** Measure PIT histogram, per-quantile coverage, CRPS. Recalibrate if off. See `14-uncertainty.md`.

### D3. Stationary assumption with no drift monitor

**Symptom.** Model trained once, no retraining trigger, no feature/prediction/performance drift dashboard.

**Why bad.** Drift is the dominant failure mode of production forecasts. By the time anyone notices, the planner has been miscalibrating for weeks.

**Ask instead.** Wire in feature drift (PSI/KS), prediction drift, and a performance-drift monitor with a retraining trigger. See `14-uncertainty.md`.

### D4. Per-cohort coverage assumed equal to marginal coverage

**Symptom.** "Conformal gives us 90% coverage."

**Why bad.** Marginal coverage averages across the whole population. The 10% tail of miscovered cases could all be the high-stakes cohorts.

**Ask instead.** Verify per-cohort (or per-tier) coverage. If miscalibrated, use group-conditional conformal. See `14-uncertainty.md`.

### D5. Uncalibrated deep ensemble reported as "probabilistic forecast"

**Symptom.** A 5-model deep ensemble produces a mean + variance per forecast; the variance is consumed by the planner as if it were a calibrated predictive distribution. No PIT, no per-quantile coverage, no CRPS in the eval.

**Why bad.** Ensemble variance is *a* proxy for uncertainty, not *the* calibrated predictive distribution. Deep ensembles are routinely over-confident on training-like inputs and under-confident out-of-distribution. A planner that trusts the variance as a calibrated quantile mis-hedges in both directions — and you find out only when production underdelivery spikes.

**Ask instead.** Measure PIT histogram and per-quantile coverage on the ensemble distribution; report CRPS, not just ensemble variance. If miscalibrated, wrap with CQR (`14-uncertainty.md`) — the deep-ensemble + CQR composite gives both adaptivity and distribution-free coverage. Cite Lakshminarayanan 2017 for the ensemble, Romano 2019 for CQR.

## Evaluation

### E1. RMSE-only reporting

**Symptom.** A single number, RMSE, in the eval write-up.

**Why bad.** RMSE doesn't capture calibration, doesn't capture the planner's amplification, doesn't capture per-cohort tail behavior.

**Ask instead.** Two tables (forecast + planner), sliced by cohort decile / horizon / regime. See `91-eval-metrics.md`.

### E2. Forecast-only reporting (no planner metrics)

**Symptom.** The eval has forecast metrics. The planner is "outside the scope."

**Why bad.** The whole point of this skill is that forecast quality must be measured at the planner output. Forecast-only eval can pick the wrong winner.

**Ask instead.** Add a sim run with planner metrics. See `15-simulation.md` and `91-eval-metrics.md`.

### E3. "X% better" without CI or effect size

**Symptom.** "Our new forecast is 4.2% better."

**Why bad.** No confidence interval (could be noise), no effect size in operational units (could be unimportant), no baseline definition (4.2% relative to what).

**Ask instead.** Paired bootstrap CI, effect size in $ / delivery / churn-events, named baseline. See `91-eval-metrics.md`.

### E4. Sim that doesn't reproduce production baselines

**Symptom.** Sim says even-pacing yields 1% underdelivery; production observation is 4%.

**Why bad.** The sim is broken. Any conclusion drawn from it about new methods is unreliable.

**Ask instead.** Calibrate the sim until it reproduces known facts (production pacer metrics, even-pacing on the same traffic). Then trust it. See `15-simulation.md`.

### E5. Pacer A/B with unfixed traffic

**Symptom.** Pacer A ran on Monday's traffic, Pacer B ran on Tuesday's.

**Why bad.** Traffic varies day-to-day. Differences attributed to the pacer might be traffic variance.

**Ask instead.** Counterfactual planner replacement (fix traffic, swap planner). See `15-simulation.md`.

## Operational

### F1. Forecast retraining cadence the team can't sustain

**Symptom.** "Retrain hourly" with a 2-person team and no MLOps pipeline.

**Why bad.** Will go stale. The promised cadence won't actually run.

**Ask instead.** What can the team sustain? Pick the cadence that gets operated. See `00-elicitation.md` dimension 7.

### F2. Model that the on-call can't debug

**Symptom.** A bespoke deep model with no per-prediction explainability, opaque feature pipeline.

**Why bad.** At 3am during a delivery emergency, on-call needs to know which feature blew up. Black-box forecasts make incident response impossible.

**Ask instead.** Per-prediction feature importance, audit logs, a way to inspect "why did this cohort's forecast change."

### F3. No fallback when forecast fails

**Symptom.** Single forecast pipeline; if it breaks, the planner has nothing.

**Why bad.** Forecast pipelines do break (data quality, retraining failures, schema changes). The planner needs a degradation mode.

**Ask instead.** Fallback to last-known-good forecast or even-pacing on failure. Document the fallback in the design.
