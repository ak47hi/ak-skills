# Routing

Load in Phase 2. Two routings applied together: mode → workflow, and prompt-intent → which concern references to load. Plus dashboard-category detection.

## Routing A — mode → workflow

| Mode | Trigger phrasing | FRAME loads | OUTPUT emits |
|---|---|---|---|
| **DESIGN** | "design a dashboard for…", "how should we visualize…", "what should the X view show" | the concern refs the prompt touches | `templates/design-doc.md` |
| **PROTOTYPE** | "prototype…", "scaffold the…", "give me a React dashboard I can run" | the touched concern refs **+** `18-react-architecture.md` | `templates/prototype/` runnable Vite app |
| **AUDIT** | "review this dashboard", "why is this bad", "critique our exec view" | `93-anti-patterns.md` **+** the concern refs the dashboard touches | `templates/audit-report.md` |

Default to DESIGN with propose-and-go when ambiguous.

## Routing B — prompt intent → concern reference

Load only what the prompt touches. Loading all nine is the failure mode — it produces a generic everything-dashboard instead of the one surface the persona needs.

| Prompt signals | Load | Why |
|---|---|---|
| "hierarchy", "overview vs detail", "how many dashboards", "tabs vs pages", "where does X live" | `10-information-arch.md` | Structure decision precedes panel decisions. |
| "which chart", "heatmap", "Sankey", "cohort matrix", "pie", "bar vs line", "treemap" | `11-chart-selection.md` | Chart-by-decision rules + ECharts mapping. |
| "actual vs forecast", "uncertainty", "confidence interval", "error decomposition", "feature attribution", "calibration", "bias" | `12-forecast-explainability.md` | Forecast-specific explainability panels. |
| "why underdeliver", "why reserved", "why replan", "allocation flow", "reservation breakdown", "pacing shift", "allocation diff" | `13-planner-debugging.md` | The five "why" root-cause workflows. |
| "health", "latency", "drift", "SLA", "anomaly", "alert", "uptime", "staleness", "oscillation" | `14-observability-health.md` | Operational monitoring + alert design. |
| "simulate", "replay", "what-if", "counterfactual", "scenario", "before/after a change" | `15-simulation-replay.md` | Sim/replay surfaces. |
| "exec", "KPI", "weekly review", "risk summary", "leadership", "one-pager" | `16-executive-reporting.md` | Curated KPI surface. |
| "cross-filter", "keyboard", "tooltip", "click path", "drill mechanics", "linked", "brushing" | `17-analytics-ux.md` | Interaction model. |
| "React", "component", "TanStack", "Zustand", "ECharts", "virtualize", "data flow", "state" | `18-react-architecture.md` | Implementation. Always loaded in PROTOTYPE. |

Support refs (`90-tradeoffs`, `91-success-metrics`, `92-output-contracts`, `93-anti-patterns`, `94-accessibility`) load by phase, not by intent: 90 in ANALYZE, 91+94 in MEASURE, 92+93 in OUTPUT. `99-citations` loads only on explicit request for sources.

## Dashboard-category detection

Map the request to one or two categories from `categories/README.md`. Categories are bundles of panels + drill paths for a recurring surface. Multi-category hybrids are normal — "why did we underdeliver" is root-cause-analysis entered from a delivery-explorer.

| Request smells like | Category |
|---|---|
| "leadership KPIs", "are we on track", "delivery health at a glance" | executive-overview |
| "actual vs forecast", "forecast accuracy", "calibration", "error attribution" | forecast-explorer |
| "per-segment delivery", "cohort anomalies", "which segments are off" | cohort-explorer |
| "planner decisions", "allocation plan", "reservation details" | planner-explorer |
| "delivery curves", "pacing", "under/over-delivery", "SLA tracking" | delivery-explorer |
| "supply→demand matching", "allocation flows", "reservation breakdown" | allocation-explorer |
| "simulated vs actual", "replay", "what-if", "scenario" | simulation-explorer |
| "drill to root cause", "anomaly triage", "why did X happen" | root-cause-analysis |

## Worked examples

**"Design a dashboard so on-call can see why a campaign underdelivered."**
Mode DESIGN. Intent → `13-planner-debugging` (the why-underdeliver workflow) + `14-observability-health` (anomaly overlays) + `11-chart-selection` (delivery curve, allocation Sankey) + `17-analytics-ux` (drill mechanics). Categories: root-cause-analysis (primary) entered from delivery-explorer + planner-explorer. OUTPUT: design doc whose drill-down section is the underdeliver workflow end to end.

**"Scaffold a React forecast explorer with actual-vs-forecast and a cohort table."**
Mode PROTOTYPE. Intent → `12-forecast-explainability` + `11-chart-selection` + `18-react-architecture` (always in PROTOTYPE). Category: forecast-explorer. OUTPUT: the `templates/prototype/` app with the forecast-vs-actual ECharts panel (calibrated band) + virtualized cohort table.

**"Is a pie chart fine for delivery-by-channel?"**
Narrow question — skip ELICIT and most of ROUTE. Intent → `11-chart-selection` only. Chat-mode answer: no, use a horizontal bar (Cleveland & McGill); pie only as a strict part-to-whole with ≤5 slices and even then bars read faster. No template.

**"Review our exec dashboard — leadership says it's noisy."**
Mode AUDIT. Load `93-anti-patterns` + `16-executive-reporting`. Category: executive-overview. OUTPUT: audit-report flagging operational-detail leakage, KPIs with no targets, and vanity metrics, with signal-dense replacements.
