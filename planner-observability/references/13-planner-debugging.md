# Planner debugging

Load when the prompt touches "why" — why underdeliver, why reserved, why allocation changed, why pacing shifted, why a replan fired. This is the root-cause spine of the skill. Each question is a **panel sequence** the on-call walks, not a single chart.

The principle: the planner is a decision system, and every decision it made is auditable. The dashboard reconstructs the decision so a human can see *why* the planner did what it did — from the inputs it had (forecast, demand, constraints) to the output it produced (allocation, pacing). A planner you can't interrogate is a planner you can't trust in an incident.

## The five "why" workflows

### Why did we underdeliver?

The most common incident. Panel sequence (each drills into the next):

1. **Delivery curve** — cumulative delivered vs commitment vs ideal pace, for the affected campaign/cohort. Where did the curve fall behind? `markArea` the shortfall window.
2. **Pacing trace** — the per-tick pace rate vs target rate over the same window. Did it under-pace throughout (forecast too low → timid) or over-pace early and exhaust (forecast too high → see `12`)?
3. **Forecast error for the window** — was the supply forecast wrong, and in which direction? Links to the forecast-explorer planner-impact panel.
4. **Supply shortfall** — was the supply simply not there (real shortfall) vs there-but-not-allocated (planner bug)? Compare forecasted supply, actual available supply, and allocated supply on one chart.

The sequence distinguishes the four root causes — forecast-low, forecast-high/exhaustion, real supply shortfall, allocation failure — which have four different fixes.

### Why was inventory reserved (and for whom)?

1. **Reservation breakdown** — for the supply pool in question, a stacked bar of how much is reserved by which demand cohort/commitment, vs free.
2. **Reservation timeline** — when each reservation was placed and by which planner run; click a reservation → the planner decision that created it.
3. **Contention view** — which other cohorts wanted the same supply and lost. Answers "why didn't my campaign get it."

### Why did the allocation change?

1. **Allocation diff** — between two planner runs (last replan vs this one), what moved: which cohort gained, which lost supply, by how much. A diverging bar (signed delta per cohort) or a before/after Sankey.
2. **Trigger attribution** — what input changed between the runs to cause the diff: forecast update, new commitment, supply change, constraint change. The diff without the trigger is "it changed"; with the trigger it's "it changed *because*."

### Why did pacing shift?

1. **Pace-rate timeline** with the inputs overlaid — forecast updates, dual-variable values (if a dual-decomposed pacer), budget remaining. A pace shift correlates with one of these; the overlay makes the cause visible.
2. **Dual-variable / control-signal trace** — for dual-decomposed or control-theoretic pacers, the internal signal that drove the shift. Oscillation here = the source of replan churn.

### Why was a replan triggered?

1. **Replan timeline** — every replan as an event marker on the time axis, with its trigger labeled (scheduled / forecast-drift / commitment-change / SLA-breach). Excessive replans cluster visibly.
2. **Trigger attribution per replan** — click a replan → what fired it and what it changed (links to the allocation diff). Replan churn that hurts downstream caching (a real `forecast-allocation` concern) is diagnosed here.

## Allocation flow (Sankey)

The supply→demand matching is the one place flow matters more than time. A Sankey with:

- **Left nodes** = supply pools (by market/placement/inventory class).
- **Right nodes** = demand cohorts / commitments.
- **Link width** = allocated volume; **link color** = utilization or reservation state (committed / flexible / spillover).

It answers "where did the inventory go" at a glance and makes mis-allocation (a fat link to a low-priority cohort while a high-priority one starves) visible. Drill a link → the reservation breakdown for that pool→cohort edge.

## Allocation-diff view

Comparing two planner states is the workhorse of planner debugging. Standardize it: pick run A and run B (consecutive replans, or before/after an incident), show the signed per-cohort delta sorted by magnitude, and surface the trigger that distinguishes them. Reused across "why allocation changed" and "why replan."

## Anti-patterns this reference exists to prevent

- A delivery curve with no pacing trace beneath it (you see the miss, not the mechanism).
- A "current allocation" view with no diff/history (you can't see what changed).
- Replans shown as a count, not as attributed events (you can't tell scheduled from reactive).
- A Sankey with no drill (pretty flow, no root cause).
- Reservation totals with no contention view (you can't answer "why didn't I get it").
