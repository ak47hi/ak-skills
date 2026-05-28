# Archetypes index

Forecast + allocation problems cluster into recognizable shapes. A god-tier designer pattern-matches the prompt to one or more archetypes, brings the archetype-specific questions, then designs against the constraints.

This directory is the catalog. Each archetype file documents:

- **When this archetype fires** — signals in the prompt that route here.
- **Additional elicitation** — archetype-specific questions to ask beyond the universal seven dimensions in `00-elicitation.md`.
- **Recurring failure modes** — what tends to break in systems of this shape.
- **What god-tier designers always ask** — questions that catch common wrong defaults.
- **Anchor numbers** — scale thresholds that help calibrate decisions.

## When to load an archetype

During **Phase 2 (ROUTE)** in any mode, after eliciting the universal constraints, check this index for signals. If one or more archetypes fire, load their files and run the archetype-specific elicitation.

If **no archetype fires**, the universal foundation in `SKILL.md` + the loaded research-area references handles it. Most forecast + allocation systems are not exotic; don't force an archetype label.

If **multiple archetypes fire**, load each — most production systems are hybrids (e.g., a capacity-planning problem that's also supply-chain-shaped).

## Routing table

| Signal cues in the prompt | Archetype |
|---|---|
| "guaranteed delivery", "ad-group", "campaign", "impressions", "advertiser commitment", "demand-side platform", "cohort = eligible ad-groups", "pacing for delivery", "underdelivery" | [guaranteed-ad-delivery](guaranteed-ad-delivery.md) |
| "capacity planning", "headroom forecast", "rightsizing", "fleet planning", "cluster sizing", "capacity reservations", "burst headroom" | [capacity-planning](capacity-planning.md) |
| "supply chain", "warehouse", "SKU", "inventory positioning", "fulfillment routing", "shipping origin assignment", "demand-to-warehouse matching" | [supply-chain](supply-chain.md) |
| "scheduler quota", "fair share", "tenant quota", "compute allocation", "job scheduling under quotas", "DRF / dominant resource fairness", "batch job placement" | [scheduler-quotas](scheduler-quotas.md) |

## Archetype list

| Archetype | One-line shape |
|---|---|
| [guaranteed-ad-delivery](guaranteed-ad-delivery.md) | Forecast supply over combinatorial ad-group cohorts; planner allocates to meet contracted impressions per campaign with smooth pacing. The canonical instance. |
| [capacity-planning](capacity-planning.md) | Forecast resource demand; planner allocates capacity (fleet sizing, reservations) to meet SLOs under burst with cost ceiling. |
| [supply-chain](supply-chain.md) | Forecast demand per (SKU, region); planner allocates fulfillment routes / inventory positions to meet demand under shipping + storage constraints. |
| [scheduler-quotas](scheduler-quotas.md) | Forecast tenant resource demand; scheduler allocates compute / IO under per-tenant quotas + fairness constraints + cluster capacity. |

## Anti-pattern: forcing an archetype that doesn't fit

The temptation is to label every system with an archetype because labels feel productive. Resist this. If the prompt is generic forecasting + allocation at modest scale, **no archetype fires** — the universal foundation handles it.

Signs you're forcing an archetype:

- You're loading an archetype file but skipping most of its elicitation questions as "not applicable."
- The archetype's failure modes don't match the user's concerns.
- The archetype's anchor numbers are several orders of magnitude away from the user's scale.

When this happens, drop the archetype and stay with the universal foundation.
