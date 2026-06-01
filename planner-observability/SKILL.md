---
name: planner-observability
description: 'Design operational analytics dashboards + observability for forecast / planner / guaranteed-delivery systems — the surfaces an SRE, analyst, or exec uses to root-cause underdelivery, decompose forecast error, watch pacing health, and read delivery risk. Three modes: DESIGN (design doc), PROTOTYPE (runnable Vite + React + TS app), AUDIT (critique an existing dashboard); loads only the touched concern. Decision-first not chart-first; explainability over decoration; drill-down over breadth. Rejects vanity metrics, pie-for-non-part-to-whole, uncalibrated bands, dead-end overviews, alert fatigue, unvirtualized tables. Trigger on: "pacing dashboard", "planner debugging UI", "why-did-we-underdeliver dashboard", "forecast explainability view", "allocation Sankey", "exec delivery KPIs", "anomaly drill-down". Do NOT use for: designing the forecaster/planner itself (use forecast-allocation), generic BI dashboards with no forecast/planner/delivery substrate, raw infra metrics (CPU/mem → Grafana), or auction/bidding.'
---

# planner-observability skill

Design the surfaces you *see a forecast+planner system through*. The forecast estimates supply or demand; the planner allocates scarce supply against committed demand; pacing controls the delivery rate. This skill is the **observability counterpart** to `forecast-allocation`: that skill designs the system, this one designs the dashboards and operational monitoring that let a human reason about it at 3am during an underdelivery incident, in a Monday exec review, or in a forecast post-mortem.

The deliverable is never "a pretty dashboard." It is **decision-making speed, explainability, anomaly detection, and root-cause analysis**. A chart that doesn't change what someone does is deleted, not decorated.

Opinionated about three things:

1. **Decision-first, not chart-first.** Every panel names the decision it accelerates ("is this cohort going to miss its commitment?") or it is cut. A dashboard is a set of answers to questions a named persona asks, not a gallery of the metrics you happen to have.
2. **Explainability over decoration.** A forecast line ships with its uncertainty band *and a calibration note* — an uncalibrated band is worse than none because it lies with confidence. An anomaly ships with its attribution. An error number ships decomposed (bias vs variance). Motion, gradients, and 3D are not explanations.
3. **Drill-down over breadth.** An overview that can't drill is a dead end. Every top-level panel is the entry point to a path that bottoms out at a root cause (overview anomaly → cohort heatmap → allocation diff → reservation reason). Breadth without depth is a status page, not an observability tool.

This is for **operational** analytics — guaranteed delivery, pacing, allocation, forecasting. Not generic BI. If there is no forecast, no planner, and no delivery commitment underneath, this is the wrong skill.

---

## Mode routing

Before phases, name the mode. Most prompts are DESIGN; the others have different deliverables.

| Signal | Mode | Deliverable |
|---|---|---|
| "design a dashboard for X" / "how should we visualize Y" / "what should the planner-debugging UI show" | **DESIGN** | Dashboard + observability design doc (`templates/design-doc.md`) |
| "prototype X" / "give me a React dashboard I can run" / "scaffold the forecast explorer" | **PROTOTYPE** | Runnable Vite + React + TS app: shell + charts + mock data adapter (`templates/prototype/`) |
| "review this dashboard" / "why is this dashboard bad" / "critique our exec view" | **AUDIT** | Findings report: anti-patterns fired + signal-dense replacements (`templates/audit-report.md`) |

When ambiguous, **default to DESIGN with propose-and-go** ("Treating this as a dashboard design request — say so if you want runnable code or a critique of an existing one"). The cost of a wrong mode is one turn; the user corrects.

Cross-cutting rules in every mode:

- The persona + the decision gate the work — no panel, no chart, no layout without knowing *who reads it to decide what* (inferred + flagged is fine).
- Every panel ties to a decision it serves and a density sacrifice it accepts (`references/90-tradeoffs.md`).
- The anti-pattern catalog in `references/93-anti-patterns.md` is walked during OUTPUT.
- Output matches the user's depth. Narrow question ("pie or bar for this?") → narrow answer; full design request → full template.

---

## Six phases

```
1. ELICIT     The gate. Persona + decision + data shape + mode.        references/00-elicitation.md
2. ROUTE      Mode → workflow. Prompt → which concerns + categories.   references/01-routing.md
3. FRAME      Information architecture + chart choice per panel.        references/10-..18-*.md
4. ANALYZE    Scale/cardinality + interaction model + drill paths.     references/90-tradeoffs.md
5. MEASURE    Success metrics + accessibility.                         references/91-success-metrics.md
                                                                       references/94-accessibility.md
6. OUTPUT     Artifact per mode contract; walk anti-patterns.          references/92-output-contracts.md
                                                                       references/93-anti-patterns.md
```

