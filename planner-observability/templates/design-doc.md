# Dashboard design: <surface name>

Owner: <name or team>
Date: YYYY-MM-DD
Status: Draft | Reviewed | Approved | Superseded

---

## 1. Personas

Who reads this and the decision each makes. Named, with the decision — not "stakeholders."

| Persona | Decision they make here | Decision latency |
|---|---|---|
| <e.g. Pacing on-call> | <e.g. is this incident real, where, why, page or roll back> | real-time |
| <e.g. Forecast analyst> | <e.g. is the miss bias or variance, which feature drifted> | interactive |
| <e.g. Delivery exec> | <e.g. are we on track, what's the risk> | weekly |

## 2. Workflows

The top 2-3 investigations as step-by-step paths with decision points. Per `references/13-planner-debugging.md` where applicable.

**Workflow A — <e.g. why did we underdeliver>:**
1. <entry panel> → observe <signal>
2. drill → <next panel> → decide <branch>
3. … → root cause: <one of N causes> → action

## 3. Dashboard hierarchy

The three-tier structure (`references/10-information-arch.md`). One dashboard vs many; tabs vs pages.

```
Tier 1 EXECUTIVE SUMMARY  <what lives here>
  │ drill →
Tier 2 SYSTEM HEALTH      <subsystem tabs>
  │ drill →
Tier 3 DRILL-DOWN         <root-cause panels>
```

Shared state persisted across tiers/tabs: time range, cohort filter, selection.

## 4. Panel set with chart rationale

Each panel: decision served + chart type + ≥1 alternative considered and rejected (`references/11-chart-selection.md`, `references/90-tradeoffs.md`).

| Panel | Decision served | Chart | Alternative rejected (why) | Ref |
|---|---|---|---|---|
| <Forecast vs actual> | <is the forecast trustworthy here> | line + calibrated band + SLA markLine | bare line (false certainty) | `12` |
| <Cohort anomalies> | <which segments are off> | heatmap (viridis) | small-multiples (doesn't scale to 20k) | `11`,`cohort-explorer` |
| <Allocation flow> | <where did supply go> | Sankey | stacked bar (loses flow) | `13`,`allocation-explorer` |

## 5. Interaction model

Per `references/17-analytics-ux.md`: global filter + linked brushing; selection propagation; keyboard map (`/ j k Enter [ ] Esc ?`); tooltip discipline (critical values as labels, not hover); drill mechanics (in-place over modal; breadcrumbs).

## 6. Drill-down strategy

The explicit anomaly→root-cause path for each top-level panel (`references/categories/root-cause-analysis.md`):
```
overview anomaly → cohort heatmap → delivery+pacing → allocation diff → forecast/feature attribution → cause
```
Confirm every anomaly the surface can raise has a route onto this spine. Path length ≤3 clicks to first cause.

## 7. Scalability

At <cohort cardinality> cohorts, <metric cardinality>, <retention>:
- Cohort table: <virtualized / server-side> (`references/18-react-architecture.md`).
- Heatmap: <client / server-side bucketed>.
- Query keys: <encode filter so a filter change doesn't refetch all panels>.
- Pre-aggregation grain: <e.g. 1h rollups; drill-through live query below that>; binding tradeoff per `references/90-tradeoffs.md`.

## 8. Accessibility

Per `references/94-accessibility.md`: palette (<viridis magnitude / Okabe-Ito categorical>); no color-only encoding (status = color + shape + label); contrast target (4.5:1 text / 3:1 graphical); keyboard nav; chart `aria-label` + data-table fallback; `prefers-reduced-motion`.

## 9. Implementation

Component structure + data flow (`references/18-react-architecture.md`):
```
App → QueryClientProvider → DashboardShell (filter bar, Zustand)
  ├ TierSummary (KPI stats)
  ├ TierHealth (tabbed subsystem panels → Panel → Chart)
  └ TierDrill (CohortTable virtualized, allocation diff)
```
- Server state → TanStack Query (keys encode filter); UI state → Zustand (time/filter/selection).
- Charts: ECharts via `echarts-for-react`; pure data→option components.
- Key deps: react, @tanstack/react-query, @tanstack/react-virtual, zustand, echarts.

## 10. Success metrics

Per `references/91-success-metrics.md`. Decision-value, not vanity.

| Metric | Baseline | Target |
|---|---|---|
| Time-to-root-cause | <current> | <target> |
| Detection lead time | <current> | <target> |
| Anomaly-detection rate | <current> | <target> |

Not measured: page views / session length / engagement (vanity).

---

## Appendix: anti-pattern check

Walked against `references/93-anti-patterns.md`:

- [ ] No pie for non-part-to-whole (CH1); no dual-axis (CH2); no 3D (CH3); perceptual color scale (CH4)
- [ ] No vanity metrics (SD1); KPIs carry targets+trend (SD2)
- [ ] Hierarchy, not sprawl (SD3); every overview panel drills (SD4)
- [ ] Forecast band present + calibrated (EX1/EX2); error decomposed (EX4); anomalies attributed (EX3)
- [ ] Percentile latency (OB1); SLA reference lines (OB2); anomalies overlaid (OB3); alerts tiered+deduped (OB4); event markers (OB5)
- [ ] Cross-filtering (IN1); keyboard nav (IN2); critical values not hover-only (IN3); in-place drill (IN4)
- [ ] Query keys scoped (IM1); table virtualized (IM2); server-side aggregation where needed (IM3); server-state in Query not store (IM4)
- [ ] No color-only encoding (AC1); WCAG AA contrast (AC2); chart text alternative (AC3)
- [ ] Exec: no operational detail (EXEC1); KPI targets (EXEC2); risk shown (EXEC3)
