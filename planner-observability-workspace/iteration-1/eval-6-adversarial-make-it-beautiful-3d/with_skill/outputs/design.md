# Dashboard design: Leadership delivery review ("Demo Wall")

Owner: Planner Observability
Date: 2026-06-01
Status: Draft

---

## Read this first: what I'm building and what I'm declining

You asked for smooth animations on every refresh, a rotating 3D globe of delivery-by-region, gradient-filled 3D bar charts, and a big animated donut. I'm not going to build those, and the rest of this doc is the version that will actually land in the leadership room.

The reason is narrow and it's the whole job of this skill: a leadership demo succeeds when, in the first ten seconds on screen, an exec can answer **are we on track, what's the risk, and where do I spend attention.** Every one of the four requested elements *slows that down* while looking like it speeds it up:

- **3D bars / 3D donut** distort the exact comparison leadership is there to make. A 3D bar's height is read through perspective and occlusion, so two regions that differ by 4% can look equal or reversed depending on viewing angle. The thing you most want them to trust — "this region is behind" — is the thing 3D makes unreliable. (Cleveland & McGill: length-on-a-common-scale is decoded accurately; perspective-distorted area is not.)
- **Animation on every refresh** means the chart is moving precisely when someone is trying to read a number off it. Motion every 15-30s is a distraction tax paid continuously; it also fails `prefers-reduced-motion` and makes the screen unreadable to anyone with vestibular sensitivity in the room.
- **Rotating globe** spends the largest, most central pixels on a low-information encoding: regions on the far side are occluded, the rotation means a region you want to compare is sometimes hidden, and "delivery by region" is at most ~6-12 categories — a job a sorted bar does instantly and a globe does never. The globe answers "is this a tech company" not "which region is at risk."
- **Animated donut** for a delivery breakdown asks leadership to compare angles (decoded worse than length), and a donut with a center number is just a stat panel wearing a costume.

What leadership will actually call "amazing" is a surface where the answer is unmissable and the drill is one click. So I'm reallocating the entire decoration budget to: **the risk lead-indicator up top, a clean delivery-vs-commitment overlay with a calibrated band, a sorted region bar, and a real drill-through** so the demo can go "we're 94% to commitment, EMEA is the risk, here's why" live, without a single rotation.

If there's a binding reason a specific 3D element must ship (a CEO who has asked for the globe by name, a brand template you can't deviate from), tell me and I'll record it as an explicit tradeoff with the legibility cost noted — but I'd push to keep it off the panels that carry the decision.

Below is the design. The requested→replacement mapping is in §4 and the appendix.

---

## 1. Personas

This is a leadership-demo surface, so the primary persona is exec/leadership. I'm inferring two more who will be in or behind the room. Flagged as inferred.

| Persona | Decision they make here | Decision latency |
|---|---|---|
| Delivery exec / leadership (primary) | Are we on track to commitment this period; what's the forecasted risk; which region/segment do I push on | Weekly review (and the demo itself) |
| Planner / delivery lead (inferred — the one who fields "why is EMEA red?" live) | Where the miss concentrates and whether it's already being worked | Interactive, during the meeting |
| Analytics owner (inferred — presents, owns the numbers) | Are the numbers defensible; is the forecast calibrated enough to quote | Interactive |

The dominant axis is the exec. Per the executive-reporting discipline, this surface is defined by what it **excludes**: no per-cohort latency, no solve times, no individual replans on Tier 1. That detail lives one drill down, for the planner lead who gets asked a pointed question.

## 2. Workflows

**Workflow A — the demo narrative ("are we on track / what's the risk"):**
1. Land on Tier 1. Read the **risk strip**: delivery-to-commitment %, $ at risk, pacing stability, forecast quality — each with target + trend arrow. Decision: green across → "we're healthy," move on. One amber → that's the story.
2. The forecast-vs-commitment overlay shows the gap closing or opening through period-end, with the calibrated band. Decision: is the projected end-of-period inside commitment.
3. The sorted **delivery-by-region bar** shows which region carries the gap. Decision: name the region.

**Workflow B — "why is that region behind?" (the live question):**
1. From the region bar, click the behind region → Tier 2 health for that region (same time range, same filter carried).
2. Read pacing + the cohort heatmap: is the miss broad or one segment; is it pacing oscillation or a supply shortfall.
3. Click the hot cell → Tier 3: forecast-vs-actual for that cohort with error decomposed (bias vs variance) and the allocation that fed it. Root cause named: forecast bias / under-allocation / pacing throttle / supply shortfall.

The demo is impressive because Workflow B runs live in three clicks, not because anything spins.

## 3. Dashboard hierarchy

```
Tier 1 EXECUTIVE SUMMARY   risk strip (6 KPIs) + delivery-vs-commitment overlay + region bar
  │ drill → (click a region / a red KPI)
Tier 2 SYSTEM HEALTH        per-region: pacing, cohort heatmap, delivery trend
  │ drill → (click a cohort / hot cell)
Tier 3 DRILL-DOWN           forecast-vs-actual + error decomposition + allocation diff → root cause
```

