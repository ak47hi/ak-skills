# Simulation & replay

Load when the prompt touches simulate, replay, what-if, counterfactual, scenario. This is the surface for reasoning about planner behavior *off the live path* — before shipping a change, or reconstructing an incident after it.

The companion to `forecast-allocation`'s simulation lane: that skill designs the sim harness (replay vs Monte Carlo, what to perturb, how to calibrate). This skill designs the surface that makes the sim's output *legible* — so a human can see whether the new pacer actually wins, and why.

## Three surfaces

### 1. Sim-vs-actual overlay

The trust check. Overlay the simulator's output against the production-observed actual on the same axes (delivery curve, pacing, underdelivery). If the sim doesn't reproduce the actual within tolerance, **the sim is broken and nothing it says about new methods is trustworthy** (`forecast-allocation` anti-pattern E4 — a sim that doesn't reproduce production baselines). The panel makes that calibration gap visible *first*, before any what-if comparison. Show the reproduction tolerance band; if the actual escapes it, flag the sim as uncalibrated at the top of the surface.

### 2. Replay timeline scrubber

Reconstruct an incident tick by tick. A timeline scrubber (drag the playhead across the window) re-renders the system state at each tick: the allocation, the pacing rate, the forecast vs actual, the reservations. The on-call scrubs to the moment delivery fell behind and watches the allocation evolve into the failure. This turns "the system underdelivered sometime this afternoon" into "at 14:32 the forecast updated, the pacer over-corrected, and supply exhausted by 15:10" — a causal story you can step through.

Implementation: the scrubber drives the shared time-selection state (`18-react-architecture.md`); every panel is bound to "state at tick t," so moving the playhead updates all of them in lockstep.

### 3. Counterfactual / what-if

Swap one thing, hold everything else fixed, re-render. The disciplined form is **counterfactual planner replacement** (`forecast-allocation` E5): fix the traffic and the forecast, swap the pacer (proportional → dual-decomposed), and compare the two delivery curves side by side. Because the inputs are pinned, the difference *is* the pacer's effect — not traffic variance. The surface enforces this by making "what's held fixed" explicit and visible; a what-if that silently changes the traffic too is comparing apples to weather.

What-if controls: pick the variable to vary (pacer, forecast-error magnitude, traffic scenario), pick the baseline, render both. The forecast-error-magnitude sweep (0% / 5% / 10% / 20%) shows how each candidate degrades as the forecast gets worse — the robustness picture a single point estimate hides.

## Scenario compare

For evaluating a change before ship: a small-multiples or paired-bars view of the candidate vs baseline across the perturbation grid, on **both** forecast metrics and planner metrics (the two-table discipline from `forecast-allocation`). The decision "ship the new pacer" is made here, against a pre-registered threshold, with the sim-calibration check passed first. A scenario-compare that shows only the happy-path point, or only forecast metrics with no planner metrics, is the eval anti-pattern that ships a regression.

## Anti-patterns this reference exists to prevent

- What-if that doesn't pin the held-fixed inputs (compares the change *and* the traffic).
- Sim-vs-actual omitted — trusting the sim without showing it reproduces production.
- Replay that re-renders only one panel, not the whole system state at tick t.
- Scenario-compare on the happy path only, or forecast metrics with no planner metrics.
