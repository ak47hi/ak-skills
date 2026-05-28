# Elicitation

Load at the start of every request. Decides whether to skip, ask, or propose-and-go before producing anything.

## The gate

Constraints come first. A forecast model picked with zero numbers is guessing. A planner picked without the SLO it has to meet is a hallucination. **Inferred constraints are fine — flag them as assumptions** — but design with no anchors at all is not.

This is the same discipline as the `system-design` skill: numbers and structure before architecture. Here the "structure" piece also matters because cohort cardinality and sparsity reshape the model family before any number does.

## Seven dimensions

For every request, these are the minimum the design needs. They map directly to the OUTPUT sections, so missing dimensions become "Open questions" in the artifact.

### 1. Forecast horizon + cadence

- **What** is being forecast: supply (impressions, capacity, jobs), demand (clicks, orders, requests), or both. Is it a count, a rate, a quantile, a distribution?
- **Horizon**: how far ahead. 1 hour vs 1 day vs 30 days are different model families.
- **Cadence**: how often the forecast refreshes. Hourly retrain is a different system from weekly retrain.
- **Grain**: per-cohort, per-cohort × hour, per-cohort × placement × hour.

A forecast at the wrong grain pollutes the planner — aggregate-then-allocate vs forecast-at-grain is a real choice, and the right one depends on sparsity.

### 2. Cohort cardinality and sparsity

- **Total cohorts.** 10³, 10⁵, 10⁷?
- **Active cohorts** in any given window. Long tail vs uniform.
- **Sparsity rate.** What fraction of cohorts have ≥30 observations in the training window? Sparsity drives representation more than scale.
- **Unseen-cohort rate.** At serving time, what fraction of cohorts the model sees were not in the training window? Decides whether memorization-style models even work.

Anchor: at ~10³ cohorts with rich history, per-cohort models are defensible. At ~10⁵ with 70%+ sparsity, only compositional representations work.

### 3. Planner objective and constraints

This is the most-missed dimension and the single biggest cause of "forecast accuracy improved but the system got worse" stories.

- **Objective.** What does the planner *minimize* or *maximize*? Underdelivery? Cost? Revenue subject to delivery? Smoothness?
- **Hard constraints.** Budget caps, delivery commitments, fairness floors, capacity ceilings.
- **Soft costs.** Replan churn (oscillation cost), allocation volatility (cost of moving demand between supply sources), pacing smoothness.
- **Loss asymmetry.** Is over-delivery as costly as under-delivery? Almost always not.

**A forecast loss that mirrors the planner's loss outperforms an RMSE-tuned forecast on the joint system.** This is the single load-bearing principle of the skill.

### 4. SLO on the joint system

- Underdelivery percentage (e.g. ≤2%).
- Allocation stability (max allocation change per replan tick).
- Replan churn ceiling (replans per cohort per day).
- Smoothness (variance of per-tick delivery).
- Tail percentiles, not means — "p95 underdelivery ≤5%" is a different system from "mean ≤2%."

### 5. Data shape

- History depth (days/weeks/years).
- Granularity (raw events vs pre-aggregated).
- Label availability lag (when does the truth land — same tick, +1 day, +7 days?). Decides feasibility of online learning.
- Missingness pattern (random vs censored — censoring is when missing data correlates with the outcome).
- Drift signal (stationary? seasonal? trended? abrupt regime shifts?).

### 6. Latency budget for inference + planning

- Forecast inference SLA (per-cohort, per-batch).
- Planner solve budget (per-tick).
- End-to-end "forecast → plan → act" budget.

A 50 ms planner budget rules out most LP solvers and forces closed-form / proportional / precomputed-dual approaches. A 1-minute budget opens the door to MILP and stochastic programming.

### 7. Operational reality

- Team size + on-call rotation.
- Existing stack (do they have a feature store? a planner already? a sim harness?).
- Retraining cadence the team can sustain.
- Who owns the model, who owns the planner, who owns the integration.

A model that needs nightly retraining by a 2-person team that doesn't have an MLOps pipeline is a model that will go stale. Boring is often correct.

## Decision rules: skip, ask, propose-and-go

| Signal in the prompt | Action |
|---|---|
| All seven dimensions stated or derivable | Skip ELICIT. Go to ROUTE. |
| Narrow targeted question ("factorize cohort forecast or per-cohort at 50k cohorts?") | Skip the full elicitation; confirm the binding constraint inline in one sentence, then answer narrowly. |
| Three or fewer dimensions missing AND defaults are uncontroversial | **Propose-and-go**: state inferred defaults in a single short block, then proceed. |
| Four or more dimensions missing OR the prompt is broadly vague ("design our forecasting system") | Ask ONE batched round. Number the questions. Do not iterate. |

**One round, not three.** Every round of clarifying questions burns user trust. If the answer to round 1 is still vague, infer the rest and flag the inferences in the design.

## Propose-and-go template

> Treating this as: ~50k active cohorts (long-tail; ~30% have ≥30 obs/week), daily forecast horizon, hourly refresh, planner minimizes underdelivery subject to a 1% smoothness ceiling and ≤3 replans/cohort/day, 10 ms forecast inference budget, weekly retrain by a 3-person team on PyTorch + Ray. Proceeding — correct any of these.

Short, numbered, replaceable. Don't dress it up.

## What NOT to ask

- The model family (GBDT vs DeepAR vs Bayesian) — that's the skill's job, not the user's.
- The planner solver (LP vs MILP vs heuristic) — same.
- The framework, the cloud, the language — implementation, not constraint.
- Multiple-choice questions that bias the answer ("Do you want a transformer or a GBDT?" — ask about the data, not the model).

## Archetype detection in ELICIT

After the seven dimensions are pinned (or inferred), check `archetypes/README.md` for the archetype signals. Loading an archetype adds 2-3 archetype-specific elicitation questions. **Don't force an archetype** if the prompt is generic forecasting + allocation; the universal seven dimensions cover it.

## When the user pushes back on the elicitation

If the user says "skip the questions, just design it" — skip. Use defaults, flag every inferred number as an assumption in the OPEN QUESTIONS section of the artifact. The user can correct on the next turn. **Don't loop the elicitation round** because the answers were terse; that's not the user's job to fix.