One dashboard, three tiers, state carried down (time range, region/cohort filter, selection). Tier 1 is the demo screen; Tiers 2-3 exist so the demo survives the first hard question. The "wow" is that the overview is not a dead end — `SD4` is the anti-pattern that kills exec dashboards, and a globe is a dead end with a motor.

## 4. Panel set with chart rationale

Tier 1 (the demo surface). Each panel names the requested-decoration it replaces where relevant.

| Panel | Decision served | Chart | Alternative rejected (why) | Ref |
|---|---|---|---|---|
| Risk strip (6 KPIs) | On track? what's at risk? where to look | KPI stat + sparkline + delta-vs-target, status as color **+ shape + label** | Bare hero numbers (vanity, no good/bad reference — SD1/SD2) | `16` |
| Delivery vs commitment, period-to-date + projection | Will we land inside commitment | Multi-line (actual, forecast) + commitment `markLine` + calibrated p10–p90 band + calibration note | Animated-on-refresh line (motion blocks reading the gap); bare line (false certainty — EX1) | `11`,`12` |
| Delivery by region | Which region carries the gap | **Sorted horizontal bar**, length on a common zero-baseline axis, behind-target regions marked with ▼ + label | **Rotating 3D globe** (occludes far regions, distorts magnitude, ~8 categories don't need a sphere); 3D bars (CH3); pie/donut (angle decoded worse than length — CH1) | `11` |
| Delivery breakdown by class | Where committed volume is going | **Stacked bar** (single bar, the whole = 100% of delivered) | **Animated donut** (angle comparison, center-number donut is a stat in costume — CH1) | `11` |
| Risk callout | The one thing trending wrong | Text + the offending sparkline, deep-links into Tier 2 | — (this is the "spend attention here" answer EXEC3 demands) | `16` |

Tier 2 (one drill): per-region pacing line with SLA `markLine`, cohort×time heatmap on a perceptually-uniform scale (viridis/cividis, not rainbow — CH4), delivery trend with event markers (replans/config changes as `markLine`).

Tier 3 (root cause): forecast-vs-actual overlay with calibrated band, **error decomposition** (signed bias vs variance, not a lone RMSE — EX4), anomaly attribution overlaid on the perturbed metric (EX3), allocation diff. This is where "why" bottoms out.

On the breakdown specifically: if leadership convention truly demands a donut, the carve-out is a strict part-to-whole with ≤5 classes and the whole meaningful — even then a stacked bar reads faster and I'd default to it. No animation on it either way.

## 5. Interaction model

- **Global filter** (time range, region) carried across all three tiers; selecting a region on Tier 1 propagates down — `IN1`, no independent widgets.
- **Drill in place / side panel**, not modal — the overview stays visible so the context that made the anomaly legible isn't lost (`IN4`). Breadcrumbs; `Esc` pops one level.
- **Critical values as labels**, not hover-only (`IN3`): every KPI number and every region bar value is on screen for the demo. Hover is for secondary detail.
- **Keyboard map**: `/` focus filter, `j`/`k` move selection, `Enter` drill, `[`/`]` time step, `Esc` up a level, `?` help. Power-user and accessibility requirement both (`IN2`).
- **Transitions**: a single ~200ms ease on *drill* (so the eye follows the context change) is the only motion. No entrance animation, no per-refresh animation, gated behind `prefers-reduced-motion`.

## 6. Drill-down strategy

```
Tier 1 region bar (EMEA behind) → Tier 2 EMEA pacing + cohort heatmap (hot cell)
  → Tier 3 cohort forecast-vs-actual + bias/variance + allocation diff → cause
```
Every Tier 1 panel drills: each red KPI deep-links to its Tier 2 subsystem; each region bar segment drills to that region; the breakdown drills to per-class delivery. Path length ≤3 clicks to a first cause. No panel on Tier 1 is terminal — the contrast with the requested globe (a terminal, non-drillable centerpiece) is the whole point.

## 7. Scalability

The exec surface is pre-aggregated and cheap; the demo must never stall on a spinner.

- Tier 1: 6 KPIs + 2 overlays + 1 bar, all from period rollups — sub-second, cacheable, can be a generated snapshot ("as of Monday 9am") for the demo so it can't break live.
- Tier 2 cohort heatmap: server-side bucketed; client renders the rollup, not raw events (`IM3`).
- Tier 3 cohort table (if shown): virtualized past ~10k rows; server-side aggregation past ~100k (`IM2`).
- Query keys encode exactly each panel's filter dependencies, so changing region on Tier 1 refetches the region bar and overlay, not all panels (`IM1`).

## 8. Accessibility

This is also why the requested elements lose. Per `94-accessibility.md`:

- **No color-only encoding** (`AC1`): on-track/behind is color **+** shape (▲/▼) **+** the number, never red/green alone — ~8% of men and every projector with bad color would otherwise lose the entire signal in a leadership room.
- **Palette**: Okabe-Ito categorical for series; viridis/cividis (colorblind-optimized) for the heatmap magnitude; no rainbow (`CH4`).
- **Contrast**: ≥4.5:1 text, ≥3:1 graphical objects — verified on the dark demo theme separately. A gradient fill (requested on the 3D bars) routinely drops part of a bar below 3:1; flat fills hold contrast.
- **Motion**: `prefers-reduced-motion` honored; no per-refresh animation. This is a direct conflict with "smooth animations on every refresh," and the accessibility rule wins.
- **Screen reader / exact numbers**: each chart carries an `aria-label` takeaway ("Delivery 94% of commitment, EMEA 11% behind") + a toggleable data table — which doubles as the "give me the exact number" feature an exec will ask for.

## 9. Implementation

```
App → QueryClientProvider → DashboardShell (filter bar, Zustand UI state)
  ├ TierSummary  (RiskStrip KPIs, DeliveryVsCommitment, RegionBar, RiskCallout)
  ├ TierHealth   (per-region: PacingLine, CohortHeatmap, DeliveryTrend)
  └ TierDrill    (ForecastVsActual + ErrorDecomp, AllocationDiff, virtualized table)
```
- Server state → TanStack Query (keys encode filter); UI state (time/region/selection) → Zustand (`IM4`).
- Charts → ECharts via `echarts-for-react`, pure data→option components. Calibrated band = two stacked line series + `areaStyle`; commitment/SLA = `markLine`; events = `markLine` on the time axis.
- Deps: react, @tanstack/react-query, @tanstack/react-virtual, zustand, echarts. No 3D/globe library (`echarts-gl`) — deliberately omitted.
- For the demo, Tier 1 can run off a deterministic snapshot adapter so it renders with no backend and can't fail live.

## 10. Success metrics

| Metric | Baseline | Target |
|---|---|---|
| Time-to-answer "are we on track" (exec, on screen) | — | < 10s, no interaction |
| Time-to-name the at-risk region | — | < 30s, ≤1 click |
| Time-to-root-cause for "why is region X behind" (live Q&A) | — | < 90s, ≤3 clicks |

Not measured: time-on-screen, "engagement," demo "wow" as a metric — those measure the dashboard's popularity, not whether anyone decided anything. The demo lands if leadership leaves able to state the risk and where it is.

---

## Appendix A: requested element → what ships instead

| You asked for | Ships instead | Why (anti-pattern) |
|---|---|---|
| Smooth animations on every refresh | One ~200ms drill transition, gated by `prefers-reduced-motion`; no per-refresh motion | Motion blocks reading the number it's animating; fails reduced-motion (`94`, OB-adjacent) |
| Rotating 3D globe, delivery by region | Sorted horizontal bar, behind-target marked ▼ + label | Occlusion + magnitude distortion + ~8 categories; a terminal centerpiece, not a drill entry (CH3, SD4) |
| Gradient-filled 3D bar charts | Flat 2D sorted bars, zero-baseline, common scale | 3D distorts the comparison leadership is there to make; gradient drops contrast (CH3, CH5, AC2) |
| Big animated donut, delivery breakdown | Stacked bar (part-to-whole), or a stat for a single rate | Angle decoded worse than length; animated; center-number donut is a stat in costume (CH1) |

## Appendix B: anti-pattern check (walked against `93-anti-patterns.md`)

- [x] No pie/donut for non-part-to-whole (CH1 — donut replaced by stacked bar/bar); no dual-axis (CH2 — projection is a `markLine`, not a second axis); **no 3D** (CH3 — globe + 3D bars declined); perceptual color scale (CH4 — viridis/cividis heatmap)
- [x] No vanity metrics (SD1 — every KPI carries target+trend); no context-free hero number (SD2 — stat+sparkline+delta)
- [x] Hierarchy not sprawl (SD3 — three tiers); **every Tier-1 panel drills** (SD4 — the globe's fatal flaw, avoided)
- [x] Forecast band present + calibration note (EX1/EX2); error decomposed bias/variance (EX4); anomalies attributed and overlaid (EX3)
- [x] Percentile latency where shown (OB1); SLA `markLine` (OB2); anomalies overlaid not in a tab (OB3); alerts (if added) tiered (OB4); event markers on trends (OB5)
- [x] Cross-filtering with carried state (IN1); keyboard nav (IN2); critical values as labels not hover (IN3); in-place drill (IN4)
- [x] Scoped query keys (IM1); virtualized/server-aggregated tables (IM2/IM3); server state in Query not store (IM4)
- [x] No color-only encoding — color + shape + label (AC1); WCAG AA contrast verified on dark theme (AC2); chart `aria-label` + data-table fallback (AC3); `prefers-reduced-motion` honored
- [x] Exec: no operational detail on Tier 1 (EXEC1); every KPI has a target (EXEC2); leads with forecasted risk, not just status (EXEC3)

## Open questions

1. Region count and class count for the breakdown (confirms bar-vs-stacked-bar and that we're under the pie carve-out — though I'd use bars regardless).
2. Is the forecast band calibrated, and over what window? If unmeasured, the band ships with that stated loudly rather than implied (EX2).
3. Is there a binding brand/leadership mandate for any 3D element? If so I'll record the legibility cost as an explicit tradeoff rather than silently drop it.
4. Live data vs Monday-snapshot for the demo screen (I recommend snapshot so it can't fail in the room).
