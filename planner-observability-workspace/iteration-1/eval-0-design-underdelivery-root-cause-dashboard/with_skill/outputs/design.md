# Dashboard design: Underdelivery Root-Cause Console

Owner: Pacing / Delivery Reliability
Date: 2026-06-01
Status: Draft

Mode: DESIGN. Category: root-cause-analysis (primary), entered from delivery-explorer + planner-explorer, localized via cohort-explorer, explained via forecast-explorer.

Scope note: this is the **incident** surface for the pacing on-call. It is not the exec weekly review and not the forecast post-mortem workbench; those are separate, linked surfaces (`10-information-arch.md`: split by persona). The whole design is the *path* from "campaign X underdelivered" to one of four named causes with a fix, in ≤3 clicks, refreshing every 15s.

---

## 1. Personas

The prompt names one persona and one decision. The secondary personas are inferred (flagged) because the same data feeds them, but the surface is designed for the on-call first; the others get drill-throughs, not their own density.

| Persona | Decision they make here | Decision latency |
|---|---|---|
| **Pacing on-call** (primary) | A committed campaign missed (or is forecast to miss). Which of the four causes is it — forecast-low (timid pacing), forecast-high (early exhaustion), real supply shortfall, or allocation/reservation failure — and what is the mitigation (bump pace, re-reserve supply, trigger replan, page forecast/planner owner, or accept-and-credit)? | real-time (15s) |
| Forecast analyst *(inferred)* | Once the on-call attributes the miss to the supply forecast, is it bias or variance, and which cohort/horizon. Reached via a deep-link out to the forecast-explorer at the same time range + cohort. | interactive |
| Delivery exec *(inferred)* | Are we at risk on committed revenue this period. Reached from a *separate* exec overview that deep-links *down* into this console; not a tier of this surface. | weekly |

