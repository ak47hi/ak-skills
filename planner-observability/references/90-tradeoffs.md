# Tradeoffs

Load in Phase 4 (ANALYZE). Every panel and every dashboard-level choice is a tradeoff: it serves a decision and accepts a sacrifice. Recording both is what separates a designed surface from an accreted one.

## The decision template

For each non-obvious choice, record:

- **Decision served.** The specific question this panel/choice answers for the named persona. If you can't name it, cut the panel.
- **Accepted sacrifice.** What this choice costs — density, drill granularity, freshness, build complexity, screen real estate.
- **Reversal cost.** Cheap to change later (a chart type) or load-bearing (the pre-aggregation grain that caps drill depth)?
- **The trigger that would force a change.** The signal that says this choice stopped working.

## Worked examples

**Pre-aggregated 1-hour rollups for the exec summary.**
- *Decision served:* leadership reads delivery-vs-commitment at a glance with sub-second load.
- *Sacrifice:* can't drill below 1-hour grain without firing a separate live query.
- *Reversal:* moderate — adding a finer rollup is a backend job, not a redesign.
- *Trigger:* on-call repeatedly needs minute-grain from the exec view → add a drill-through live query, don't lower the rollup grain for everyone.

**Heatmap (not small-multiples) for cohort × hour anomalies.**
- *Decision served:* localize an anomaly across 20k cohorts × 24 hours fast — find the hot cell.
- *Sacrifice:* loses the per-cohort *shape* over time that small-multiples would show.
- *Reversal:* cheap — it's a chart swap.
- *Trigger:* readers keep drilling every hot cell to a line chart anyway → the shape is what they want; reconsider.

**Virtualized client table (not server-side aggregation) at 20k cohorts.**
- *Decision served:* full sortable/filterable cohort table with instant interaction at a tractable size.
- *Sacrifice:* fetches all 20k rows; won't scale to 1M.
- *Reversal:* expensive — moving to server-side pagination changes the data layer and the query shape.
- *Trigger:* cohort count crosses ~100k or fetch latency degrades → go server-side (`18-react-architecture.md`).

## The density tradeoff specifically

Signal density is the recurring axis. More panels per screen = more context visible at once = better for an SRE mid-incident; but past a threshold it's sprawl that hides the one panel that matters. The resolution is the **hierarchy** (`10-information-arch.md`), not a density dial: dense where the persona scans (Tier 2 health grid), sparse where they decide (Tier 1 exec). Record the choice — "Tier 2 is intentionally dense because the on-call trades legibility for coverage during triage" — so a reviewer doesn't mistake density for carelessness.

## How this feeds OUTPUT

Each recorded tradeoff becomes a line in the design doc's "chart rationale" and "scalability" sections (alternatives considered + why rejected), and a candidate Open Question where the trigger is plausible. A design that states only what it chose, never what it sacrificed, hasn't been analyzed — it's been asserted.
