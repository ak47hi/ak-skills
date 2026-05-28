# Eval plan: <system or change name>

Owner: <name or team>
Date: YYYY-MM-DD
Status: Draft | Approved | In-flight | Completed

---

## 1. Hypothesis

<Falsifiable claim. Examples:
- "Pacer A has lower replan churn than Pacer B at 10% forecast error magnitude on p95 of tier-1 commitments."
- "Switching forecast from RMSE-tuned GBDT to pinball-tuned GBDT reduces underdelivery p95 by ≥0.5 percentage points with no smoothness regression."
- "Stochastic LP planner outperforms dual-decomposed online pacer on planner regret by ≥5% under heavy-tailed forecast error."

State pre-registered hypothesis before running the eval. Decision rule (Section 10) follows from this.>

## 2. Baselines

Mandatory:

- **Production system** — current state, named version.
- **Even-pacing** — the dumb floor.
- **Oracle planner** — uses revealed ground-truth supply; upper bound on what the planner can do.

Additional, as relevant:

- <prior model version / prior pacer>
- <competing approach from the design doc's "alternatives considered">

## 3. Datasets / simulation harness

### Strategy

<Per `references/15-simulation.md`: replay / Monte Carlo / synthetic / counterfactual planner replacement.>

### Data

- **Time window:** <e.g., 30 days of historical traffic>
- **Cohorts:** <head / body / tail decile breakdown; unseen-cohort fraction>
- **Granularity:** <e.g., per-impression discrete-event, or per-minute interval-based>

### What's held fixed, what varies

<Counterfactual planner replacement: fix forecast + traffic, vary planner.
Forecast comparison: fix planner + traffic, vary forecast.
Monte Carlo: vary forecast realization, hold planner.>

### Sim calibration check

The sim must reproduce production baselines within <tolerance> before the eval runs:

- Production pacer underdelivery on replayed traffic ≈ production-observed within ±0.5%.
- Even-pacing yields the predicted smoothness.
- Oracle has near-zero regret.

Document the calibration evidence here before drawing conclusions from the sim.

## 4. Forecast metrics (Table 1)

Per `references/91-eval-metrics.md`.

| Metric | Slice | Direction | Target |
|---|---|---|---|
| Pinball loss (q=0.5) | aggregate, per-cohort decile, per-horizon | ↓ | <…> |
| Pinball loss (q=0.9) | aggregate | ↓ | <…> |
| CRPS | aggregate, per-cohort tier | ↓ | <…> |
| Coverage at 90% | per-cohort tier | ≈ 0.90 | 0.88–0.92 |
| Bias | aggregate, per-regime | ≈ 0 | within ±2% |

Slices: head / body / tail cohort decile, per-horizon, seen vs unseen cohort, regime / time-of-day.

## 5. Planner metrics (Table 2)

| Metric | Slice | Direction | Target |
|---|---|---|---|
| Underdelivery % (mean) | per commitment | ↓ | <…> |
| Underdelivery % (p95) | per commitment | ↓ | <…> |
| Replan churn | per cohort per day | ↓ | <…> |
| Smoothness (Σ Δα²) | aggregate | ↓ | <…> |
| Allocation stability | per replan | ↓ | <…> |
| Planner regret vs oracle | aggregate | ↓ | <…> |
| SLA violation count | per commitment tier | ↓ | <…> |

Slices: across the perturbation grid (Section 7), per-tier, per-regime.

## 6. Ablation grid

Components to ablate to attribute the source of improvement (or its absence):

| Ablation | Variants |
|---|---|
| Forecast model | <baseline / candidate / candidate-without-cohort-embedding / candidate-with-RMSE-loss> |
| Pacer | <even / proportional / dual-decomposed / proposed> |
| Replan-churn control | <none / dual-smoothing / trust-region / batched-replan> |
| Uncertainty input to planner | <point / p25 / p75 / full distribution> |
| Replan cadence | <per-tick / per-5-tick / per-15-tick> |

## 7. Perturbation grid

Stress the planner across forecast quality.

| Axis | Values |
|---|---|
| Forecast error magnitude | 0%, 5%, 10%, 20%, 50% |
| Forecast bias | -10%, 0%, +10% |
| Drift scenario | stationary, gradual drift, regime shift |
| Traffic shock | 1×, 2×, 5× spike |
| New-cohort fraction | 0%, 5%, 20% |

Report the planner-metric table at each grid cell (or, for compactness, a heatmap of one summary metric).

## 8. Statistical significance protocol

- **Test:** paired bootstrap on metric differences (resample by cohort × day; recompute the metric difference per resample; 95% CI).
- **Sample size:** <e.g., 30 sim days × cohort population = N=<…>; power analysis under expected effect size of <…>>.
- **Multiple comparisons:** Bonferroni / Benjamini-Hochberg across the perturbation grid if drawing multiple conclusions.
- **Pre-registered hypotheses:** <list>. Post-hoc findings flagged as exploratory.

## 9. Reporting format

The eval emits:

- A summary paragraph naming the binding finding (the planner metric that decides).
- **Two tables** (forecast + planner) at the headline operating point.
- A heatmap or matrix of the planner-metric across the perturbation grid.
- A separate ablation table.
- The pre-registered hypothesis with the verdict (supported / refuted / inconclusive).
- A reproducibility appendix (seed, sim version, calibration evidence, code commit).

Lives in <docs/evals/<eval-id>/>; reviewed by <team>.

## 10. Decision rule (pre-registered)

<Stated before running the eval — what outcome ships the change, what outcome reverts.

Example: "Ship the candidate pacer if (a) underdelivery p95 improves by ≥0.5pp with 95% CI excluding zero, (b) replan churn does not regress by >10%, (c) at no point in the perturbation grid does any metric regress by >2x the baseline noise floor."

Stating this in advance is the protection against motivated reasoning after the eval lands. Don't soften this when results come in.>

---

## Appendix: anti-pattern check

Walked against `references/93-anti-patterns.md`:

- [ ] Both forecast AND planner tables reported (E2)
- [ ] No RMSE-only comparison (E1)
- [ ] CI + effect size in operational units (E3)
- [ ] Sim calibrated against production baselines (E4)
- [ ] Counterfactual planner replacement uses fixed traffic (E5)
- [ ] Per-cohort coverage measured if claims involve uncertainty (D4)
- [ ] MAPE not used in zero-heavy series (A5)
