# Category: cohort-explorer

**When it fires.** "Per-segment delivery", "cohort anomalies", "which segments are off", "delivery by group", "high-cardinality segment view". Tier 2.

**Decision it serves.** Planner SRE / analyst: across thousands of cohorts, *which ones* are anomalous, and is it localized (a few cohorts) or systemic (all of them)? The anomaly localizer.

**Key panels + chart choices.**
- **Cohort × time heatmap** — the primary localizer; perceptually-uniform scale (`11` CH4), value = delivery deficit / error / anomaly score. The hot cells are the lead.
- **Cohort matrix / table** — sortable, filterable, **virtualized** past ~10k rows; server-side aggregated past ~100k (`18`). In-cell sparklines for shape.
- **Cross-segment small multiples** — for the top-N anomalous cohorts, the same delivery curve repeated; the eye compares shapes (`11`).
- **Segment breakdown** — delivery by market/device/placement as sorted horizontal bars (NOT pie, CH1).

**Drill paths.** Heatmap hot cell → that cohort's delivery curve (delivery-explorer) → allocation diff (planner-explorer) → root cause. Selection propagates the cohort across all panels (`17`).

**Recurring anti-patterns.** IM2 unvirtualized table; IM3 client-side aggregation; CH4 rainbow heatmap; CH1 pie for segment breakdown; SD4 heatmap with no drill.

**Anchor metrics.** Per-cohort delivery %, anomaly score, error, supply utilization; cardinality and sparsity (which cohorts even have signal).
