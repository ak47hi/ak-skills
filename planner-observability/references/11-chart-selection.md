# Chart selection

Load when the prompt touches "which chart." Charts are chosen by the **decision** they serve, not by variety. The question is always "what does the reader need to compare or detect," and the chart is whatever makes that comparison fastest and least error-prone.

## Decision → chart table

| Decision the panel serves | Chart | Why this over the alternative |
|---|---|---|
| Track a value over time; spot trend, seasonality, a break | **Line** | Position-along-axis is the most accurately decoded encoding. Bars waste ink for continuous time. |
| Compare delivered vs forecast vs commitment over time | **Multi-line + reference line** | Overlay on shared axis; the gap *is* the signal. `markLine` for the commitment. |
| Show forecast risk / confidence | **Line + uncertainty band** | The band is the hedge information the planner consumes. A bare line implies false certainty. See `12-forecast-explainability.md`. |
| Localize an anomaly across cohort × time | **Heatmap** | Two categorical/ordinal axes + one value; the eye finds the hot cell fast. Perceptually-uniform scale only. |
| Compare a metric across many segments at one time | **Horizontal bar (sorted)** | Length comparison beats angle (pie) and beats vertical bars for long labels. Sort by value, not alphabetically. |
| Cross-segment performance across two dimensions | **Cohort matrix** (table-heatmap hybrid) | Dense; sortable; drillable per cell. Virtualize past ~10k rows. |
| Supply → demand matching, allocation flow, reservation breakdown | **Sankey / allocation-flow** | Shows where inventory went and how much each link carried. The one place flow matters more than time. |
| Same chart across many cohorts for pattern-scanning | **Small multiples** | Shared scales; the eye compares shapes. Beats one overloaded multi-series line. |
| Part-to-whole, few slices, the whole is meaningful | **Stacked bar** (or treemap if many slices) | See the avoid-pie rule below. |
| Distribution of a metric (latency, error) | **Histogram / ECDF**; percentile lines | Mean hides the tail. Show p50/p95/p99 explicitly. |
| Single current value against a target | **KPI stat + sparkline + delta vs target** | A number alone is a vanity metric; the sparkline + target makes it a decision. |
| Two related rates over time at different scales | **Two stacked aligned charts**, shared x-axis | NOT a dual-axis chart — see anti-chartjunk. |

## ECharts mapping

The skill defaults to **ECharts** (`echarts` + `echarts-for-react`). Per chart:

- **Line / multi-line** — `series.type: 'line'`, `dataZoom` for pan/zoom, `markLine` for commitments/SLAs, `markArea` for incident windows or shaded regions.
- **Uncertainty band** — two `line` series (lower, upper) with the upper `stack`ed on the lower and `areaStyle` with opacity, or a single band series; the median line on top. Label the band's quantiles in the legend.
- **Heatmap** — `series.type: 'heatmap'` + `visualMap` with a perceptually-uniform piecewise scale (e.g. viridis-like), not the rainbow default.
- **Bar** — `series.type: 'bar'`, horizontal via swapped `xAxis`/`yAxis` category; sort the data before binding.
- **Sankey** — `series.type: 'sankey'` with `links` carrying allocation volume as `value`; node labels = supply pools / demand cohorts.
- **Large data** — `series.large: true` + `sampling: 'lttb'` (largest-triangle-three-buckets) for dense time-series; downsample server-side past what the canvas can show anyway.
- **Anomaly overlay** — `markPoint` / `markLine` on the primary series rather than a separate panel; the anomaly belongs *on* the metric it perturbs.
- **Events** — deploys, replans, config changes as `markLine` with labels on the time axis, so a reader correlates a metric break with the change that caused it.

D3 is the escape hatch for bespoke visuals ECharts handles awkwardly — a custom allocation-flow with reservation-state coloring, or a linked cohort matrix with in-cell sparklines. Reach for it only when the built-in is genuinely insufficient; the maintenance cost is real.

## The avoid-pie rule

Default: **don't use a pie chart.** Humans decode angle and area far less accurately than position and length (Cleveland & McGill graphical-perception ranking). A sorted horizontal bar conveys the same part-to-whole faster and supports labels, more slices, and precise comparison.

The one carve-out: a strict part-to-whole where the *whole* is the point (e.g. "100% of inventory split across 3 demand classes"), **and** ≤5 slices, **and** the audience expects it (exec convention). Even then, a stacked bar usually reads faster. A donut with a center metric is a stat panel wearing a costume — just use the stat.

Never use pie for: time series, comparisons across >5 categories, anything where slices are close in size, or "share over time" (use a stacked area).

## Anti-chartjunk

- **No dual-axis charts.** Two y-axes invite spurious correlation — the reader sees the lines cross and infers a relationship the axes manufactured. Use two stacked charts with a shared, aligned x-axis instead.
- **No truncated y-axis on counts/volumes.** Starting a bar axis at a non-zero baseline exaggerates differences. (A truncated axis is defensible on a *line* tracking small relative changes — label it.)
- **No rainbow / jet color scales.** They create false boundaries (the eye sees bands where the data is smooth) and fail for colorblind readers. Use perceptually-uniform sequential (viridis, magma) for magnitude and a diverging scale only for signed deviation around a meaningful midpoint.
- **No 3D.** 3D bars/pies distort comparison via perspective and occlusion for zero information gain.
- **No chartjunk.** Gradients, drop shadows, background images, decorative gridlines — every non-data pixel competes with the signal (Tufte's data-ink ratio). Default to spare.
- **No more than ~5-7 series on one line chart.** Past that, switch to small multiples; overlaid spaghetti can't be read.

See `99-citations.md` for Cleveland & McGill, Tufte, Munzner.
