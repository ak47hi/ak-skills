# Pacing

Load when the prompt mentions pacing, smooth delivery, underdelivery control, dual decomposition, throttling, or budget-spreading.

## What pacing is

A pacer takes a **commitment** (deliver D units of supply to demand element `i` over horizon `[0, T]`), a **forecast** of supply (`ŝ_t` per tick), and **decisions per tick** (how much of the available supply at tick `t` to assign to commitment `i`). It controls the per-tick allocation rate `α_{i,t}` to land the cumulative delivery near the commitment with side-objectives on smoothness, fairness, and replan churn.

The simplest non-trivial version: spend a daily budget B over 24 hours when arriving traffic is non-uniform. Spending all of B in the first hour over-delivers early and under-delivers late; spending uniformly under-uses cheap traffic windows.

## Objectives — there are at least four

A pacer balances:

1. **Delivery accuracy.** `|delivered − committed|` over the horizon. Asymmetric — under-delivery usually costs more than over-delivery.
2. **Smoothness.** Variance of per-tick delivery rate. Spiky pacing is operationally bad (provisioning, downstream amplification) and economically bad (misses cheap-traffic windows).
3. **Replan churn.** How often + by how much the per-tick allocation changes when the forecast updates. Each replan has cost (planner runtime, downstream cache invalidation, behavioral effects).
4. **Fairness across commitments.** Multiple commitments compete for shared supply; allocation has to respect priorities + floors.

**Naming the weights between these is part of the design** — every pacer baked in different weights.

## Pacer ladder

### 1. Proportional (asap / front-loaded)

Spend at max rate until commitment is met. Trivial; over-delivers early, leaves nothing for late-arriving high-value traffic. **Reject by default; rare valid cases (latency-critical commitments).**

### 2. Even-pacing (uniform)

Allocate `B / T` per tick, ignoring forecast. Wins on smoothness, loses on accuracy when traffic varies (under-delivers in low-traffic windows, over-delivers in high-traffic ones). **The baseline; beat it on planner metrics or default to it.**

### 3. Forecast-proportional

Per-tick rate `α_t = B · (ŝ_t / Σ_{τ≥t} ŝ_τ)`. Spends proportional to forecast share of remaining supply. Strong baseline; sensitive to forecast error — if forecast is wrong, accuracy degrades, and re-deriving the share each tick causes churn.

### 3.5. HWM (high-water-mark) algorithm

The canonical analytical pacer for guaranteed delivery (Vee, Vassilvitskii, Shanmugasundaram 2010). At each tick, compute a per-commitment "water level" `θ_i` such that allocating to commitments with `θ_i ≥ threshold` exactly clears the forecast. The HWM threshold rises and falls as commitments fill, naturally distributing supply across competing campaigns. Provably optimal under deterministic forecasts; the lineage that informs every modern GD pacer.

**SHALE** (Bharadwaj et al. 2012) is the production refinement of HWM that adds non-uniform priorities and exploits supply factor structure (the same factorization that powers `12-cohort.md`). The Yahoo / LinkedIn GD systems descend from this lineage; teams designing a new GD pacer should benchmark against SHALE as the baseline. See `99-citations.md`.

### 4. Probabilistic / participation-rate

Decide independently per arriving impression whether to consume it for commitment `i`, with probability tuned to hit the commitment. Smooths the trajectory and naturally handles concurrent commitments. Standard in display ad delivery. Tune via PID controller or analytical formula from running delivery vs target.

### 5. Dual-decomposed (Lagrangian) pacer

For multi-commitment, shared-supply problems, the LP relaxation has dual variables `λ_i` (shadow price per commitment). At each tick, take the arriving impression and assign it to the commitment with highest priority adjusted by dual: `argmax_i (value_i − λ_i)`. Update `λ_i` via subgradient based on observed under/over-delivery. **The modern standard for guaranteed-ad-delivery.** Naturally handles multi-tenant, multi-commitment allocation; degrades gracefully under forecast error. Theoretical grounding: Buchbinder & Naor (2009), Devanur & Hayes (2009), Agrawal–Wang–Ye (2014) — see `99-citations.md` and `13-allocation.md`.

### 6. Control-theoretic (PID / MPC)

Treat the cumulative delivery vs target as a control problem. PID tunes a single feedback loop; MPC (model-predictive control) solves a constrained optimization over a receding horizon using the forecast. MPC gets very close to optimal under good forecasts; requires solver budget per tick. **Use when the planner has the solve budget AND forecast quality is decent.**

### 7. RL-based

Learn the pacing policy directly. Justified when (a) the cost function is non-convex (multi-objective with weird interactions), (b) you have offline historical data to learn from + a simulator to validate, (c) the team has the infrastructure. **Reject by default; the win over dual-decomposed is small for most problems and the operational cost is large.**

## Throttling vs pacing

These compose; they are not the same:

- **Pacing** controls the *trajectory* against a cumulative commitment — "deliver D impressions over [0, T] with smooth pacing." Output is a per-tick allocation rate that hits the target curve.
- **Throttling** caps the *instantaneous rate* on a per-resource basis — "never exceed 1000 QPS to this advertiser's endpoint" or "no more than X% of cohort `c`'s supply to commitment `i` in any minute."