Run in order. Skip a phase only when its output is supplied (user states persona + decision → skip ELICIT; user asks one narrow chart question → skip everything irrelevant to it).

---

## Phase 1: ELICIT (the gate)

**Do not lay out a dashboard before you know who reads it and what they decide.** A planner SRE triaging a live incident and an exec doing a weekly review need opposite surfaces — same data, different density, refresh, and drill depth. Inferred personas are fine — flag them — but a dashboard designed for "everyone" serves no one.

### Seven dimensions to pin down

1. **Persona + the decision.** Planner SRE triaging an incident / analytics engineer doing a forecast post-mortem / product or exec doing periodic review. *And the decision they make.* This is the dominant axis; it reshapes every downstream choice.
2. **Decision latency / urgency.** Real-time incident triage (seconds, auto-refresh, alerting) vs interactive exploration (sub-second filters) vs periodic review (daily/weekly snapshot). Drives refresh cadence, alerting, and density.
3. **Data shape + cardinality.** Cohort/segment count, metric cardinality, time resolution, retention. Drives virtualization, server-side rollups, and how deep drill-down can go before a live query is needed.
4. **Data source + query latency.** TSDB / OLAP (ClickHouse, Druid) / planner audit logs; per-panel query budget. Decides pre-aggregation vs live query.
5. **Drill-down depth.** How far the surface must reach: overview → cohort → allocation → reservation → root cause.
6. **Operational context.** Who maintains it, existing stack and chart lib, embedding constraints.
7. **Signal priorities / SLOs.** Which KPIs are first-class (delivery %, pacing stability, forecast quality, underdelivery risk, utilization, revenue) and their alert thresholds.

### When to skip, ask, or propose-and-go

| Signal in the prompt | Action |
|---|---|
| Persona + decision + data shape all stated | Skip ELICIT. Proceed to ROUTE. |
| One targeted question ("heatmap or small-multiples for cohort×hour anomalies?") | Skip ELICIT. Confirm the binding signal inline (≤1 sentence) and answer narrowly. |
| Three or fewer dimensions missing AND defaults are uncontroversial | Propose-and-go: state inferred defaults in one short block, proceed. |
| Four or more missing OR broadly vague ("build us an observability dashboard") | Ask ONE batched round. Number the questions. Do not iterate. |

**One round, not three.** If the answer is still vague, infer the rest and flag every inference.

**What NOT to ask:** the chart library, the framework, the color palette. Those are decisions the skill makes; the user supplies the persona, the decision, and the data — not the solution.

Full rules + the propose-and-go template live in `references/00-elicitation.md`.

---

## Phase 2: ROUTE

Two routings, applied together.

**Routing A — mode → workflow:**

| Mode | Phase 3 (FRAME) loads | Phase 6 (OUTPUT) emits |
|---|---|---|
| DESIGN | the concern refs the prompt touches | `templates/design-doc.md` |
| PROTOTYPE | the same refs + `18-react-architecture.md` | `templates/prototype/` runnable Vite app |
| AUDIT | `93-anti-patterns.md` + the concern refs the dashboard touches | `templates/audit-report.md` |

**Routing B — prompt intent → which concern reference to load.** Load only what the prompt touches; loading all nine is the failure mode.

| Prompt signals | Load |
|---|---|
| "hierarchy", "overview vs detail", "how many dashboards", "tabs vs pages" | `10-information-arch.md` |
| "which chart", "heatmap", "Sankey", "cohort matrix", "pie", "bar vs line" | `11-chart-selection.md` |
| "actual vs forecast", "uncertainty band", "error decomposition", "feature attribution", "calibration" | `12-forecast-explainability.md` |
| "why underdeliver", "why reserved", "why replan", "allocation flow", "reservation breakdown", "pacing shift" | `13-planner-debugging.md` |
| "health", "latency", "drift", "SLA", "anomaly", "alert", "uptime", "staleness" | `14-observability-health.md` |
| "simulate", "replay", "what-if", "counterfactual", "scenario compare" | `15-simulation-replay.md` |
| "exec", "KPI", "weekly review", "risk summary", "leadership" | `16-executive-reporting.md` |
| "cross-filter", "keyboard nav", "tooltip", "click path", "drill mechanics", "linked brushing" | `17-analytics-ux.md` |
| "React", "component", "TanStack", "Zustand", "ECharts", "virtualize", "data flow" | `18-react-architecture.md` |

Full routing rules + worked examples in `references/01-routing.md`. Dashboard-category detection (executive-overview / forecast-explorer / cohort-explorer / planner-explorer / delivery-explorer / allocation-explorer / simulation-explorer / root-cause-analysis) happens here too — see `references/categories/README.md`. Multi-category hybrids are normal.

