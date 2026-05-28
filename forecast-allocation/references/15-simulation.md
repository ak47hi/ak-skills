# Simulation

Load when the prompt mentions simulation, replay, Monte Carlo, stress test the planner, forecast-error perturbation, or counterfactual planner evaluation.

## Why simulation is non-negotiable

You cannot evaluate a forecast + planner system on offline forecast metrics alone. Two different forecasts with the same RMSE will produce different planner outputs; the planner amplifies or absorbs forecast error in ways the forecast metric doesn't capture. The only way to know the joint system's behavior is to run it end-to-end on something that looks like production.

Simulation is the *experimentation substrate* for the whole skill. Without it:

- You can't compare pacing strategies on the metrics that matter (replan churn, smoothness, planner regret).
- You can't stress-test the planner under forecast error.
- You can't validate that a new model improves the joint system, not just the forecast.

## Four simulation strategies

### 1. Replay simulation

Take historical traffic logs and play them back through the candidate forecast + planner. Measure outcomes. Strongest because the traffic is real; weakest because it can't evaluate counterfactual decisions (you only saw what *did* happen, not what would have happened under different allocation).

Use for:

- A/B-ing pacing strategies on the same historical traffic stream.
- Validating that a new forecast doesn't break the existing planner on real data.
- Regression testing.

Key gotcha: **the planner's decisions in production altered the traffic**. Replay assumes the historical traffic is fixed; if your new allocation changes which impressions arrive (auction dynamics, frequency caps, etc.), replay overstates accuracy.

### 2. Monte Carlo over forecast distributions

For each tick, sample a forecast from the predictive distribution; run the planner on the sample; measure outcomes. Repeat over many samples to get a distribution of planner outcomes.

Use for:

- Measuring how planner robustness degrades as forecast variance widens.
- Computing planner regret distributions (not just means).
- Stress-testing the planner under deliberately perturbed forecasts.

Cheap; doesn't require historical traffic.

### 3. Synthetic traffic generation

Generate traffic from a parametric model (Poisson arrivals, calendar-driven volume, demographic mixes). Run the system. Measure.

Use for:

- Scale tests (10× traffic to see where the planner breaks).
- Drift scenarios (simulate a regime shift, see if drift monitor catches it).
- New-cohort introduction (test unseen-cohort generalization).
- Edge cases that don't appear in real traffic but matter operationally.

Calibrate the generator against real traffic statistics or the results are vapor.

### 4. Counterfactual planner replacement

Hold the forecast and traffic fixed; swap the planner; rerun. Compare planners on identical inputs. The cleanest pacer A/B.

Use for:

- Comparing pacing strategies (the most common evaluation).
- Comparing solver strategies (LP vs dual-decomposed).
- Quantifying replan churn under different replan policies.

## Discrete-event vs interval-based

- **Discrete-event.** Each impression arrival is an event; the planner makes a decision per event. Realistic for impression-level allocation. Higher fidelity; higher compute.
- **Interval-based.** Time is bucketed (per minute, per hour). The planner allocates aggregate volume per bucket. Faster; loses sub-bucket dynamics.

Use discrete-event when the planner makes per-impression decisions (probabilistic pacer, dual-priced allocation). Use interval-based when the planner allocates aggregates (proportional pacer, batch LP).

## What to measure

Two tables, always (mirror `91-eval-metrics.md`):

**Forecast metrics in sim:**

- Point: RMSE, MAE, wMAPE per cohort and aggregate.
- Probabilistic: pinball loss per quantile, CRPS, PIT histogram, per-quantile coverage.

**Planner metrics in sim:**

- **Underdelivery percentage** (and tail percentiles, not just mean).
- **Pacing smoothness** (variance of per-tick delivery, or `Σ (α_t − α_{t-1})²`).
- **Replan churn** (replans per cohort × magnitude of change).
- **Allocation stability** (how much per-cohort allocation moves across replans).
- **Planner regret** (gap to optimal allocation under retrospective ground truth).
- **SLA violations** (count of commitments missing target by > X%).

## Perturbation grids

To stress-test the planner under forecast error, run the sim across a grid:

- Forecast-error magnitude: 0%, 5%, 10%, 20%, 50%.
- Forecast bias: ±0%, ±10% (under- vs over-forecasting).
- Drift scenarios: stationary, gradual drift, regime shift.
- Traffic shocks: 2×, 5× spike.
- Cohort introduction: N% new cohorts injected mid-run.