A production stack runs a pacer that produces the trajectory and a throttler that enforces hard rate caps on top. Throttling is mostly an operational concern (load shedding, fairness floors); pacing is mostly an economic + SLA concern (commitment delivery).

## Overbooking

Selling more guaranteed inventory than the point forecast supports, on the expectation that some fraction never fills (campaigns pause, advertisers under-pace their own demand, eligibility filters tighten mid-flight). Standard in display ad sales; revenue uplift can be 5–20% versus strict-feasibility allocation.

The pacer absorbs the consequence: when actual demand from booked commitments exceeds available supply, the dual-decomposed pacer's `λ_i` rises and assignment goes to the highest-priority commitment automatically — the duals act as a market-clearing price. The economic question becomes the **SLA breach probability** at the chosen overbooking ratio: with what probability does some commitment under-deliver by > X% versus contract?

Tune via chance-constrained planner (`13-allocation.md`): `P(deliver_i ≥ D_i) ≥ 1 − ε` per commitment. Overbooking ratio that keeps ε ≤ contractual SLA is the operating point.

## Online vs offline planning

Most production GD systems run **both**:

- **Offline plan.** Batch LP / SHALE over the full pacing horizon, computed at replan boundaries (e.g., every 15 min – 1 h). Produces the duals `λ_i` and a per-cohort allocation curve.
- **Online pacer.** Per-impression dual-decomposed assignment using the precomputed duals; subgradient updates the duals between offline replans to absorb forecast error.

This two-layer pattern reconciles the latency budget (the online pacer runs at impression rate, ms-budget) with the optimization fidelity (the offline plan runs at minute / hour rate, second-budget). See `13-allocation.md` solver ladder for the offline side.

## Math for the dual-decomposed pacer

Minimize `Σ_i max(0, D_i − delivered_i)` (under-delivery, asymmetric) + smoothness penalty, subject to per-tick capacity. The LP relaxation:

```
min Σ_i u_i + λ_smooth · ‖α‖²
s.t.   delivered_i + u_i ≥ D_i           ∀ i        (under-delivery slack)
       Σ_i α_{i,t} ≤ ŝ_t                  ∀ t        (capacity per tick)
       α_{i,t} ≥ 0                                   (non-negativity)
```

Duals on the under-delivery constraints (`λ_i`) become the per-commitment shadow prices. Online subgradient:

```
λ_i ← max(0, λ_i + η · (D_i_remaining − projected_delivery_i))
```

Then per arriving impression at tick t, assign to `argmax_i (eligibility_i · λ_i)`.

This is the **load-bearing pacing algorithm in production ad-delivery systems**.

## Pacing under forecast uncertainty

If forecast is wide, pacing must hedge. Three approaches:

- **Quantile pacing.** Pace to the lower quantile of forecast (e.g. p25) to under-promise. Over-delivers slightly on average; under-delivery rate drops sharply.
- **Robust pacing.** Pace to worst-case forecast within a confidence band. Strong guarantees, often over-conservative.
- **Stochastic pacing.** Optimize expected delivery under the forecast distribution; planner solves a stochastic program. Highest fidelity, highest cost.

`14-uncertainty.md` covers how to get usable uncertainty into the pacer.

## Replan-churn control

The planner re-solving every tick can cause large allocation swings under noisy forecasts. Mitigations:

- **Dual-variable smoothing.** Low-pass filter the `λ_i` updates. Reduces oscillation; adds lag.
- **Hysteresis.** Only re-solve when the forecast moves > X% or the running delivery deviates > Y% from plan. Crude but effective.
- **Batched replanning.** Replan every K ticks instead of every tick. Tunes the latency-vs-stability tradeoff.
- **Trust-region replanning.** Each re-solve is constrained to stay within a ball of the previous solution. Smooth, principled, more expensive.

**Whichever mitigation, measure replan-churn as a first-class planner metric** (`91-eval-metrics.md`).

## Smoothness vs accuracy tradeoff

These almost always trade off. Even-pacing is smoothest, worst on accuracy when traffic varies. Forecast-proportional is more accurate, less smooth. **Name the weight in the design** — don't leave it as an implicit "we want both."

## Multi-commitment / fairness

With many commitments competing for shared supply:

- **Priority tiers.** Hard priorities (gold > silver > bronze). Risk: lower tiers starve.
- **Proportional fairness.** Allocation maximizes Σ log(delivered_i). Provably fair; classical.
- **Dual-priced.** The dual-decomposed pacer's `λ_i` is exactly the per-commitment shadow price; it produces a market-clearing allocation.

## Anti-patterns (cross-ref `93-anti-patterns.md`)

- Even-pacing without confirming forecast variance is low (leaves accuracy on the table).
- Forecast-proportional with no replan-churn control (oscillates).
- Per-tick LP re-solve from scratch under heavy load (latency blowout).
- RL pacer without a calibrated sim (silent failures in prod).
- No measurement of replan churn (you'll ship the noisier pacer and not know).
- Pacing to the point forecast when planner is loss-asymmetric (use a quantile).