What this surface is **not** for: solving the planner/pacer (that's `forecast-allocation`), generic campaign ROAS, host metrics.

## 2. Workflows

The console is built around the "why did we underdeliver" panel sequence (`13-planner-debugging.md`), instrumented end to end. Three investigations, each a short keyboard-drivable path.

**Workflow A — why did campaign X underdeliver (the spine):**
1. Enter on the **incident header** for campaign X (delivered % vs commitment, projected final %, shortfall volume, time-remaining). Observe: is the miss already booked, or projected? → sets urgency.
2. **Delivery curve** (cumulative delivered vs commitment vs ideal pace) — `markArea` the shortfall window. Decide *when* it fell behind.
3. Read the **pacing trace** directly beneath, same x-axis — under-paced throughout (→ forecast-low / timid) vs over-paced early then flat (→ forecast-high / exhausted)? This branch already halves the cause space.
4. **Supply triptych** (forecasted supply vs actual available supply vs allocated) on one chart for the shortfall window — splits the remaining space: actual < forecast → **real supply shortfall**; actual ≥ forecast but allocated < actual → **allocation failure**.
5. Branch to cause:
   - forecast-low / forecast-high → **forecast-error strip** (signed bias for the window) → deep-link to forecast-explorer → action: widen hedge / page forecast owner.
   - real supply shortfall → confirm on the triptych; cross-check the cohort heatmap for whether it's market-wide → action: accept-and-credit or re-source.
   - allocation failure → **allocation diff** (this replan vs prior) + **reservation/contention panel** → action: re-reserve, raise priority, page planner owner.
6. Root cause named + mitigation chosen. Breadcrumb records the path for the incident write-up.

**Workflow B — which cohorts are driving the miss (localize before you commit):**
1. From the incident header, drill to the **cohort heatmap** (campaign's cohorts: market × device × placement, ~20k, value = delivery deficit vs pace).
2. Find the hot block. Is the deficit concentrated in a few cohorts (a contention/reservation problem) or smeared across a market/device slice (a supply or forecast problem)? Sort/pivot by axis to test.
3. Click the hottest cohort → carries that cohort into Workflow A's panels (delivery curve, pacing, supply triptych, allocation diff all re-scope).

**Workflow C — did something change in the last replan:**
1. From the pacing trace or allocation diff, open the **replan timeline** (replans as attributed event markers).
2. Identify the replan whose timestamp aligns with the curve break. Click it → trigger attribution (forecast update / new commitment / supply change / constraint change) + the allocation diff it produced.
3. Cause: this campaign lost supply to another cohort at replan T because of trigger Y → action: re-reserve / page planner.

## 3. Dashboard hierarchy

One persona, one tight incident loop → **one dashboard, master-detail**, not three. Because the entry point is always a *known* campaign ("campaign X underdelivered"), Tier 1 here is campaign-scoped, not a fleet KPI wall (that's the exec overview, a separate linked surface). Tier 2 is the localization + mechanism band; Tier 3 is the planner-decision detail.

```
Tier 1  INCIDENT HEADER (campaign-scoped)        "How bad, booked or projected, how long left?"
        Delivered % vs commitment, projected final %, shortfall volume, time-remaining,
        active-alert badge with severity + attribution chip.
          │ drill: open the campaign →
Tier 2  MECHANISM + LOCALIZATION (tabbed lens, shared state)
        [Delivery]    delivery curve + pacing trace + supply triptych  (delivery-explorer)
        [Cohorts]     cohort heatmap market×device×placement           (cohort-explorer)
        [Forecast]    supply-forecast actual-vs-forecast + bias strip  (forecast-explorer, calibrated)
        Anomaly windows overlaid (markArea/markPoint); SLA/commitment as markLine.
          │ drill: click a cohort cell / a replan / the shortfall window →
Tier 3  PLANNER DECISION / ROOT CAUSE
        Allocation diff (run A vs B), reservation + contention breakdown,
        allocation-flow Sankey (supply→cohort), replan timeline + trigger attribution.
```

Tabs (not pages) for the Tier-2 subsystems — switching Delivery → Cohorts → Forecast is changing the lens mid-incident, not resetting the investigation. **Shared state across every tier and tab:** time range (the incident window — never snaps back to "last 24h"), campaign filter, selected cohort, selected replan/anomaly. Per `10-information-arch.md`: tab by subsystem, never split by metric.

## 4. Panel set with chart rationale

Each panel names the decision it serves and the alternative rejected (`11-chart-selection.md`, `90-tradeoffs.md`).

| Panel | Tier | Decision served | Chart | Alternative rejected (why) | Ref |
|---|---|---|---|---|---|
| Incident header | 1 | Booked vs projected miss, urgency | KPI stats + sparkline + delta-vs-commitment; **projected-final** carries a calibration-aware band | Hero number alone (SD2 — level without trend/target/projection is not actionable; exec steers on the *projected* miss, not the current %) | `14`,`16` |
| Delivery curve | 2 | When did it fall behind | Cumulative multi-line: delivered vs commitment vs ideal pace; `markArea` shortfall, `markLine` commitment | Single delivered line (loses the gap, which *is* the signal); bar (wastes ink on continuous time) | `11`,`13`,delivery-explorer |
| Pacing trace | 2 | Under-paced throughout vs over-paced-and-exhausted | Line: pace rate vs target rate, **stacked beneath delivery curve, shared x-axis** | Dual-axis pace+delivery on one chart (CH2 — manufactures correlation; two aligned charts instead) | `11`,`13` |
| Supply triptych | 2 | Real shortfall vs allocation failure | Three lines on one axis: forecasted / actual-available / allocated supply | Three separate panels (the whole point is reading the three gaps together) | `13` |
| Supply-forecast vs actual | 2 | Is the supply forecast trustworthy for this window | Line + **calibrated** p10–p90 band + bias strip; band legend states coverage | Bare forecast line (EX1 — false certainty); band with no calibration note (EX2 — lies with confidence) | `12` |
| Cohort heatmap | 2 | Where is the deficit — concentrated or smeared | Heatmap, cohort (market×device×placement) × time, value = signed delivery deficit vs pace, **diverging** blue↔orange around zero | Small multiples (doesn't scale to ~20k cohorts); pie/bar per cohort (no localization across two axes) | `11`,cohort-explorer |
| Allocation diff | 3 | What the planner moved between runs | Diverging horizontal bar: signed per-cohort delta, sorted by magnitude | Before/after two pies (CH1); current-allocation-only view (can't see what changed) | `13`,allocation-explorer |
| Reservation + contention | 3 | Why didn't this campaign get the supply | Stacked bar: reserved-by-cohort vs free for the pool, + contention list (who wanted it and won) | Reservation totals with no contention (can't answer "why not me") | `13` |
| Allocation-flow Sankey | 3 | Where did the inventory go | Sankey: supply pools → demand cohorts, link width = volume, link color = reservation state | Stacked bar (loses the flow / mis-allocation pattern) | `11`,`13`,allocation-explorer |
| Replan timeline | 3 | Did a replan cause the break; scheduled or reactive | Event markers on the time axis, labeled by trigger; click → allocation diff | Replan **count** (SD/OB — can't tell scheduled from reactive) | `13`,`14` OB5 |

Latency/health note: this is an incident-attribution surface, so subsystem latency (planner solve p50/p95/p99 with SLA `markLine`) lives as a compact secondary strip, surfaced only when the attribution points at "allocation failure" (is the planner timing out?) — kept off the primary path to avoid noise but available, p50/p95/p99 never mean-only (OB1).

## 5. Interaction model

Per `17-analytics-ux.md`. Optimized for the operator who lives in this console during an incident.

- **Global filter bar** (persistent, inherited by every tier/tab): time range = incident window, campaign, cohort, market. Setting any filter re-scopes every panel — they are lenses on one filtered context, not independent widgets (IN1 avoided).
- **Linked brushing.** Brushing the shortfall window on the delivery curve shades the same `markArea` on the pacing trace, supply triptych, and forecast chart — the correlation is visible without re-navigating.
- **Selection propagation.** Clicking a cohort cell in the heatmap carries that cohort into the delivery curve, supply triptych, allocation diff, and reservation panel. Clicking a replan marker filters the allocation diff to that run pair.
- **Synced axis-pointer.** Hovering a time on any Tier-2 chart shows the crosshair value on all linked charts at that instant — read the whole system state at 14:32 in one hover.
- **Tooltip discipline.** Critical values (delivered %, projected final %, shortfall volume, commitment) are **labels/ticks, not hover** (IN3). Hover carries secondary detail: value + delta-vs-target + cohort + timestamp.
- **Drill mechanics: in-place / side-panel, never modal** (IN4). Drilling a cohort expands a detail region with the overview still visible; breadcrumb shows `Campaign X → cohort (US/iOS/feed) → allocation diff @ replan 14:31` and is clickable.
- **Keyboard map:** `/` focus campaign/cohort search · `j`/`k` move through heatmap hot-cells / replan list · `Enter` drill selected · `[`/`]` step time window · `Esc` pop one drill level · `?` shortcut overlay.

## 6. Drill-down strategy

The console **is** the root-cause spine (`categories/root-cause-analysis.md`). Every anomaly the surface can raise routes onto it:

```
incident header (booked/projected miss) →
  cohort heatmap (WHERE: which cohorts) →
  delivery curve + pacing trace + supply triptych (HOW: under-pace vs exhaust vs no-supply vs not-allocated) →
  allocation diff + reservation/contention  (WHAT the planner did) →
  forecast bias strip / deep-link to forecast-explorer (WHY the input was wrong) →
  cause: { forecast-low | forecast-high/exhaustion | real supply shortfall | allocation failure }
```

Path length: incident header → Tier-2 mechanism (1) → cohort or allocation detail (2) → cause panel (3). **≤3 clicks to first cause**, instrumented (Section 10). Each of the four causes terminates in a distinct panel state with a distinct mitigation, so the path doesn't dead-end at "it's red" (SD4). The alert that pages the on-call deep-links straight to the incident header at the right campaign + time range, so the on-call starts mid-spine, not at a blank dashboard.

Alert design (so the page is trustworthy, `14-observability-health.md`): page only on the **symptom** — "campaign projected-underdelivery > X% of commitment with < Y h remaining," burn-rate / multi-window (sustained, not single-tick); forecast-coverage drop or solve-latency spike are **dashboard signals that explain the page**, not pages themselves (OB4). One incident spanning 50 cohorts is **one** page, deduped by root-cause dimension, not 50. Severity tiers: booked miss / large projected miss = page; small projected drift = ticket + annotation.

## 7. Scalability

At ~20k cohorts per the fleet (a single campaign touches a subset), 15s refresh, ClickHouse (delivery / pacing / forecast) + planner audit logs (allocations / reservations / replans):

- **Cohort heatmap:** server-side bucketed in ClickHouse — the deficit-vs-pace value is aggregated per (cohort, time-bucket) in the OLAP store, the browser fetches the rollup, not raw events (IM3 avoided). At 20k cohorts × time-buckets the heatmap renders bucketed cells, not 20k raw rows.
- **Cohort table** (heatmap's tabular twin, sortable): `@tanstack/react-virtual` past ~10k rows; 20k is virtualized client-side after the server-side aggregation (IM2). Binding tradeoff: fetches the aggregated 20k-row set, not 1M raw — if cohort cardinality crosses ~100k, move to server-side pagination + windowed query (`90-tradeoffs.md`).
- **Query keys** encode each panel's exact dependencies `{panel, campaign, cohort, timeRange, replanPair}` so changing the cohort filter refetches only the cohort-scoped panels, not the whole board (IM1 avoided).
- **Pre-aggregation grain:** 1-minute rollups in ClickHouse for delivery/pacing/forecast feed the 15s-refresh Tier-2 charts (the metrics move slower than 15s; the refresh is for freshness, not new grain). Allocation diff / reservation / replan come from the **planner audit log** keyed by run id — pulled on drill, not on every refresh (audit-log queries are heavier; they fire only when the on-call drills to Tier 3). Tradeoff: can't see sub-minute pacing wobble from the rollup; if a pacer oscillation incident needs sub-minute, add a drill-through live query rather than lowering the global grain.
- **Refresh discipline:** 15s polling on Tier-1 + visible Tier-2 panels only; off-screen tabs and Tier-3 audit-log panels refetch on focus/drill, not on a timer — keeps the ClickHouse + audit-log query load bounded during an incident.
- **Dense time-series:** `series.large: true` + `sampling: 'lttb'` for the delivery/pacing lines; downsample server-side beyond canvas resolution.

## 8. Accessibility

Per `94-accessibility.md`. The on-call reads this at 3am on a glare-y dark screen — accessibility is a primary-user requirement, not compliance.

- **No color-only encoding** (AC1): under/over-delivery and healthy/breaching carry **color + shape + label** — ▲ over / ▼ under beside the value, status word not just hue, signed values positioned above/below the zero line. A red heatmap cell is paired with its signed magnitude on a labeled scale.
- **Palette:** diverging **blue↔orange** (colorblind-safe, not red↔green) for the signed delivery-deficit heatmap and allocation diff, around a meaningful zero midpoint; sequential **viridis/cividis** for any pure-magnitude scale (no rainbow/jet — CH4). Categorical lines (delivered/commitment/ideal/pace) use Okabe-Ito + **direct end-labels + dash patterns**, not color alone.
- **Contrast (WCAG AA):** ≥4.5:1 text, ≥3:1 for lines/bars/key chart elements; verified on the **dark on-call theme** separately (contrast that passes on light often fails on dark); no thin light-gray series.
- **Keyboard-first:** the full `/ j k Enter [ ] Esc ?` map operable without a pointer; visible focus indicators; drill/filter/time controls all keyboard-operable.
- **Screen-reader / non-visual:** each chart carries an `aria-label` takeaway ("Delivery 92% of commitment, projected 88%, falling since 14:00") + a **toggleable data-table fallback** (doubles as the power-user "exact numbers" view); the 15s refresh announces via `aria-live="polite"`.
- **Motion:** respect `prefers-reduced-motion`; **no entrance animation on the 15s refresh** — motion every 15s is a distraction, not an explanation.

## 9. Implementation

Component structure + data flow (`18-react-architecture.md`):

```
App → QueryClientProvider → IncidentConsoleShell (global filter bar + Zustand: campaign/cohort/timeRange/selection)
  ├ TierIncidentHeader (KPI stats + projected-final band)
  ├ TierMechanism (tabbed, shared state)
  │   ├ DeliveryTab    → DeliveryCurve + PacingTrace + SupplyTriptych   (ECharts panels)
  │   ├ CohortsTab     → CohortHeatmap (server-bucketed) + VirtualCohortTable
  │   └ ForecastTab    → ForecastVsActual (calibrated band) + BiasStrip
  └ TierRootCause (drill, audit-log-backed)
      ├ AllocationDiff (diverging bar)
      ├ ReservationContention
      ├ AllocationSankey
      └ ReplanTimeline (+ TriggerAttribution)
  Breadcrumb + KeyboardLayer cross-cut all tiers
```

- **Server state → TanStack Query**, keys encode `{panel, campaign, cohort, timeRange, replanPair}`; 15s `refetchInterval` on Tier-1 + visible Tier-2, focus/drill-triggered for Tier-3 (IM1/IM4 — never hand-managed in the store).
- **UI state → Zustand** only: time range, campaign/cohort filter, selected cohort, selected replan/anomaly. This is the shared-state contract that follows the reader across tabs and drills.
- **Two data adapters:** a ClickHouse adapter (delivery/pacing/forecast rollups, server-side heatmap bucketing) and a planner-audit-log adapter (allocations/reservations/replans, keyed by run id). Tier-3 panels read the audit adapter; the diff/Sankey/contention all derive from it.
- **Charts:** ECharts via `echarts-for-react`; pure data→option components; `large`+`lttb` sampling on dense series; `markArea`/`markLine`/`markPoint` for shortfall windows, commitments, anomalies, replans, SLAs.
- **Key deps:** react, @tanstack/react-query, @tanstack/react-virtual, zustand, echarts, echarts-for-react.

## 10. Success metrics

Per `91-success-metrics.md`. Decision-value, not vanity.

| Metric | Baseline | Target |
|---|---|---|
| Time-to-root-cause (page → one of the four causes named) | current ad-hoc query / log-grep flow (unmeasured, est. 15–40 min) | < 5 min median |
| Drill-path click count (incident header → cause) | — | ≤ 3 clicks (instrumented) |
| Detection lead time (projected-miss flagged before booked miss) | reactive — found after the miss books | flag ≥ Y h before commitment window closes |
| Mis-triage reduction (wrong cause / wrong owner paged) | current rate of mis-attributed pages | measurable drop vs baseline |
| Incident retro coverage | — | console would have flagged + correctly attributed ≥ last quarter's underdelivery incidents |

Validated by timed task studies (on-call answers "which cohort drove it and why" against the current flow as baseline) + incident-retro replay, not traffic.

**Not measured:** page views, session length, engagement (vanity — a heavily-viewed incident console may just be hard to read; `91`).

---

## Appendix: anti-pattern check

Walked against `references/93-anti-patterns.md`:

- [x] No pie for non-part-to-whole (CH1 — allocation diff is diverging bar, before/after is a bar not two pies); no dual-axis (CH2 — pacing stacked beneath delivery on a shared x-axis, not overlaid); no 3D (CH3); perceptual/diverging color scale (CH4 — viridis/cividis magnitude, blue↔orange diverging).
- [x] No vanity metrics (SD1 — every header stat carries commitment/target + projected delta); header is stat + sparkline + projection, not a hero number (SD2); hierarchy not sprawl (SD3 — three campaign-scoped tiers, subsystem tabs); every Tier-1/Tier-2 panel drills to a cause (SD4 — the four-cause spine).
- [x] Forecast band present + **calibrated** with coverage note (EX1/EX2); forecast bias surfaced for the window, full bias/variance decomposition handed to forecast-explorer on deep-link (EX4); anomalies attributed to cohort + input + window (EX3).
- [x] Planner solve latency p50/p95/p99 when surfaced, never mean-only (OB1); SLA/commitment as `markLine` on every health/delivery series (OB2); anomalies overlaid on the perturbed metric, not a separate tab (OB3); alerts tiered + symptom-based + burn-rate + deduped + deep-linked (OB4); replans/config changes as event markers (OB5).
- [x] Cross-filtering + linked brushing + selection propagation (IN1); full keyboard map (IN2); critical values as labels not hover (IN3); in-place/side-panel drill with breadcrumbs, no modal (IN4).
- [x] Query keys scoped per panel (IM1); cohort table virtualized (IM2); heatmap server-side bucketed in ClickHouse (IM3); server state in TanStack Query, UI state in Zustand (IM4).
- [x] No color-only encoding — color + shape + label + position (AC1); WCAG AA contrast verified on dark theme (AC2); chart `aria-label` + toggleable data-table fallback (AC3).
- [x] Exec detail kept off this surface — exec overview is a separate linked surface, this console is on-call-density (EXEC1); header leads with **projected** (forecasted) underdelivery risk, not only booked status (EXEC3).

### Open questions / flagged inferences

1. **Calibration data availability.** The forecast band's coverage note (EX2) assumes per-cohort-tier empirical coverage is tracked. If it isn't, the band must say so loudly ("calibration unmeasured") rather than imply a calibrated interval — confirm the supply forecast emits coverage stats.
2. **Audit-log query latency.** Tier-3 panels assume the planner audit log is queryable by run id at interactive latency on drill. If audit-log reads are slow, pre-materialize the allocation diff per replan pair into ClickHouse rather than querying the log live.
3. **Cohort cardinality per campaign.** Design assumes a single campaign touches a tractable subset of the 20k cohorts (virtualized client-side after server bucketing). If a single campaign spans ~all 20k *and* the fleet grows past ~100k cohorts, the cohort table moves to server-side pagination (`90-tradeoffs.md` trigger).
4. **"Projected final %" model.** The header's projected miss needs a pace-extrapolation or the planner's own projection. Which source — and is *it* calibrated — determines whether the lead-time metric is trustworthy.
