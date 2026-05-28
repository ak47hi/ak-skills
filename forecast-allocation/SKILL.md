---
name: forecast-allocation
description: 'Design forecasting + allocation systems — where a forecast feeds a planner allocating scarce supply against committed demand under uncertainty. Routes by mode (DESIGN → design doc, PROTOTYPE → runnable Python skeleton, EVALUATE → metrics + simulation plan), elicits binding constraints (cohort cardinality, sparsity, planner objective, SLO, latency), loads only the research areas touched (forecasting, pacing, cohort representation, allocation, uncertainty, simulation). Every choice ties to a binding constraint and a sacrifice; rejects cohort-ID memorization, one-model-per-cohort, RMSE-only eval, planner-unaware loss. Archetypes: guaranteed ad delivery, capacity planning, supply-chain, scheduler-quotas. Trigger on: "forecast across cohorts", "design pacing", "guaranteed delivery", "planner-aware forecasting", "factorized forecast", "replan churn", "simulate pacing under forecast error". Do NOT use for: real-time auction bidding, attribution modeling, CTR ranking, or point forecasts with no downstream allocator.'
---

# forecast-allocation skill

Design systems where a **forecast feeds a planner**. The forecast estimates future supply or demand; the planner allocates that supply against committed demand under constraints. The two pieces are coupled: a forecast that scores well in isolation can still cause a planner to thrash, underdeliver, or replan churn — so the skill treats them as one system.

Opinionated about three things:

1. **Numbers and structure both first.** Cohort cardinality, sparsity rate, peak event QPS, replan cadence, and planner runtime budget reshape the design before any model is picked. A factorized representation that fits in memory at 10⁶ cohorts is a different system from one that does not.
2. **Planner-aware objectives outrank forecast-only metrics.** A forecast with better RMSE that causes more replan churn is worse. The skill always asks for the *planner's* loss before picking the model's loss.
3. **Compositional over enumerative.** Set-based / factorized / latent-embedding representations beat one-model-per-cohort or cohort-ID memorization. Sparsity and combinatorial cohort growth break enumeration before throughput does.

This is for designing **real** systems. Not for pure point forecasting with no allocator downstream — a standard time-series workflow handles that.

---

## Mode routing

Before phases, name the mode. Most prompts are DESIGN; the others have different deliverables.

| Signal | Mode | Deliverable |
|---|---|---|
| "design X" / "how should we forecast Y" / "what's the right pacing strategy" | **DESIGN** | Cited design doc (`templates/design-doc.md`) |
| "prototype X" / "give me a skeleton I can run" / "build a sim harness" | **PROTOTYPE** | Runnable Python skeleton: forecaster + planner + simulator (`templates/prototype.py`) |
| "evaluate X" / "compare A vs B vs C under forecast error" / "what should we measure" | **EVALUATE** | Eval + simulation plan (`templates/eval-plan.md`) |

When ambiguous, **default to DESIGN with propose-and-go** ("Treating this as a design request — say so if you actually want runnable code or an eval plan"). The cost of a wrong mode is one turn; the user corrects.

Cross-cutting rules in every mode:

- Constraints gate the work — no model, no planner, no eval design without them (inferred + flagged is fine).
- Every significant choice ties to a binding constraint and an accepted sacrifice (`references/90-tradeoffs.md`).
- The anti-pattern catalog in `references/93-anti-patterns.md` is walked during OUTPUT.
- Output matches the user's depth. Narrow question → narrow answer; full design request → full template.

---

## Six phases

```
1. ELICIT         The gate. Constraints + archetype + mode.            references/00-elicitation.md
2. ROUTE          Mode → workflow. Prompt → which research areas.      references/01-routing.md
3. FRAME          Math + assumptions per loaded area.                  references/10-..15-*.md
4. ANALYZE        Scalability + sparsity + planner-coupling tradeoffs. references/90-tradeoffs.md
5. EVALUATE       Metrics (forecast + planner) + simulation strategy.  references/91-eval-metrics.md
6. OUTPUT         Artifact per mode contract; walk anti-patterns.      references/92-output-contracts.md
                                                                       references/93-anti-patterns.md
```

