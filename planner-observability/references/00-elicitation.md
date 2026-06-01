# Elicitation

Load at the start of every request. Decides whether to skip, ask, or propose-and-go before laying out anything.

## The gate

The persona and the decision come first. A dashboard designed without knowing *who reads it to decide what* is a gallery, not an instrument. The same delivery data becomes three different surfaces depending on the reader: a planner SRE wants a dense incident-triage view with drill-to-root-cause; an analytics engineer wants a forecast post-mortem with error decomposition; an exec wants six KPIs against targets and nothing else. **Inferred personas are fine — flag them as assumptions** — but "a dashboard for everyone" serves no one.

This is the same discipline as `forecast-allocation`'s "numbers first": there, cohort cardinality reshapes the model before any chart. Here, the persona reshapes the layout before any panel.

## Seven dimensions

For every request, these are the minimum the design needs. They map directly to the OUTPUT sections, so missing dimensions become "Open questions" in the artifact.

### 1. Persona + the decision

The dominant axis. Name the reader **and** the decision they make on this surface.

- **Planner SRE / on-call.** Decision: is this incident real, where is it, what's the root cause, do I page or roll back? Needs density, real-time refresh, drill-to-root-cause, alerting.
- **Analytics engineer / data scientist.** Decision: why did the forecast miss, is it bias or variance, which feature drifted, does the fix actually help? Needs error decomposition, calibration views, slicing, comparison.
- **Product lead / exec.** Decision: are we on track to meet commitments, what's the risk, where do I spend attention? Needs curated KPIs against targets, trend, risk — and nothing operational.

A surface that tries to serve all three blends densities and serves none. If the prompt genuinely needs all three, that's *three linked dashboards in a hierarchy*, not one.

### 2. Decision latency / urgency

- **Real-time incident triage** — seconds matter; auto-refresh, alerting, live queries, anomaly overlays.
- **Interactive exploration** — sub-second filters; pre-aggregated, cached, cross-filtered.
- **Periodic review** — daily/weekly snapshot; can be a generated report, no live refresh.

Urgency drives refresh cadence, whether alerting exists, and how much you pre-compute.

### 3. Data shape + cardinality

- **Cohort/segment count.** 10², 10⁴, 10⁶? Drives whether the cohort table needs virtualization or server-side aggregation.
- **Metric cardinality.** How many series, dimensions, tags.
- **Time resolution + retention.** 1-minute for 7 days vs 1-hour for 2 years — decides rollup strategy and what drill granularity is even available.

### 4. Data source + query latency

- **Backend.** Time-series DB (Prometheus, InfluxDB), OLAP (ClickHouse, Druid, BigQuery), planner audit logs, or a mix.
- **Per-panel query budget.** A 50 ms pre-aggregated rollup is a different panel from a 5 s live scan. Decides pre-aggregation vs live query, and which drill levels need a spinner.

### 5. Drill-down depth

How far the surface must reach: overview anomaly → cohort heatmap → per-cohort delivery curve → allocation diff → reservation reason. Each level is a query and a panel. A surface that stops at "the metric is red" without a path to "because cohort X's supply forecast was 30% high" is half a tool.

### 6. Operational context

- Who builds and maintains it; their stack and existing chart lib.
- Embedding constraints (standalone app vs embedded in an existing console).
- Existing dashboards to extend or replace.

### 7. Signal priorities / SLOs

- Which KPIs are first-class: delivery %, pacing stability, forecast quality (calibration/accuracy), underdelivery risk, inventory utilization, revenue impact.
- The SLOs and alert thresholds attached to each. "Underdelivery p95 ≤ 2%" is the reference line that turns a time-series into a decision surface.

## Decision rules: skip, ask, propose-and-go

| Signal in the prompt | Action |
|---|---|
| Persona + decision + data shape stated or derivable | Skip ELICIT. Go to ROUTE. |
| Narrow targeted question ("heatmap or small-multiples for cohort×hour anomalies?") | Skip the full elicitation; confirm the binding signal inline in one sentence, answer narrowly. |
| Three or fewer dimensions missing AND defaults are uncontroversial | **Propose-and-go**: state inferred defaults in one short block, proceed. |
| Four or more dimensions missing OR broadly vague ("build us an observability dashboard") | Ask ONE batched round. Number the questions. Do not iterate. |

**One round, not three.** Every clarifying round burns trust. If round 1 is still vague, infer the rest and flag the inferences in the artifact.

## Propose-and-go template

> Treating this as: planner-SRE incident-triage surface, real-time (15 s refresh), ~20k cohorts (cohort table virtualized, server-side rollups for the heatmap), ClickHouse backend with a ~300 ms panel budget, drill from overview → cohort heatmap → delivery curve → allocation diff, first-class signals delivery % and underdelivery risk against a p95 ≤ 2% SLO. Proceeding — correct any of these.

Short, numbered, replaceable. Don't dress it up.

## What NOT to ask

- The chart library (ECharts vs Highcharts) — the skill's job.
- The framework, the color palette, the CSS approach — implementation, not constraint.
- Multiple-choice questions that bias the answer ("Do you want a heatmap or a Sankey?" — ask what decision the panel serves, not which chart).

## Category detection in ELICIT

After the seven dimensions are pinned (or inferred), check `categories/README.md` for the dashboard-category signals. A request often maps to one or two categories (e.g. "why did we underdeliver" → root-cause-analysis + planner-explorer). Loading a category adds 2-3 category-specific panels and drill paths. **Don't force a category** if the prompt is a generic observability surface; the universal seven dimensions cover it.

## When the user pushes back on the elicitation

If the user says "skip the questions, just design it" — skip. Use defaults, flag every inferred value in the OPEN QUESTIONS section of the artifact. The user corrects on the next turn. **Don't loop the elicitation** because the answers were terse; that's not the user's job to fix.