Report planner metrics across the grid. The flat region (where the planner is robust) and the cliff (where it isn't) are both informative.

## Chaos engineering for planners

The perturbation grid stresses *forecast quality*. Chaos engineering stresses *operational reliability* — an orthogonal axis that's just as load-bearing. The planner's degradation path (fall back to even-pacing? freeze on last-known plan? page on-call?) is tested only by injecting realistic operational failures:

- **Solver timeouts.** Planner LP times out mid-tick; does the system use the previous solution, or no allocation?
- **Retraining failures.** Forecast pipeline fails for N days; does serving fall back to a frozen model, last-known-good, or a degraded baseline?
- **Label-pipeline delay.** Delivery confirmations land +24 h late instead of +1 day; does drift detection still fire, or does it silently miss?
- **Partial cohort blackout.** Forecast unavailable for X% of cohorts (data quality issue, schema change); does the planner allocate zero, fall back to historical, or crash?
- **Correlated traffic shock.** All cohorts in a market spike 5× simultaneously (sporting event, news cycle); does the planner thrash on replan churn, or does the smoothing absorb it?

This is the "chaos monkey" pattern from distributed systems applied to forecasting + allocation. Pair it with the forecast-error perturbation grid; both axes need coverage before production.

### Latency / jitter injection

In production, planner solve time and label availability both vary stochastically. Sim that uses deterministic latencies says "replan-every-tick is fine" when production says otherwise. Add to the perturbation grid:

- **Planner solve latency variance** (e.g., p50 = 100 ms, p95 = 5 s, p99 = 30 s).
- **Label-availability lag distribution** (e.g., p50 = +1 day, p99 = +7 days).
- **Retraining cycle drift** (e.g., scheduled hourly, but 5% of the time it's delayed by 6+ hours).

### Regime shift injection (drift regression test)

Synthesize an abrupt 20% mean shift at tick `T/2`. Measure:

- **Time-to-detect** — how many ticks before the drift monitor (`14-uncertainty.md`) fires.
- **Planner recovery time** — how many ticks before planner metrics return within SLA.
- **Worst-case underdelivery during the recovery window**.

Use this as a regression test every time the drift pipeline or retraining trigger changes — without it, drift-monitoring regressions ship silently.

## Baselines

Every sim run needs baselines or the numbers are meaningless:

- **Production planner** (the thing currently running).
- **Even-pacing.** Cheap, dumb; the floor.
- **Oracle planner** (using ground-truth supply, not forecast). Upper bound on performance; the planner-regret denominator.

A new planner is interesting only if it beats production on the SLO metrics, beats even-pacing meaningfully, and approaches oracle within the forecast error budget.

## Calibrating the simulator

A sim that doesn't match production is a confident lie generator. Calibration:

- **Traffic distribution.** Volume, time-of-day, day-of-week, cohort mix. Match the marginals to within ~5%.
- **Forecast error distribution.** Don't use uniform-noise perturbations if production forecast errors are heavy-tailed. Calibrate the error model against historical forecast residuals.
- **Latencies.** Simulate planner solve time, retrain cycle, label availability lag. Otherwise the sim says replan-every-tick is fine when it isn't.

## Validation: the sim should reproduce known facts

Before trusting the sim's verdict on a new pacer, verify the sim reproduces facts you already know:

- Production pacer's metrics on replayed historical traffic match production-observed metrics within tolerance.
- Even-pacing produces the smoothness it should and the underdelivery it should.
- Oracle produces near-zero regret.

If the sim doesn't reproduce these, the sim is broken — fix it before drawing conclusions from it.

## Deliverable in PROTOTYPE mode

`templates/prototype.py` ships a runnable `simulator.py` event loop with this shape:

```
for t in time_grid:
    forecast = forecaster.predict(t, horizon)
    allocation = planner.allocate(forecast, demand, constraints)
    realized = traffic_source.realize(t)            # historical replay or synthetic
    observed = environment.step(allocation, realized)
    metrics.record(observed, allocation, forecast)
```

Three swappable interfaces (`forecaster`, `planner`, `traffic_source`) so users can plug in their own implementations.

## Anti-patterns (cross-ref `93-anti-patterns.md`)

- A sim that doesn't reproduce production baselines.
- Reporting planner metrics on a sim calibrated only on traffic but not forecast-error distribution.
- Comparing pacers without a fixed forecast (so improvements get attributed to the pacer when they came from forecast variance).
- A perturbation grid that only covers symmetric Gaussian noise (production forecast errors are heavy-tailed and biased).
- "Looks good in sim" as the ship criterion — sim is a necessary, not sufficient, condition.