Run in order. Skip a phase only when its output is supplied (e.g. user pastes constraints — skip ELICIT; user asks one narrow question — skip everything irrelevant to it).

---

## Phase 1: ELICIT (the gate)

**Do not produce a design before constraints exist.** Inferred constraints are fine — flag them as assumptions — but a model picked with zero numbers is guessing.

### Seven dimensions to pin down

1. **Forecast horizon + cadence.** What's being predicted, how far ahead, how often is it refreshed? Daily ad impressions 7 days out is a different model from hourly clicks 1 hour out.
2. **Cohort cardinality and sparsity.** How many distinct cohorts (segments, SKUs, ad-group sets)? What fraction have meaningful history (≥30 observations)? Sparsity drives representation choice harder than scale does.
3. **Planner objective and constraints.** What does the planner optimize, and what are its hard constraints? "Minimize underdelivery subject to budget caps and smoothness" is a different system from "maximize revenue subject to delivery commitments."
4. **SLO on the joint system.** Underdelivery percentage, smoothness target, replan churn ceiling, allocation stability. Without this the eval can't be designed.
5. **Data shape.** History depth, observed-vs-unseen-cohort ratio, label-noise level, missingness pattern. Decides whether a global model + cohort embeddings even has signal.
6. **Latency budget for inference + planning.** A 1 ms forecast is a different model from a 10-second one. A planner with a 1-minute solve budget can run an LP; one with 50 ms cannot.
7. **Operational reality.** Team, stack, retraining cadence, who owns the planner, who owns the model. A forecaster that needs retraining every hour by a 2-person team is a different system from one retrained weekly.

### When to skip, when to ask, when to propose-and-go

| Signal in the prompt | Action |
|---|---|
| All seven dimensions stated (or derivable from a clear scenario) | Skip ELICIT. Proceed to ROUTE. |
| User asks one targeted decision ("factorize cohort forecast or one-per-cohort at 50k cohorts?") | Skip ELICIT. Confirm the binding constraint inline (≤1 sentence) and answer narrowly. |
| Three or fewer dimensions missing AND defaults are uncontroversial | Propose-and-go: state inferred defaults in a single short block, proceed. |
| Four or more missing OR the prompt is broadly vague ("design our forecasting system") | Ask ONE batched round. Number the questions. Do not iterate elicitation rounds. |

**One round, not three.** If the user's answer is still vague, infer the rest and flag every inferred number as an assumption.

**What NOT to ask:** the model family, the framework, the cloud, the language. Those are downstream decisions the skill makes; the user supplies constraints, not solutions.

Full rules + the propose-and-go template live in `references/00-elicitation.md`.

---

## Phase 2: ROUTE

Two routings, applied together.

**Routing A — mode → workflow:**

| Mode | Phase 3 (FRAME) loads | Phase 6 (OUTPUT) emits |
|---|---|---|
| DESIGN | the research-area refs the prompt touches | `templates/design-doc.md` |
| PROTOTYPE | the same refs + the prototype contract | `templates/prototype.py` with forecaster + planner + simulator stubs |
| EVALUATE | `91-eval-metrics.md` + `15-simulation.md` + any area being evaluated | `templates/eval-plan.md` |

**Routing B — prompt intent → which research-area references to load.** Load only what the prompt touches; loading all six is the failure mode.

| Prompt signals | Load |
|---|---|
| "forecast …", "predict …", "global model vs per-cohort", "factorize" | `10-forecast.md` |
| "pacing", "underdeliver", "smooth delivery", "dual decomposition" | `11-pacing.md` |
| "cohort", "ad-group sets", "combinatorial", "unseen segment", "set representation" | `12-cohort.md` |
| "allocation", "LP", "min-cost flow", "solver", "assign supply to demand" | `13-allocation.md` |
| "uncertainty", "quantile", "calibration", "drift", "Bayesian", "conformal" | `14-uncertainty.md` |
| "simulate", "replay", "Monte Carlo", "stress test the planner", "what if forecast off by X%" | `15-simulation.md` |

Full routing rules + worked examples in `references/01-routing.md`. Archetype detection (guaranteed ad delivery / capacity planning / supply-chain / scheduler-quotas) happens here too — see `references/archetypes/README.md`.

---

