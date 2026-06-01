# Anti-patterns

Load during **Phase 6 (OUTPUT)**. Walk every pattern against the artifact; each that fires is fixed (DESIGN/PROTOTYPE) or *is the finding* (AUDIT). In AUDIT mode this catalog is the rubric.

Each entry: **symptom** (how it shows up), **why bad** (the failure mode), **ask instead** (the redirect).

## Chart misuse

### CH1. Pie chart for non-part-to-whole
**Symptom.** A pie/donut comparing categories that aren't a meaningful whole, or with >5 slices, or for share-over-time.
**Why bad.** Angle/area are decoded far less accurately than length/position (Cleveland & McGill). Close slices are indistinguishable; labels don't fit; trends are invisible.
**Ask instead.** Sorted horizontal bar. Stacked bar or treemap only for a genuine part-to-whole with the whole meaningful. Stacked area for share-over-time. See `11-chart-selection.md`.

### CH2. Dual-axis chart
**Symptom.** One chart, two y-axes, two series at different scales.
**Why bad.** The crossing point and relative slopes are artifacts of the chosen axis scales — the chart manufactures a correlation the data may not have.
**Ask instead.** Two stacked charts sharing an aligned x-axis. See `11-chart-selection.md`.

### CH3. 3D charts
**Symptom.** 3D bars, 3D pie, perspective.
**Why bad.** Perspective and occlusion distort comparison for zero information gain.
**Ask instead.** The 2D form. Always.

### CH4. Rainbow / jet color scale for magnitude
**Symptom.** A heatmap on the default rainbow scale.
**Why bad.** Non-perceptually-uniform — the eye sees false boundaries where data is smooth, and it fails for colorblind readers.
**Ask instead.** Perceptually-uniform sequential (viridis/magma) for magnitude; a diverging scale only around a meaningful midpoint (e.g. signed deviation). See `94-accessibility.md`.

### CH5. Truncated axis on counts / chartjunk
**Symptom.** Bar axis not starting at zero; gradients, shadows, background images, heavy gridlines.
**Why bad.** Truncated count-bars exaggerate differences; decoration competes with signal (Tufte data-ink).
**Ask instead.** Zero-baseline for bars; spare styling. A truncated axis is defensible on a *line* of small relative changes — label it.

## Signal density

### SD1. Vanity metric
**Symptom.** A number with no decision attached ("4.2M impressions delivered") and no target/trend.
**Why bad.** It looks informative and isn't — the reader can't tell good from bad without a reference.
**Ask instead.** Attach a target and a trend, or cut it. "4.2M vs 4.0M commitment, ↑3% wk/wk" is a decision. See `16-executive-reporting.md`, `91-success-metrics.md`.

### SD2. Hero number with no context
**Symptom.** A giant single stat, no sparkline, no comparison.
**Why bad.** Level without trend or target isn't actionable.
**Ask instead.** Stat + sparkline + delta-vs-target.

### SD3. Dashboard sprawl
**Symptom.** 30 panels, no hierarchy, everything on one screen.
**Why bad.** During an incident the reader can't find the one panel that matters. Breadth hides signal.
**Ask instead.** The three-tier hierarchy (overview → health → drill-down); split by persona, tab by subsystem. See `10-information-arch.md`.

### SD4. Dead-end overview
**Symptom.** A summary panel with no drill-down.
**Why bad.** "The metric is red" with no path to "because cohort X's supply forecast was high" is half a tool — a status page, not an observability surface.
**Ask instead.** Every Tier-1 panel links into Tier-2; every Tier-2 anomaly into Tier-3 root cause. See `13-planner-debugging.md`.

## Explainability

### EX1. Forecast line with no uncertainty band
**Symptom.** A bare forecast line.
**Why bad.** Implies false certainty; the planner consuming it can't see the risk it should hedge.
**Ask instead.** Show the calibrated interval (e.g. p10–p90). See `12-forecast-explainability.md`.

### EX2. Uncertainty band with no calibration note
**Symptom.** A shaded band with no statement of whether it's calibrated.
**Why bad.** An uncalibrated band is *worse* than none — it lies with confidence, and the planner mis-hedges against it.
**Ask instead.** Annotate empirical coverage vs target ("p10–p90, coverage 0.87/0.80 trailing 14d"), per-cohort-tier. If unmeasured, say so loudly. See `12-forecast-explainability.md`.

### EX3. Anomaly flagged with no attribution
**Symptom.** A red dot / alert that says "anomaly" but not where or why.
**Why bad.** An alarm with no address — the reader still has to do all the localization work.
**Ask instead.** Attribution attached: which cohort, which input, which window. Overlay it *on* the perturbed metric. See `14-observability-health.md`.

### EX4. Error shown without bias/variance decomposition
**Symptom.** A single RMSE / "8% off" number.
**Why bad.** Doesn't tell you the fix — bias (systematic, fix the model) vs variance (noisy, widen the hedge) vs where it concentrates.
**Ask instead.** Decompose into signed bias, variance, and an attribution heatmap (cohort × horizon). See `12-forecast-explainability.md`.

## Observability

### OB1. Mean-only latency
**Symptom.** Latency shown as a single average line.
**Why bad.** The mean launders the tail — a p99 timeout that causes the incident is invisible.
**Ask instead.** p50/p95/p99 as separate lines with the SLA `markLine`. See `14-observability-health.md`.

