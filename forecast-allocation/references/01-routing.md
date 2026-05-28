# Routing

Load after ELICIT. Decides (a) what mode-specific workflow to run, (b) which research-area references to load, (c) whether an archetype fires.

The failure mode is loading everything. Don't load research areas the prompt doesn't touch — context budget is real, and a more-focused design beats a more-comprehensive one.

## Routing A: mode → workflow

| Mode | Trigger signals | Phase 3 (FRAME) loads | Phase 6 (OUTPUT) emits |
|---|---|---|---|
| **DESIGN** | "design", "how should we forecast", "what's the right pacing strategy", "architecture for X" | research-area refs the prompt touches + `90-tradeoffs.md` | `templates/design-doc.md` |
| **PROTOTYPE** | "prototype", "skeleton", "give me code I can run", "sim harness", "starter implementation" | same refs + `92-output-contracts.md` (prototype section) | `templates/prototype.py` (forecaster + planner + simulator stubs) |
| **EVALUATE** | "evaluate", "compare A vs B", "what should we measure", "stress test", "simulate under forecast error" | `91-eval-metrics.md` + `15-simulation.md` + any area being evaluated | `templates/eval-plan.md` |

**Ambiguous?** Default to DESIGN with a propose-and-go disclosure: "Treating this as a design request — say so if you wanted a runnable prototype or an eval plan."

A request can shift mode mid-conversation ("now prototype this"). The skill switches modes cleanly, re-using already-elicited constraints.

## Routing B: prompt intent → research-area references

Load only the references the prompt touches. The grid:

| Prompt signals (any) | Load |
|---|---|
| "forecast", "predict", "global model", "per-cohort", "factorize", "hierarchical forecast", "demand forecast", "supply forecast" | `10-forecast.md` |
| "pacing", "smooth delivery", "underdeliver", "delivery rate", "throttle", "dual decomposition" | `11-pacing.md` |
| "cohort", "segment", "ad-group set", "combinatorial", "unseen cohort", "set representation", "embedding for segments" | `12-cohort.md` |
| "allocation", "LP", "min-cost flow", "solver", "assign supply", "matching", "scheduling" | `13-allocation.md` |
| "uncertainty", "quantile", "calibration", "drift", "Bayesian", "conformal", "confidence", "interval", "predictive distribution" | `14-uncertainty.md` |
| "simulate", "replay", "Monte Carlo", "stress test", "perturb forecast", "what if forecast off by X%", "counterfactual planner" | `15-simulation.md` |

A request often touches multiple areas. Examples:

- "Design a forecast for ad-group cohorts where data is sparse." → `10-forecast.md` + `12-cohort.md` + `14-uncertainty.md` (sparsity ⇒ uncertainty).
- "Compare pacing strategies under 10% forecast error." → `11-pacing.md` + `15-simulation.md` + `14-uncertainty.md`.
- "Build a planner that consumes a quantile forecast and minimizes underdelivery." → `11-pacing.md` + `13-allocation.md` + `14-uncertainty.md`.
- "Prototype a sim harness I can run locally." → `15-simulation.md` is mandatory; the rest depend on what's being simulated.

## Routing C: archetype detection

Run after Routing A + B. Check `archetypes/README.md` for archetype signals. If one fires, load the archetype file — it adds 2-3 archetype-specific elicitation questions, recurring failure modes, and anchor numbers.

**Don't force an archetype.** If none of the signals match, the universal foundation handles it. Forcing an archetype that doesn't fit pollutes the design with irrelevant concerns.

## Anti-routing

Load *only* what's needed. Specifically:

- A pure forecasting question with no planner downstream (forbidden by the skill's "do not use for" clause) — refuse politely and point to a standard time-series workflow.
- A pure pacing question that mentions no cohorts ("how do I pace one ad group?") — do **not** load `12-cohort.md`. Just pacing + maybe allocation + maybe uncertainty.
- A pure eval question ("what metrics matter") — load `91-eval-metrics.md` and only the area being evaluated. Do not re-derive the entire forecast stack.

## Worked examples

### Example 1: "We're forecasting ad-group cohort impressions across 50k cohorts. Half are sparse. Pacing has to hit ≥98% delivery with ≤3 replans/cohort/day."

- Mode: **DESIGN** (default; "we're forecasting" + "pacing has to hit" + design implied).
- Research areas: `10-forecast.md`, `12-cohort.md` (cohorts + sparsity), `11-pacing.md`, `14-uncertainty.md` (sparsity ⇒ wide intervals).
- Archetype: `guaranteed-ad-delivery.md` fires hard.
- Out: design-doc.md with factorized forecast + dual-decomposed pacer + planner-aware quantile loss + sim plan.

### Example 2: "Give me a Python skeleton for a pacing simulator I can run locally to test underdelivery under noisy forecasts."

- Mode: **PROTOTYPE** ("skeleton", "I can run locally").
- Research areas: `15-simulation.md` (mandatory), `11-pacing.md`, `14-uncertainty.md` (noisy forecasts).
- Archetype: not forced — generic pacing sim.
- Out: prototype.py with `forecaster.py` (noisy stub), `planner.py` (proportional pacer), `simulator.py` (tick loop measuring underdelivery + smoothness).

### Example 3: "Compare proportional, probabilistic, and dual-decomposed pacing for replan churn under 10% forecast error."

- Mode: **EVALUATE** ("compare … for replan churn under …").
- Research areas: `11-pacing.md`, `15-simulation.md`, `91-eval-metrics.md`.
- Archetype: not forced.
- Out: eval-plan.md with three pacer baselines, forecast-error perturbation grid (5%, 10%, 20%), forecast + planner metric tables, ablation on replan cadence, significance protocol (paired bootstrap).

### Example 4 (narrow): "Should I use quantile loss or RMSE for a forecast that feeds an LP planner with asymmetric underdelivery cost?"

- Mode: chat-mode narrow answer (still DESIGN, but no template needed).
- Research areas: `14-uncertainty.md`, `13-allocation.md`, brief `91-eval-metrics.md`.
- Out: short scoped answer naming the binding signal (LP + asymmetric cost → planner consumes quantiles, so calibration + asymmetric quantile loss; RMSE is wrong because it punishes the wrong errors). Do **not** emit the full design-doc template.

## After routing

Hand off to Phase 3 (FRAME) with the loaded references. Each loaded reference contributes its math, candidate approaches, and tradeoff axes to the design.