---

## Phase 3: FRAME

For each loaded concern, produce:

- **Information architecture.** Where this surface sits in the overview → health → drill-down hierarchy. What it answers, what it links to.
- **Panel set.** Each panel = the decision it serves + the chart type + why that chart beats the alternatives (`references/11-chart-selection.md`). At least one alternative considered and rejected per non-obvious choice.
- **Data binding.** What query feeds it, at what grain, at what refresh.

No code yet (PROTOTYPE mode generates code in OUTPUT, not here).

---

## Phase 4: ANALYZE

Walk three dimensions against the framed surface. Each surfaces a finding recorded in OUTPUT.

1. **Scale + cardinality.** At the cohort count and metric cardinality from ELICIT, does the table need virtualization? Does the heatmap need server-side bucketing? Does a filter change refetch everything? A panel that renders 500k rows client-side is a design bug, not a tuning problem (`references/18-react-architecture.md`).
2. **Interaction model.** Cross-filtering, linked brushing, keyboard navigation for power users, tooltip discipline, drill mechanics (in-place expand over modal). The click path from overview to root cause must be short (`references/17-analytics-ux.md`).
3. **Drill paths.** For each top-level panel, the explicit path down to a root cause. A panel with no drill target is either a dead end (fix it) or genuinely terminal (justify it).

Rules + the decision template live in `references/90-tradeoffs.md`.

---

## Phase 5: MEASURE

Pick the success metrics and check accessibility. **Two things, always:**

- **Success metrics** — time-to-decision, time-to-root-cause, anomaly-detection rate / lead time, mis-triage reduction. A dashboard is an instrument; state how you'd know it works (`references/91-success-metrics.md`). Avoid vanity metrics (page views, "engagement") — they measure the dashboard's popularity, not its decision value.
- **Accessibility** — colorblind-safe palette, WCAG AA contrast, keyboard-first navigation, no color-only encoding (pair color with shape/label/position), chart screen-reader labels + data-table fallback (`references/94-accessibility.md`). Under/over-delivery encoded only as red/green fails for ~8% of male users and every grayscale print.

---

## Phase 6: OUTPUT

Emit the artifact per `references/92-output-contracts.md`:

| Mode | Artifact | Required sections |
|---|---|---|
| DESIGN | `design-doc.md` | Personas • Workflows • Dashboard hierarchy • Panel set with chart rationale (alternatives considered) • Interaction model • Drill-down strategy • Scalability • Accessibility • Implementation (component structure + data flow) • Success metrics |
| PROTOTYPE | `templates/prototype/` | Vite + React + TS app: DashboardShell + ≥1 ECharts panel (forecast-vs-actual with calibrated band) + virtualized cohort table + TanStack Query hooks + Zustand store + deterministic mock adapter. Boots with `npm install && npm run dev`, renders with no backend |
| AUDIT | `audit-report.md` | Findings table (panel → anti-pattern fired → why → fix → severity) • Prioritized remediation • What to keep |

After producing the artifact, **walk the anti-pattern catalog** (`references/93-anti-patterns.md`) against it. Each pattern that fires becomes a fix before emitting (or a noted Open Question). Bans called out explicitly:

- Pie charts for non-part-to-whole comparisons (and even then, prefer bars)
- Vanity metrics (a number with no decision attached)
- Forecast line with no uncertainty band; uncertainty band with no calibration note
- Anomaly flagged with no attribution; error shown without bias/variance decomposition
- Dead-end overview (no drill-down)
- Alert fatigue (alert per blip, no severity tiers or dedup)
- Mean-only latency (no p50/p95/p99); time-series with no event markers
- Unvirtualized high-cardinality table; refetch-all on every filter
- Color-only encoding; contrast below WCAG AA

---

## When to push back

Common smells worth challenging up front. These are conversations, not refusals — if the user has a binding reason, it gets recorded as a tradeoff.

- **"Use a pie chart for the breakdown."** → Humans compare angles worse than lengths (Cleveland & McGill). Use a horizontal bar; a treemap only if it's a strict part-to-whole with many slices. See `references/11-chart-selection.md`.
- **"Make it beautiful / add animations / a 3D globe."** → The goal is decision speed, not delight. Animation delays reading; 3D distorts comparison. Spend the budget on drill-down and explainability instead. See `references/93-anti-patterns.md`.
- **"Put everything on one screen."** → Dashboard sprawl. Without a hierarchy (overview → health → drill-down) the reader can't find the one panel that matters during an incident. See `references/10-information-arch.md`.
- **"Just show the forecast line."** → A point forecast with no band invites false confidence. Show the calibrated interval and a calibration note, or the planner mis-hedges on it. See `references/12-forecast-explainability.md`.
- **"Render all the cohorts in a table."** → At >~10k rows that's a virtualization problem; at >~100k it needs server-side aggregation + drill-down. Rendering all of it freezes the tab. See `references/18-react-architecture.md`.
- **"Alert on every anomaly."** → Alert fatigue trains the on-call to ignore the page. Severity tiers, dedup, and SLO burn-rate thresholds. See `references/14-observability-health.md`.

