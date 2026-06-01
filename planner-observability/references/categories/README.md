# Dashboard-category catalog

Detected in ELICIT/ROUTE. A category is a recurring surface bundled as: panels + chart choices + drill paths + recurring anti-patterns + anchor metrics. Most requests map to one or two; multi-category hybrids are normal (e.g. "why did we underdeliver" = root-cause-analysis entered from delivery-explorer + planner-explorer).

**Don't force a category** if the prompt is a generic observability surface — the universal concern refs (`10`–`18`) cover it. Load a category file only when the request clearly is that surface.

## Detection table

| Request smells like | Category | File |
|---|---|---|
| "leadership KPIs", "are we on track", "delivery health at a glance" | executive-overview | `executive-overview.md` |
| "actual vs forecast", "forecast accuracy", "calibration", "error attribution" | forecast-explorer | `forecast-explorer.md` |
| "per-segment delivery", "cohort anomalies", "which segments are off" | cohort-explorer | `cohort-explorer.md` |
| "planner decisions", "allocation plan", "reservation details", "what did the planner do" | planner-explorer | `planner-explorer.md` |
| "delivery curves", "pacing", "under/over-delivery", "SLA tracking" | delivery-explorer | `delivery-explorer.md` |
| "supply→demand matching", "allocation flows", "reservation breakdown" | allocation-explorer | `allocation-explorer.md` |
| "simulated vs actual", "replay", "what-if", "scenario" | simulation-explorer | `simulation-explorer.md` |
| "drill to root cause", "anomaly triage", "why did X happen" | root-cause-analysis | `root-cause-analysis.md` |

## Tier placement (from `10-information-arch.md`)

| Category | Tier |
|---|---|
| executive-overview | 1 (entry for leadership) |
| delivery-explorer, cohort-explorer, forecast-explorer | 2 (system health) |
| planner-explorer, allocation-explorer, root-cause-analysis | 2→3 / 3 (drill-down) |
| simulation-explorer | side (off the live path) |

## Per-category file shape

Each file carries:
- **When it fires** — the signals that select it.
- **The decision it serves** — the persona + question.
- **Key panels + chart choices** — with the reference that governs each.
- **Drill paths** — where each panel goes down.
- **Recurring anti-patterns** — the ones this surface gets wrong most.
- **Anchor metrics** — the first-class signals.
