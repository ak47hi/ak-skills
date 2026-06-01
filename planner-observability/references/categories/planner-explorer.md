# Category: planner-explorer

**When it fires.** "Planner decisions", "allocation plan", "reservation details", "what did the planner do", "why did the allocation change", "replan history". Tier 2 → 3.

**Decision it serves.** Planner SRE: reconstruct what the planner decided and why — which inputs it had, what it allocated, what changed between runs. A planner you can't interrogate is one you can't trust in an incident.

**Key panels + chart choices** (governed by `13-planner-debugging.md`).
- **Allocation plan** — current allocation by cohort/commitment; sorted bars or a matrix.
- **Allocation diff** — signed per-cohort delta between two runs (diverging bars) + the trigger that distinguishes them. The workhorse.
- **Reservation breakdown** — stacked bar: reserved-by-whom vs free, per supply pool; + contention view (who wanted it and lost).
- **Replan timeline** — every replan as an attributed event marker (scheduled / drift / commitment / SLA), with churn clustering visible (`13`, `14` OB5).
- **Pace-rate + dual-variable trace** — internal planner signals over time for "why pacing shifted."

**Drill paths.** Replan event → allocation diff → trigger attribution → the forecast/demand/constraint change that fired it. Reservation → the planner run that created it → contention.

**Recurring anti-patterns.** "Current allocation" with no diff/history; replans as a count not attributed events; reservation totals with no contention; SD4 dead-end plan view.

**Anchor metrics.** Replan frequency, allocation churn, reservation success/failure, contention rate, constraint violations.