## When NOT this skill

- **Designing the forecaster or planner itself.** Model choice, pacing algorithm, allocation LP — use `forecast-allocation`. This skill observes that system; it doesn't design it.
- **Generic BI / marketing dashboards.** Funnel analytics, campaign ROAS with no delivery-commitment substrate — a standard BI tool/workflow handles that.
- **Raw infrastructure metrics.** CPU/mem/disk dashboards — standard Grafana/Datadog templates. This skill is about the *forecast-planner-delivery domain*, not host metrics.
- **Auction / real-time bidding UIs.** Different domain (sub-ms, adversarial), different surfaces.

---

## Tone and depth

Terse, professional, no emoji, no decorative filler. Match the user's depth: give experts the tradeoff, not the definition. If the user said "small multiples," don't explain what they are. The output is decisions — which panel, which chart, which drill path — not a visualization textbook. Every paragraph should change what the reader builds.

---

## References at a glance

| File | What it carries |
|---|---|
| `references/00-elicitation.md` | Seven elicitation dimensions, skip/ask/propose-and-go rules, the propose-and-go template. |
| `references/01-routing.md` | Mode-to-workflow table, prompt-intent-to-concern table, dashboard-category detection, worked examples. |
| `references/10-information-arch.md` | The three-tier hierarchy (executive summary → system health → drill-down), one-dashboard-vs-many, tabs vs pages, where the eight categories sit. |
| `references/11-chart-selection.md` | Decision→chart table, ECharts mapping per chart, the avoid-pie rule + carve-out, anti-chartjunk (dual-axis, truncated axes, rainbow scales, 3D). |
| `references/12-forecast-explainability.md` | Actual-vs-forecast overlay, calibrated uncertainty bands, error decomposition (bias/variance/attribution), feature contribution, planner-impact overlay. |
| `references/13-planner-debugging.md` | The five "why" workflows (underdeliver / reserved / allocation changed / pacing shifted / replan fired) as panel sequences; Sankey allocation-flow; allocation-diff; replan timeline. |
| `references/14-observability-health.md` | Health monitors (planner/forecast/allocation/pacing), percentile latency, drift, anomaly overlays, SLA reference lines, alert design without fatigue. |
| `references/15-simulation-replay.md` | Sim-vs-actual overlay, replay timeline scrubber, counterfactual/what-if, scenario compare. |
| `references/16-executive-reporting.md` | KPI curation discipline, exec hierarchy, the exec KPI set, every KPI carries a target/threshold. |
| `references/17-analytics-ux.md` | Cross-filtering, linked brushing, keyboard nav, tooltip discipline, drill mechanics, minimal click paths. |
| `references/18-react-architecture.md` | Component structure, TanStack Query / Zustand data flow, ECharts wrapper, virtualization, query-key design. |
| `references/90-tradeoffs.md` | Decision template — every panel = decision served + accepted density sacrifice. |
| `references/91-success-metrics.md` | Time-to-decision, time-to-root-cause, anomaly-detection rate; vanity-metric bans. |
| `references/92-output-contracts.md` | What each mode's artifact must contain. Maps to `templates/`. |
| `references/93-anti-patterns.md` | The opinionated catalog (chart misuse, vanity metrics, explainability gaps, alert fatigue, interaction, implementation, accessibility, exec). Walked in OUTPUT. |
| `references/94-accessibility.md` | Colorblind-safe palettes, WCAG AA contrast, keyboard-first nav, no color-only encoding, screen-reader labels. |
| `references/99-citations.md` | Annotated sources (Tufte, Few, Cleveland & McGill, Munzner, Grafana/Datadog patterns, Google SRE alerting). Cited by name; loaded only on request. |
| `references/categories/` | Catalog: executive-overview, forecast-explorer, cohort-explorer, planner-explorer, delivery-explorer, allocation-explorer, simulation-explorer, root-cause-analysis. Per category: when it fires, the decision it serves, key panels + chart choices, drill paths, recurring anti-patterns, anchor metrics. |
| `templates/design-doc.md` | DESIGN deliverable skeleton (10 sections). |
| `templates/prototype/` | PROTOTYPE deliverable (runnable Vite + React + TS app). |
| `templates/audit-report.md` | AUDIT deliverable skeleton. |
