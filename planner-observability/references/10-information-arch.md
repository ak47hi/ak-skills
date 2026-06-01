# Information architecture

Load when the prompt touches structure: how many dashboards, overview vs detail, tabs vs pages, where a surface lives.

## The three-tier hierarchy

Operational analytics for a forecast+planner system organizes into three tiers. The reader enters at the tier matching their decision latency and drills down.

```
Tier 1  EXECUTIVE SUMMARY    "Are we on track? Where's the risk?"
        6-9 KPIs vs targets, trend, risk. No operational detail.
          │  drill: click a red KPI →
Tier 2  SYSTEM HEALTH         "Which subsystem / cohort / window is off?"
        Delivery, pacing, forecast quality, allocation health.
        Anomaly overlays. Per-cohort heatmaps. SLA reference lines.
          │  drill: click an anomaly cell →
Tier 3  DRILL-DOWN / ROOT CAUSE  "Why is this one thing off?"
        Per-cohort delivery curve, allocation diff, reservation reason,
        forecast error decomposition, replan timeline.
```

The tiers are not three dashboards you build independently — they are **one navigable surface** where every Tier-1 panel links into Tier-2 and every Tier-2 anomaly links into Tier-3. Breadth at the top, depth on demand. An overview that can't drill is a status page; a drill-down with no overview is a query console. The value is the path between them.

## One dashboard vs many

| Situation | Structure |
|---|---|
| One persona, one decision loop | One dashboard, three tiers as scroll regions or a master-detail layout. |
| Distinct personas (SRE vs exec) | Separate top-level dashboards, **linked** — the exec KPI deep-links into the SRE health view at the same time range + filter. Don't merge densities. |
| Distinct subsystems (forecast / pacing / allocation) | Tabs within Tier 2, not separate dashboards — the on-call switches subsystems mid-incident without losing context (time range, cohort filter). |

**Rule:** split by *persona* (different density, different refresh), tab by *subsystem* (same persona, same incident, different lens). Never split by metric — "a dashboard per metric" fragments the one view where correlations live.

## Tabs vs pages vs scroll

- **Scroll regions** for the three tiers when one persona reads top-to-bottom (exec summary at top, drill below). Preserves context; no navigation cost.
- **Tabs** for sibling subsystems at the same tier (forecast | pacing | allocation health). State (time range, cohort filter, selected cohort) is **shared across tabs** — switching tabs is changing the lens, not resetting the investigation.
- **Pages / routes** only across personas or across genuinely separate workflows (live monitoring vs historical post-mortem). A route change is allowed to reset some state; a tab change is not.

## Context that must persist across the hierarchy

Three pieces of state follow the reader down every drill and across every tab, or the investigation resets each click:

1. **Time range** — set once at the top, inherited everywhere. The single most common IA bug is a drill-down that snaps back to "last 24h" and loses the incident window.
2. **Cohort / segment filter** — drilling into a cohort from the heatmap carries that cohort into the delivery curve and the allocation diff.
3. **Selected anomaly / event** — the thing the reader clicked is highlighted (via `markLine`/`markPoint`) in every panel it appears in.

Implementation of this shared state lives in `18-react-architecture.md` (Zustand store for filter/time/selection; TanStack Query keyed on it).

## Where the eight categories sit

| Category | Tier | Role |
|---|---|---|
| executive-overview | 1 | The KPI summary; the entry point for leadership. |
| delivery-explorer | 2 | Delivery + pacing health; entry for "are commitments being met." |
| forecast-explorer | 2 → 3 | Forecast quality at Tier 2; error decomposition at Tier 3. |
| cohort-explorer | 2 | Per-segment heatmap; the anomaly localizer. |
| planner-explorer | 2 → 3 | Allocation plans + planner decisions; reservation detail at Tier 3. |
| allocation-explorer | 3 | Supply→demand flow (Sankey), reservation breakdown. |
| simulation-explorer | side | What-if / replay; a parallel surface, not in the live drill path. |
| root-cause-analysis | 3 | The terminal tier — the assembled drill path from anomaly to cause. |

`root-cause-analysis` is less a separate dashboard than the *path* Tier-1 and Tier-2 panels lead into. Design it as the spine: every anomaly in the system should have a drill route that ends in one of its panels.