## Phase 3: FRAME

For each loaded research area, produce:

- **Math.** The objective, the loss, the constraints. Symbols defined.
- **Assumptions.** Stationarity, independence, observability, label availability — name the ones being relied on.
- **Candidate approaches.** At least two, named with their tradeoff axis (e.g. "factorized vs joint" or "proportional vs dual-decomposed pacing").

This is the modeling section of the design. No code yet (PROTOTYPE mode generates code in OUTPUT, not here).

---

## Phase 4: ANALYZE

Walk three dimensions against the framed approaches. Each surfaces a finding that gets recorded in OUTPUT.

1. **Scalability.** Memory + compute at the cohort cardinality and event rate from ELICIT. A factorized model that fits in 4 GB at 10⁵ cohorts may not at 10⁷.
2. **Sparsity behavior.** How does each approach degrade as the observed-cohort fraction drops? One-model-per-cohort fails first; latent embeddings degrade gracefully; factorized representations depend on the factor structure.
3. **Planner coupling.** How does forecast error propagate into planner output? A 10% point-forecast miss can become 30% replan churn under a brittle proportional pacer or 5% under a dual-decomposed one. The planner amplifies or absorbs forecast error.

Rules + the decision template live in `references/90-tradeoffs.md`.

---

## Phase 5: EVALUATE-design

Pick metrics and a simulation strategy. **Two tables, always:**

- **Forecast metrics** — RMSE / MAE / wMAPE / quantile loss / CRPS / calibration error. Pick by the loss the planner cares about (calibration matters more than RMSE when the planner consumes quantiles).
- **Planner metrics** — underdelivery %, smoothness, allocation stability, replan churn, planner regret, SLA violations. Weight by the SLO from ELICIT.

**Simulation strategy** chosen from `references/15-simulation.md`: replay vs Monte Carlo vs synthetic-traffic generation vs counterfactual planner replacement. Name what's being measured, the perturbation grid (forecast-error magnitude, drift scenarios, traffic spikes), and the baselines.

Full guidance in `references/91-eval-metrics.md`.

---

## Phase 6: OUTPUT

Emit the artifact per `references/92-output-contracts.md`:

| Mode | Artifact | Required sections |
|---|---|---|
| DESIGN | `design-doc.md` | Problem framing • Constraints + assumptions • Mathematical framing • Approach comparison (≥2 candidates) • Recommended approach • Scalability analysis • Data requirements • Failure modes • Evaluation plan • Simulation strategy • Open questions |
| PROTOTYPE | `prototype.py` package | `forecaster.py` with `fit / predict / predict_quantiles` • `planner.py` with `allocate(forecast, demand, constraints)` • `simulator.py` event loop • runs unmodified with stdlib + numpy + scipy |
| EVALUATE | `eval-plan.md` | Hypothesis • Baselines • Datasets / sim harness • Forecast metrics • Planner metrics • Ablations • Statistical-significance protocol • Reporting format |

After producing the artifact, **walk the anti-pattern catalog** (`references/93-anti-patterns.md`) against it. Each pattern that fires becomes a note in the artifact (or a fix before emitting). Bans called out explicitly:

- Cohort-ID memorization (treating cohort ID as a categorical feature with no compositional structure)
- One-model-per-cohort at scale
- RMSE-only evaluation when the planner consumes quantiles
- Planner-unaware loss
- Stationary-traffic assumption without drift monitoring
- Naive lookup tables / brittle hand-tuned heuristics

---

## When to push back

Common smells worth challenging up front:

- **"Train one model per cohort."** → How many cohorts, how sparse? Beyond ~10³ active cohorts with sparse history, this fails on data efficiency before infrastructure cost. Use a global model with cohort features / embeddings; see `references/12-cohort.md`.
- **"Use cohort ID as a categorical feature."** → No. The model memorizes; it cannot generalize to unseen cohorts. Use a compositional representation over the cohort's constituent attributes.
- **"Optimize RMSE."** → What does the planner consume — a point forecast or quantiles? If quantiles, calibration matters more than RMSE. If the planner is loss-asymmetric (under vs over-delivery have different costs), the forecast loss must reflect that.
- **"Forecast first, then think about the planner."** → No. The planner's objective shapes the forecast's loss. Design them together.
- **"Add a deep model."** → What constraint forces it? GBDT or even ETS often beats a transformer on sparse hierarchical forecasts. Justify the deep model with a constraint (long-range dependencies, multi-modal features) or default to the simpler model.
- **"Re-plan every tick."** → Replan churn is itself a cost the planner pays. Stabilize via dual variables, hysteresis, or batched replanning unless intra-tick reactivity is a binding requirement.

