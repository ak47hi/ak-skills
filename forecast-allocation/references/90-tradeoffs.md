# Tradeoffs

Load when entering **Phase 4 (ANALYZE)** in any mode. Goal: every significant choice in the design ties to a binding constraint and an accepted sacrifice.

## The discipline

A design that says "we chose X because it's standard" is not done. The justification must be:

- The **binding constraint** the choice addresses (from ELICIT).
- The **alternatives considered** and the specific constraint each failed to satisfy.
- The **sacrifice accepted** (what gets worse to make this trade).

If a choice can't be explained this way, either the design isn't finished or the choice wasn't significant. Both are fine — say so.

## Core tradeoff axes specific to forecast + allocation systems

Most decisions sit on one of these axes. Naming the axis is the first step toward reasoning about the decision rather than asserting it.

### Forecast accuracy vs planner stability

A more accurate forecast updated more often produces a planner that re-solves often. Re-solves cause allocation churn (downstream cost, behavioral effects). A less-accurate, smoother forecast produces a steadier planner.

The right point on the axis depends on the planner's churn cost: high-churn-cost planners (downstream caching, behavioral effects) prefer smoother forecasts even at some accuracy loss.

### Point forecast vs probabilistic forecast

Point forecasts are cheap, simple to consume, and ignore uncertainty. Probabilistic forecasts cost more (training, inference, integration), are required for principled hedging in the planner.

Default to probabilistic when the planner has loss asymmetry or wide forecast error; default to point when the planner is robust to forecast and the team can't operate a probabilistic pipeline.

### Per-cohort model vs global model + cohort features

Per-cohort: independent fits; ignores cross-cohort signal; fails on sparse cohorts. Global + features: shares signal; needs careful feature engineering; doesn't handle highly unique cohorts well.

Threshold: at cohort count > 10³ with non-trivial sparsity, global wins. Below that with rich history, per-cohort can win on simplicity.

### Enumerative cohort vs factorized cohort

Forecasting `N_cohorts` targets directly vs factorizing into named attribute combinations and computing cohort supply at query time.

Factorize when cohort count is combinatorial in named attributes (almost always in ad-delivery, supply-chain, scheduler-quota systems). The sacrifice: cohort forecast becomes a derived quantity, not a model output — debugging shifts to the factor model + the aggregation step.

### LP vs heuristic planner

LP: optimal under known objective, slower, principled, scales with solver. Heuristic: faster, simpler, harder to reason about under multi-objective.

Use heuristic when (a) latency budget rules out LP, (b) the heuristic is empirically within 1-2% of LP on simulation, (c) the team won't operate a solver.

### Re-solve every tick vs batched replan

Per-tick re-solve: most responsive to forecast updates, highest churn. Batched: smoother, less responsive.

Tunes on the replan-churn cost. Trust-region replan is a middle ground.

### Forecast loss = RMSE vs planner-coupled loss

RMSE-tuned forecast minimizes a generic loss. Planner-coupled loss minimizes the actual downstream cost.

Planner-coupled wins on the system metric; costs training infrastructure (often requires a differentiable planner or surrogate). RMSE wins on simplicity + portability. The right answer is usually **train on quantile loss with the quantile chosen to match the planner's asymmetry** — cheaper than full coupling, captures most of the benefit.

### Build vs buy (model + planner)

Buy: managed forecast service (Vertex AI, SageMaker Forecast), off-the-shelf solver (Gurobi). Build: custom model + custom planner.

Buy the planner solver always (no one writes their own LP solver). Buy the forecast for short-tail use cases without unusual structure. Build when cohort structure is unusual (factorized, set-based) — no managed service does this well today.

## The decision template

For each significant choice, produce a record:

```markdown
### Decision: <one-line title>

**Context.** The binding constraint that demands a decision. Include the
specific numbers (cohort count, sparsity rate, latency budget, planner
objective, SLO). Avoid filler.

**Decision.** What we're doing. One paragraph. Imperative voice.

**Alternatives considered.**
- **<Name>.** What it is, in one sentence. Why we didn't pick it: the
  specific constraint it failed to satisfy.
- **<Name>.** ...
- **<Name>.** ...

**Sacrifice accepted.** What gets worse. Be specific —
"may have higher inference cost" beats "may have tradeoffs".

**Reversal cost.** One-way door or two-way door? If one-way, what would
force a reversal and what would the reversal involve (engineer-weeks,
data migration, downtime).

**Monitoring.** Metric or signal that confirms this is working. Metric
or signal that would force the next step.
```

This is ADR-style, lifted from `system-design/references/tradeoffs.md` with the axes specific to this skill.

## Significant-choice criteria

Not every choice needs a tradeoff record. The skill records one only when at least one of:

- **One-way door.** Cohort representation, factorization scheme, primary forecast model class — switching costs are real.
- **New operational surface.** Adding a solver, a feature store, a sim harness — operational cost.
- **Deviation from team's existing stack.** New ML framework, new training pipeline.
- **Non-obvious tradeoff.** When a reasonable person would pick differently.

Two-way-door / already-team-standard / implementation-level choices don't get tradeoff records — say so and move on.

## Common decision pairings (worked examples)

### "GBDT vs Transformer for hierarchical cohort forecasting"

- Binding constraint: 50k cohorts, long-tail, weekly retrain, 10 ms inference budget per cohort.
- Decision: GBDT (LightGBM) with cohort features + cohort embeddings.
- Alternatives:
  - TFT: ruled out — long-range dependencies aren't the binding need at daily horizon; training cost not justified.
  - DeepAR: ruled out — overkill for the variance structure; team doesn't have GPU ops.
- Sacrifice: ceiling lower than transformer if long-range dependencies become important.
- Reversal: two-way door; can switch model family if planner metric saturates.

### "Per-tick LP re-solve vs dual-decomposed online pacer"

- Binding constraint: 10⁵ concurrent commitments, sub-second per-impression decisions, replan churn must be ≤3/cohort/day.
- Decision: dual-decomposed online pacer.
- Alternatives:
  - Per-tick LP: latency unacceptable at 10⁵ commitments × per-impression scale.
  - Forecast-proportional: doesn't naturally handle multi-commitment fairness.
- Sacrifice: dual updates have lag; transient under-delivery during regime shifts.
- Reversal: two-way door for algorithmic choice; one-way door for the dual-variable storage schema.

### "Point forecast vs quantile forecast"

- Binding constraint: planner has 3× asymmetric underdelivery cost.
- Decision: quantile forecast at q ∈ {0.1, 0.5, 0.9}; planner consumes p25 for pacing.
- Alternatives:
  - Point forecast: doesn't expose the variance the planner needs to hedge.
  - Bayesian posterior: too expensive for current ops budget; quantile gives 80% of the win.
- Sacrifice: 3× training cost, slightly more complex inference.
- Reversal: two-way door.
