# Allocation

Load when the prompt mentions allocation, LP, min-cost flow, matching, scheduling, supply-to-demand assignment, or "the planner."

## The planner as constrained optimization

A planner takes:

- A **supply forecast** (`ŝ_t` per resource per tick), with or without uncertainty.
- A set of **commitments** (deliver `D_i` to demand element `i` over `[0, T]`, with priority, eligibility constraints, fairness floors).
- **Operational constraints** (capacity per resource, latency budget, batch boundaries).

…and produces an **allocation** (`α_{i, r, t}` — how much of resource `r`'s tick-`t` supply goes to commitment `i`). The objective is a weighted sum of delivery accuracy, smoothness, replan churn, fairness, revenue.

This reference catalogs the solver families and when to pick each.

## Solver ladder

### 1. Closed-form proportional split

When all commitments are equal-priority, no per-tick capacity binds, and forecast is deterministic, allocation is `α_i ∝ D_i / Σ D_j` per tick. Trivial.

Use when there is genuinely no interaction. The narrow valid case.

### 2. Greedy / heuristic

Per arriving impression (or per tick), pick the highest-scoring eligible commitment by a hand-coded rule. Fast, simple, hard to reason about under multi-objective settings. **Strong baseline; weak ceiling.**

### 3. Linear program (LP)

```
min   c^T α                                  (objective: weighted sum of slacks, smoothness, churn)
s.t.  A α ≤ b                                 (capacity per resource × tick)
      B α ≥ D − u, u ≥ 0                      (commitment with under-delivery slack)
      α ≥ 0
```

Standard LP. Solvers: `scipy.optimize.linprog` (small), HiGHS / Gurobi / CPLEX (large). Polynomial-time; warm-startable from the previous tick's solution to speed re-solves.

**The dominant planner formulation.** Use when (a) objectives are linear or linearizable, (b) the planner has a solve budget of seconds-not-milliseconds, (c) the structure (totally unimodular A) or scale makes LP tractable.

### 4. Min-cost flow

Special case of LP with a graph structure: sources (supply ticks), sinks (commitments), edges with cost + capacity. Polynomial-time, often orders of magnitude faster than general LP for the same problem because the network simplex / cost-scaling algorithms exploit structure.

Use whenever the allocation problem reduces to a bipartite assignment with capacities — guaranteed-ad-delivery without complex side-constraints, supply-chain shipment routing, scheduler-to-quota assignment.

### 5. Convex program (QP / SOCP)

When the objective has a quadratic smoothness term (`λ ‖α‖²`) or robust constraints (`Σ α ≥ D` under uncertainty set), the problem is convex but not LP. Solvers: OSQP, ECOS, MOSEK.

Cost vs LP: higher solve time, smaller solver ecosystem, but supports principled smoothing and robustness.

### 6. Mixed-integer (MILP)

When decisions are discrete — assign-or-not flags, batch-size choices, on/off scheduling. NP-hard in general; practical scale up to ~10⁵ variables with commercial solvers, much less with open-source.

**Justify carefully.** Most "must be integer" problems have an LP relaxation + rounding that ships fine; the MILP is a 10× operational cost.

### 7. Stochastic programming / robust optimization

Two-stage stochastic: solve `min E_ω[c^T α(ω)]` subject to constraints over realizations of forecast uncertainty `ω`. Robust: solve `min max_ω c^T α` over a confidence set. Both incorporate forecast uncertainty directly into the planner.

Use when forecast uncertainty is wide and the planner is currently brittle to it. Cost: solver expertise, solve time grows in scenario count.

### 8. Online / sequential decision

Treat allocation as a control problem solved tick-by-tick rather than as a batch optimization. The dual-decomposed pacer in `11-pacing.md` is exactly this. Multi-armed bandits, online convex optimization, MPC fall here. Strong when the problem has natural sequential structure and forecasts are short-horizon.

### 9. RL / learned planner

Learn the allocation policy. Justified rarely; the analytical solvers above almost always win on stability + sample efficiency + interpretability. The win for RL is in problems where the cost function is non-differentiable, non-convex, and rich offline data + a sim exist.

## Dual decomposition

If the LP has structure — coupling constraints (per-tick capacity) connecting otherwise-independent commitments — dual decomposition lifts the coupling constraints into the objective via multipliers `λ_t`, then each commitment solves an independent subproblem given the duals. Subgradient updates the duals.

The resulting algorithm is:

```
for each tick t with arriving supply s_t:
    for each arriving impression: assign to argmax_i (value_i − λ_i,t) over eligible commitments
    observe under/over-delivery
    update λ_i,t via subgradient: λ_i ← max(0, λ_i + η · (D_i − projected_delivery_i))
```

This is the load-bearing online planner for guaranteed-ad-delivery. Scales linearly in commitments × supply ticks, decentralizable, naturally handles streaming arrival.

## Robust / stochastic under forecast uncertainty

If the forecast comes with a predictive distribution (quantiles, samples), the planner can:

- **Quantile-plan.** Pace to a conservative quantile of supply (e.g. p25 of `ŝ_t`). Cheap, asymmetric, leaves quality on the table.
- **Scenario-based stochastic LP.** Sample K forecast trajectories; solve `min Σ_k c^T α^k subject to per-scenario constraints` with non-anticipativity. Computationally expensive; principled.
- **Chance-constrained.** Enforce constraints in probability: `P(Σ α_t ≤ s_t) ≥ 1 − ε`. Tractable for Gaussian forecasts; reformulates as deterministic LP with shifted RHS.

Pick by solve budget. `14-uncertainty.md` covers how to produce the inputs.

## Replan strategy

A planner that re-solves every tick under noisy forecasts oscillates. Mitigations:

- **Warm start.** Re-solve seeded from the previous solution. Solver converges fast, but the solution can still move a lot if forecast moved.
- **Trust-region replan.** Constrain `‖α_new − α_old‖ ≤ ε` per re-solve. Smooth; loses some optimality.
- **Forecast-change-triggered replan.** Only re-solve when forecast moved > X% or running delivery drift > Y%. Cheapest; coarse.
- **Batched replan.** Re-solve every K ticks. Tunes latency-vs-stability.

## Latency budget

Rough solve times (single machine, ~10⁴ variables / constraints):

| Solver | Order of magnitude |
|---|---|
| Closed-form / heuristic | µs - ms |
| Network simplex (min-cost flow) | ms - 100 ms |
| LP (HiGHS / Gurobi) | 10 ms - seconds |
| QP (OSQP) | 10 ms - seconds |
| MILP | seconds - minutes (or unbounded) |
| Stochastic LP (100 scenarios) | seconds - minutes |

A planner with 50 ms budget rules out MILP and pushes toward closed-form / heuristic / dual-decomposed. A planner with 1-minute budget opens LP / stochastic.

## Anti-patterns (cross-ref `93-anti-patterns.md`)

- MILP when LP-relaxation + rounding is empirically fine.
- Re-solve every tick with no replan-churn control.
- Closed-form proportional with multi-priority commitments (loses fairness).
- Ignoring forecast uncertainty in the planner ("just use the point forecast") when the forecast is wide.
- RL planner without a sim that matches production.
- Hand-tuned heuristic claimed to be "as good as LP" without an A/B vs LP.