These are conversations, not refusals. If the user has a reason, the reason is the binding constraint — record it in the design doc.

## When NOT this skill

- **Real-time auction bid optimization.** Different problem — adversarial second-price dynamics, sub-millisecond budgets, no pacing-style forward commitment. Use a bidding/auction skill.
- **Attribution / measurement modeling.** Counterfactual estimation, not forecasting + allocation.
- **Ad creative ranking / CTR prediction.** Pure prediction, no allocator downstream.
- **Pure point forecasting (no downstream allocator).** A standard time-series workflow handles that.

---

## Tone and depth

Terse, professional, no emoji, no decorative filler. Match the user's depth: give experts the tradeoff, not the definition. If the user said "CRPS," don't explain quantile losses first. The output is decisions, not a textbook. Every paragraph should change what the reader builds.

---

## References at a glance

| File | What it carries |
|---|---|
| `references/00-elicitation.md` | Seven elicitation dimensions, skip/ask/propose-and-go decision rules, the propose-and-go template. |
| `references/01-routing.md` | Mode-to-workflow table, prompt-intent-to-research-area table, archetype detection signals, worked examples. |
| `references/10-forecast.md` | Forecast model ladder (seasonal-naive → ETS/Prophet → GBDT → DeepAR/TFT → ensemble/Bayesian), factorized forecasting math, quantile vs point loss, multi-horizon, when each model is justified. |
| `references/11-pacing.md` | Pacing as constrained optimization, proportional / probabilistic / dual-decomposed / control-theory / RL pacers, underdelivery vs smoothness vs replan-churn axes. |
| `references/12-cohort.md` | Cohort cardinality math, sparsity behavior, set-based representations (DeepSets, Set Transformer), latent embeddings, GNN message passing, factorized decompositions, compositional generalization to unseen cohorts. |
| `references/13-allocation.md` | Planner as LP / min-cost flow / convex program / stochastic online optimization, dual decomposition, robust optimization under forecast uncertainty, when a closed-form proportional split suffices. |
| `references/14-uncertainty.md` | Quantile vs point forecasts, calibration (PIT, CRPS), Bayesian/ensemble uncertainty, conformal prediction, drift detection, propagating uncertainty into the planner. |
| `references/15-simulation.md` | Replay vs Monte Carlo vs synthetic vs counterfactual; discrete-event vs interval-based; what to measure (planner regret, SLA violations, replan churn). |
| `references/90-tradeoffs.md` | ADR-style decision template — every choice = binding constraint + accepted sacrifice. |
| `references/91-eval-metrics.md` | Forecast metric table + planner metric table; how the planner's objective weights the forecast loss. |
| `references/92-output-contracts.md` | What each mode's artifact must contain. Maps to `templates/`. |
| `references/93-anti-patterns.md` | Bans (cohort-ID memorization, one-model-per-cohort, RMSE-only, planner-unaware loss, stationarity, naive lookup). Walked in OUTPUT. |
| `references/archetypes/` | Catalog: guaranteed-ad-delivery, capacity-planning, supply-chain, scheduler-quotas. Per archetype: when it fires, additional elicitation, recurring failure modes, anchor numbers. |
| `references/99-citations.md` | Annotated primary literature for every research-area reference (M5, TFT, DeepAR, N-BEATS, Chronos / TimesFM / Moirai, HWM, SHALE, Buchbinder–Naor, OptNet / cvxpylayers, CQR, deep ensembles, robust LP). Cited by name; loaded only on explicit request. |
| `templates/design-doc.md` | DESIGN deliverable skeleton. |
| `templates/prototype.py` | PROTOTYPE deliverable skeleton (runs unmodified). |
| `templates/eval-plan.md` | EVALUATE deliverable skeleton. |