### OB2. Health chart with no SLA reference line
**Symptom.** A metric time-series with no threshold drawn on it.
**Why bad.** Forces the reader to remember the SLO; "480ms" isn't a decision without "SLA is 500."
**Ask instead.** SLO as `markLine`, error budget as `markArea`.

### OB3. Anomalies in a separate tab
**Symptom.** An anomaly list divorced from the metrics it perturbs.
**Why bad.** Forces the reader to re-correlate "anomaly at 14:32" with what the metric was doing — the work the overlay should do.
**Ask instead.** Overlay anomalies on the primary chart (`markArea`/`markPoint`).

### OB4. Alert fatigue
**Symptom.** Alert on every blip; no severity tiers; no dedup; alerting on causes not symptoms.
**Why bad.** Trains the on-call to ignore the page; the real incident gets missed.
**Ask instead.** Severity tiers, symptom-based alerts, burn-rate/multi-window thresholds, dedup, every alert links to its drill path. See `14-observability-health.md`.

### OB5. Time-series with no event markers
**Symptom.** A metric break with no deploys/replans/config-changes annotated.
**Why bad.** The reader sees the break but not the change that caused it — re-correlation by hand.
**Ask instead.** Events as `markLine` on the time axis.

## Interaction

### IN1. No cross-filtering
**Symptom.** Panels are independent widgets; a filter on one doesn't affect the others.
**Why bad.** The correlations that explain an incident live *across* panels; without linked context they're invisible.
**Ask instead.** Global filter + linked brushing + selection propagation. See `17-analytics-ux.md`.

### IN2. Mouse-only
**Symptom.** No keyboard navigation.
**Why bad.** Slow for the power user who lives in the dashboard; inaccessible for keyboard/AT users.
**Ask instead.** `/` `j` `k` Enter `[` `]` `Esc` `?`. See `17-analytics-ux.md`, `94-accessibility.md`.

### IN3. Critical value hidden behind hover
**Symptom.** Must hover each element to read the number you need to decide.
**Why bad.** Hostile to scanning; the headline value should be readable at a glance.
**Ask instead.** Critical values as labels/ticks; hover for secondary detail only.

### IN4. Modal-heavy drill
**Symptom.** Drilling opens a modal that covers the overview.
**Why bad.** Breaks the investigation flow; loses the context that made the anomaly legible.
**Ask instead.** Expand in place / side panel; breadcrumbs; `Esc` pops one level.

## Implementation

### IM1. Refetch-all on every filter
**Symptom.** Changing a filter refetches every panel (one giant query, or keys including everything).
**Why bad.** Sluggish; it's a query-key design bug, not a backend-speed problem.
**Ask instead.** Query keys encode exactly each panel's dependencies. See `18-react-architecture.md`.

### IM2. Unvirtualized high-cardinality table
**Symptom.** Rendering all rows of a 100k-row cohort table.
**Why bad.** Freezes the tab, blows memory.
**Ask instead.** `@tanstack/react-virtual` past ~10k rows; server-side aggregation + windowed query past ~100k. See `18-react-architecture.md`.

### IM3. Client-side aggregation of high-cardinality data
**Symptom.** Fetching a million raw rows to sum/group them in the browser.
**Why bad.** Wasteful and slow; the browser is the wrong place to aggregate.
**Ask instead.** Aggregate in the OLAP store; fetch the rollup; drill on demand.

### IM4. Server state in a global store
**Symptom.** Fetched data in Zustand/Redux with hand-managed refetch.
**Why bad.** Reimplements caching/dedup/staleness — badly.
**Ask instead.** TanStack Query for server state; Zustand for UI state only. See `18-react-architecture.md`.

## Accessibility

### AC1. Color-only encoding
**Symptom.** Under/over-delivery (or healthy/breaching) shown only as red/green.
**Why bad.** Fails for ~8% of male users and every grayscale context.
**Ask instead.** Pair color with shape, label, or position. See `94-accessibility.md`.

### AC2. Contrast below WCAG AA
**Symptom.** Light-gray text/series on white; thin low-contrast lines.
**Why bad.** Unreadable for low-vision users and on glare-y on-call screens.
**Ask instead.** ≥4.5:1 for text, ≥3:1 for graphical objects.

### AC3. Chart with no text alternative
**Symptom.** A canvas chart with no SR label, no data-table fallback.
**Why bad.** Invisible to screen readers; the data is locked in pixels.
**Ask instead.** `aria-label` summary + a toggleable data table. See `94-accessibility.md`.

## Executive

### EXEC1. Operational detail in an exec view
**Symptom.** Per-cohort latency, solve times, individual replans on the leadership surface.
**Why bad.** Leadership can't act on it; it's the noise that makes them distrust the dashboard.
**Ask instead.** Curate to the 6-9 decision KPIs; push detail to Tier 2 with a drill-through. See `16-executive-reporting.md`.

### EXEC2. KPI with no target
**Symptom.** An exec stat with no threshold/target.
**Why bad.** A vanity metric (see SD1) wearing an exec hat — no good/bad reference.
**Ask instead.** Every KPI carries its target and delta.

### EXEC3. Status without risk
**Symptom.** Current delivery shown; forecasted underdelivery omitted.
**Why bad.** Execs steer on leading indicators; status is lagging.
**Ask instead.** Lead with forecasted risk; show the trend.
