# Category: allocation-explorer

**When it fires.** "Supply→demand matching", "allocation flows", "where did the inventory go", "reservation breakdown", "spillover". Tier 3.

**Decision it serves.** Planner SRE / analyst: how is supply flowing to demand, where is it mis-matched (a fat link to a low-priority cohort while a high-priority one starves), and how much of each pool is committed vs free?

**Key panels + chart choices** (governed by `13-planner-debugging.md`).
- **Allocation Sankey** — supply pools (left) → demand cohorts (right); link width = allocated volume; link color (+ label) = utilization / reservation state (`11` Sankey, `94` no color-only). The "where did it go" panel.
- **Reservation breakdown** — per pool, stacked committed / flexible / spillover / free.
- **Supply vs allocated vs available** — three series on one chart to separate "no supply" from "supply not allocated."
- **Utilization heatmap** — pool × time, perceptually-uniform scale.

**Drill paths.** Sankey link → reservation breakdown for that pool→cohort edge → the planner run that placed it (planner-explorer) → contention. Low-utilization pool → why (no demand vs constraint-blocked).

**Recurring anti-patterns.** Sankey with no drill (pretty flow, no cause); color-only reservation-state encoding (AC1); CH1 pie for pool composition; conflating "no supply" with "not allocated" by showing only allocated.

**Anchor metrics.** Supply utilization, spillover rate, reservation success/failure, allocation concentration, contention.
