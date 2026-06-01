# Category: delivery-explorer

**When it fires.** "Delivery curves", "pacing", "under/over-delivery", "SLA tracking", "are commitments being met". Tier 2.

**Decision it serves.** Planner SRE / analyst: is delivery on pace against commitment, where is it falling behind, and is the pacing the cause? The primary "are we meeting commitments" surface.

**Key panels + chart choices.**
- **Delivery curve** — cumulative delivered vs commitment vs ideal pace; `markArea` the shortfall window; commitment as `markLine` (`11`, `13`).
- **Pacing trace** — per-tick pace rate vs target, beneath the delivery curve so the mechanism sits under the symptom.
- **Under/over-delivery distribution** — across commitments, p50/p95 (not mean), against the SLO (`14` OB1/OB2).
- **SLA tracking** — % of commitments meeting SLO over time, with the SLO reference line.

**Drill paths.** Delivery shortfall → pacing trace → forecast error (forecast-explorer) → supply shortfall vs allocation failure (the four-cause split in `13`). Cohort selection carries through.

**Recurring anti-patterns.** Delivery curve with no pacing trace (symptom without mechanism); mean-only under/over-delivery (OB1); no SLA reference line (OB2); EX-class forecast gaps when the forecast overlay is added.

**Anchor metrics.** Delivery % vs commitment, pace adherence, under/over-delivery p95, SLA-violation rate.
