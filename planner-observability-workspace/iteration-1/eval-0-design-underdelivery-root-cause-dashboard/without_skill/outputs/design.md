# Underdelivery Root-Cause Dashboard — Design

## 1. Purpose and Audience

**Who:** The pacing on-call engineer, mid-incident, under time pressure.

**Job to be done:** Get from *"Campaign X underdelivered (or is projected to underdeliver) against its guaranteed commitment"* to a **defensible root cause** in minutes, not hours — across a system that allocates guaranteed delivery over ~20,000 cohorts (market × device × placement).

**Design north star:** Every screen answers the next question the on-call is about to ask. The dashboard is a **diagnostic funnel**, not a wall of charts. It must point at a cause, quantify the gap, and hand off to the right remediation owner.

**Non-goals:** This is not a BI/exec reporting tool, not a long-horizon trend explorer, and not the place to reconcile billing. It is an incident instrument.

---

## 2. The Root-Cause Taxonomy (the spine of the whole design)

Before laying out panels, we fix the **set of causes the dashboard must be able to distinguish**. Underdelivery in a guaranteed-delivery (GD) system almost always falls into one of these buckets. The entire layout is organized to walk the on-call through them in the order that's cheapest to rule out.

| # | Root-cause class | One-line definition | Primary signal | Owner / remediation |
|---|------------------|---------------------|----------------|---------------------|
| A | **Supply shortfall** | Forecasted available impressions in the campaign's eligible cohorts didn't materialize (traffic down). | Actual cohort supply << forecast supply | Forecasting / nothing (external) |
| B | **Forecast error** | Supply *was* there historically, but the forecast the planner allocated against was wrong (over-optimistic). | Forecast supply >> realized supply, consistently | Forecasting team |
| C | **Allocation/reservation gap** | Planner never reserved enough capacity to this campaign (under-allocated at plan time). | Sum of reservations < commitment, or reservations on thin cohorts | Planner / yield management |
| D | **Contention / loss in auction** | Capacity was reserved, supply existed, but the campaign lost the impression (priority, competing GD, pricing, frequency cap). | High eligible-but-not-won rate; win-rate drop vs peers | Ad serving / priority config |
| E | **Pacing throttle (self-inflicted)** | The pacing controller deliberately held the campaign back (smoothing too aggressive, ASAP vs even, daily caps). | Delivered < pace target while ample won-able supply existed | Pacing config |
| F | **Targeting / eligibility collapse** | Eligible cohort set shrank or was misconfigured (creative disapproval, targeting edit, brand-safety block, budget/flight gating). | Eligible-cohort count or eligible-supply dropped at a timestamp | Trafficking / campaign ops |
| G | **Replan disruption** | A planner replan moved capacity away from this campaign (re-allocation to a higher-priority deal, solver instability). | Reservation step-down correlated with a replan event | Planner / yield |
| H | **Data/pipeline artifact** | The campaign actually delivered; the *measurement* underdelivered (late logs, dedup, join gap, clock skew). | Delivery present in raw but missing in aggregated; freshness lag | Data eng |

> H is listed last but is **checked first** in the flow (Section 4, Step 0): you never debug a number you can't trust.

This taxonomy is also the **vocabulary of the verdict**: when the on-call resolves the incident, they tag it A–H. Those tags feed the postmortem and a "recurring cause" trend (Section 9).

---

## 3. Data Model & Metric Definitions

Getting these definitions pinned down is the hard part; the panels are easy once they're agreed.

### 3.1 Sources

- **ClickHouse — delivery**: impression-level or pre-aggregated counts per (campaign, cohort, minute). Won impressions, served, billable.
- **ClickHouse — pacing**: pacing controller state per (campaign, minute): pace target, pace ratio, ASAP/even mode, throttle factor, daily cap state.
- **ClickHouse — forecast**: forecasted available supply per (cohort, horizon, forecast-vintage). Vintage matters — see §3.3.
- **Planner audit logs**: discrete events — `allocation`, `reservation`, `replan`, `solver_run`. Each carries campaign id, cohort set, capacity numbers, priority, timestamp, and a `replan_reason`.

### 3.2 The core identity (delivery decomposition)

Every panel ties back to one **delivery identity** so numbers always reconcile. For a campaign over a time window:

```
Delivered
  = Σ_cohort [ Supply_realized
               × Eligibility            (is campaign allowed to bid here, 0/1 over time)
               × Reserved_share         (planner's intended share of this cohort)
               × Win_rate               (won / eligible-contended)
               × (1 − Throttle)         (pacing controller holdback)
             ]
```

Each multiplicative term maps to a root-cause class:

- `Supply_realized` low vs forecast → **A / B**
- `Eligibility` dropped → **F**
- `Reserved_share` low → **C / G**
- `Win_rate` low → **D**
- `Throttle` high → **E**

This is the single most important artifact in the design: it lets the dashboard **attribute the delivery gap to terms**, not just show that a gap exists. Section 5 builds a literal waterfall from it.

### 3.3 Definitions that bite (write these on the panels)

- **Commitment / contracted goal**: total impressions promised over the flight. **Pace target at time _t_**: the goal pro-rated by the pacing curve (even, front-loaded, custom). Underdelivery is measured against *pace target to date*, not the final goal, during the flight.
- **Forecast vintage**: a forecast value is meaningless without "as of when." The planner allocated against the forecast *vintage current at allocation time*. To judge **forecast error (B)** we compare that vintage to realized. To judge **supply shortfall (A)** we compare the *most recent* forecast (best estimate of "normal") to realized. Mixing vintages is the #1 way to misdiagnose A vs B — the dashboard must always label vintage.
- **Eligible vs contended vs won**: eligible = passed targeting/budget/brand-safety; contended = entered an auction; won = secured. Win-rate denominators differ; D requires the contended denominator.
- **Cohort**: market × device × placement. ~20k of them. Most campaigns touch a long tail; **delivery is usually concentrated in a few hundred cohorts** — the UI must surface concentration (Pareto), never force the user to scroll 20k rows.

### 3.4 Pre-aggregation (this is what makes 15s refresh feasible)

We do **not** query impression-level data live during an incident. We maintain ClickHouse materialized views / `AggregatingMergeTree` rollups:

- `campaign_minute`: delivered, pace_target, throttle, mode — per campaign per minute.
- `campaign_cohort_minute`: the five identity terms per (campaign, cohort, minute). This is the workhorse; it's the source for the waterfall and the cohort table.
- `campaign_cohort_5m` / `_1h`: coarser rollups for the trend and longer lookbacks.
- A small **`incident_focus` table**: when an on-call pins a campaign, a background job narrows continuous aggregation to that campaign's cohort set so the heavy panels stay cheap.

Planner audit events are indexed by campaign and time and surfaced as an **event stream overlaid on time axes** (not joined row-by-row into ClickHouse — they're annotations).

See Section 8 for the full performance argument.

---

## 4. The Diagnostic Flow (how the on-call actually moves)

The dashboard is built as a **funnel with five stops**. Each stop either *localizes* the problem and passes the user down, or *exonerates* a cause and moves on. The layout (Section 5) physically mirrors this top-to-bottom.

```
  [ALERT: Campaign X underdelivering]
            │
   Step 0 ──┤  TRUST THE DATA?      → Freshness/health banner. If stale → cause H, page data-eng. STOP.
            │
   Step 1 ──┤  HOW BIG, HOW URGENT? → Gap vs pace, projected end-of-flight miss, time-to-breach.
            │                          Frame the incident. Is it still recoverable?
            │
   Step 2 ──┤  WHICH TERM BROKE?     → Delivery-decomposition WATERFALL (the §3.2 identity).
            │                          Attributes the gap to A/B, C/G, D, E, or F. THE key panel.
            │
   Step 3 ──┤  WHERE & WHEN?         → Cohort concentration (which cohorts carry the gap) +
            │                          timeline with planner events overlaid (when did it start).
            │
   Step 4 ──┤  WHY THAT TERM?        → Cause-specific drill panel, auto-selected by the dominant
            │                          waterfall term. Confirms the specific A–H verdict.
            │
            └─→ [VERDICT + handoff] tag A–H, owner, evidence permalink.
```

The on-call should reach a verdict using only Steps 0–2 in the common cases, dropping into 3–4 only to confirm or when the gap splits across terms.

---

## 5. Layout — Panel by Panel

Single scrollable page, **top-down = funnel order**, with a sticky context header. One campaign in focus at a time (the "incident view"). A separate fleet view (Section 6) is where you arrive when no single campaign is named.

### Sticky Header — Context & Trust (always visible)

- **Campaign selector / pin**: id, advertiser, flight dates, pacing mode (even / ASAP / front-loaded), priority tier.
- **Step 0 — Data freshness chips**: max event-time lag per source (delivery / pacing / forecast / audit). Green < 30s, amber, red. **If any source is red, a banner reads "Diagnosis may be unreliable — data lag on <source>" and cause H is pre-flagged.** This is non-negotiable: it prevents the classic mis-page where the campaign delivered fine and only the pipeline was late.
- **Refresh control**: 15s auto during incident; pause toggle (so the screen holds still while the on-call reads); "as of" timestamp.

### Step 1 — Incident Framing (top strip, big numbers)

Goal: in one glance, *how bad, how urgent, still saveable?*

- **Delivery vs Pace gauge**: delivered-to-date vs pace-target-to-date. Show the **gap in impressions and %**, color by severity.
- **Projected end-of-flight delivery** vs commitment, with a confidence band (uses current realized rate + remaining forecast supply). This is what tells the on-call whether they're fighting a recoverable shortfall or already-lost inventory.
- **Time-to-breach** / "hours of runway": at current pace, when does cumulative fall irrecoverably behind? Drives triage priority across simultaneous incidents.
- **Sparkline**: pace ratio (delivered/target) over the flight, so a sudden cliff vs slow bleed is obvious immediately — they imply different causes (cliff → F/G/config; bleed → A/B/D).

### Step 2 — Delivery Decomposition Waterfall (THE panel)

This is the centerpiece and the panel that most directly produces a root cause.

- A **waterfall from "Expected (pace target)" down to "Actual delivered,"** with one bar per identity term from §3.2:
  `Expected → −Supply shortfall → −Eligibility loss → −Under-reservation → −Auction loss → −Pacing throttle → Actual`.
- Each step is the impressions lost attributable to that term, computed by holding other terms at their planned/forecast values (a Shapley-ish sequential attribution; order documented and fixed so it's reproducible).
- **The largest bar is the headline cause.** Clicking a bar:
  - sets the **dominant-term context** that auto-selects the Step-4 drill panel,
  - filters the Step-3 cohort table and timeline to that term's contribution.
- Beside the waterfall, a **one-line plain-English verdict draft**: e.g. *"68% of the gap is auction loss (D) concentrated in 12 cohorts; reservations and supply look healthy."* — generated from the attribution, editable, becomes the incident note.

This panel is what turns "underdelivered" into "underdelivered *because*." If we build only one thing well, it's this.

### Step 3 — Where & When

Two side-by-side panels, both driven by the term selected in Step 2.

**3a. Cohort concentration (WHERE)**
- **Pareto / treemap of the gap by cohort** — because delivery concentrates, ~10–30 cohorts usually explain most of the miss. Don't make them hunt through 20k.
- Table (virtualized, sortable) columns: cohort (market/device/placement), gap (imps & %), and the per-term breakdown for *that* cohort (supply δ, eligibility, reservation, win-rate, throttle). Each row is a mini delivery-identity.
- Group-by toggles: roll up the 20k to **market**, **device**, **placement**, or pairs — to spot "all of `mobile×video` collapsed" vs "one market." Fastest way to see whether the cause is structural (a whole dimension) or local.
- Row click → pins the cohort and cross-filters the timeline + drill.

**3b. Timeline with planner-event overlay (WHEN)**
- Stacked time series of the dominant term (or all terms) over the flight at 1m/5m granularity.
- **Audit events rendered as vertical annotations**: `replan` (with reason), `reservation` change, `allocation`, `solver_run`, plus config-change markers (targeting edit, creative status). Hover → full event payload.
- This panel is how you nail **G (replan disruption)**: a reservation step-down line landing exactly on a `replan` annotation is a smoking gun. It also separates "broke at 14:02" (config/event) from "slowly drifted" (forecast/supply).

### Step 4 — Cause-Specific Drill (auto-selected by dominant term)

One panel slot that swaps content based on the Step-2 dominant term, so the on-call sees *only the evidence relevant to the leading hypothesis*. Each variant is built to confirm/deny one or two taxonomy classes:

- **Supply / Forecast (A vs B)** → realized supply vs forecast, split by **vintage**: latest-forecast line (judges A) and allocation-time-vintage line (judges B). If realized tracks latest-forecast but both are below allocation-vintage → **B**. If realized is below *both* → **A**. Add a "this cohort's supply vs same-time-last-week" baseline to catch genuine traffic drops.
- **Reservation (C vs G)** → reservation history for the campaign's cohorts vs commitment; sum-of-reservations vs goal; overlay competing campaigns' priority/reservations in the contested cohorts. A clean under-allocation from t0 → **C**; a mid-flight step-down on a replan → **G**.
- **Auction loss (D)** → win-rate trend vs a peer baseline (similar campaigns/cohorts), loss-reason breakdown if available (lost-to-priority, lost-to-price, frequency-capped, below-floor), and a "who won instead" view in the contested cohorts (which higher-priority deal or competing GD took the impression).
- **Pacing throttle (E)** → throttle factor and pace mode over time vs winnable supply. Confirms self-inflicted holdback: ample won-able supply + high throttle = pacing config too conservative (or ASAP exhausted early). Distinguishes "we chose not to deliver" from "we couldn't."
- **Eligibility (F)** → eligible-cohort count and eligible-supply over time with a change-point marker, joined to config/audit events (creative disapproval, targeting edit, brand-safety block, budget pause). A cliff in eligibility at an event timestamp is the confirmation.

### Footer — Verdict & Handoff

- **Tag the root cause** (A–H, multi-select if split). Pre-filled from the waterfall.
- **Owner / runbook**: each class maps to a team and a remediation runbook link (e.g. D → "request priority bump / pricing review"; E → "loosen pacing smoothing").
- **Evidence permalink**: snapshot of the current filtered state (campaign, time window, selected term/cohorts, "as of" time) so the page handoff or postmortem reproduces exactly what the on-call saw.
- **Push to incident channel** button: posts the verdict draft + permalink.

---

## 6. Fleet / Triage View (the entry point when no campaign is named)

The alert sometimes says "pacing is off," not "Campaign X." This is the landing page; clicking a row deep-links into the incident view above.

- **Underdelivery leaderboard**: all campaigns currently behind pace, ranked by *projected miss* (impressions and revenue at risk) × *urgency* (time-to-breach). Not just "% behind" — a 5% miss on a huge deal outranks a 40% miss on a tiny one.
- Each row shows a **mini-waterfall sparkbar** (dominant term color) so you can often guess the cause class before opening the campaign — and spot **correlated incidents** (many campaigns all dominated by "supply" in the same market = systemic A, page forecasting/infra rather than triaging campaigns one by one).
- **Systemic banners**: auto-detected cross-campaign patterns — "Forecast freshness degraded," "Solver replan storm (N replans/5m)," "Supply down >X% in market M." These convert N individual pages into one root cause.

---

## 7. Interaction Model & Cross-Filtering

- **One focus, cross-filtered**: campaign + time-window + selected-term + selected-cohort form a shared filter state. Every panel respects it. Selecting a waterfall bar, a cohort row, or a time-brush updates all others. This is what keeps the funnel coherent.
- **Time brush** on any timeline narrows the whole page to that window — essential for "what changed between 14:00 and 14:10."
- **Pause/freeze** during reading; the 15s refresh shouldn't yank the view out from under analysis. A subtle "3 newer updates — click to refresh" affordance instead of auto-jumping.
- **Compare-to-baseline** toggle (same campaign yesterday, or peer cohorts) on supply/win-rate panels — diagnosing GD is mostly "vs what it should have been."
- **Drill, don't navigate away**: Step 4 swaps in place; the on-call never loses the framing context at the top.
- **Keyboard-first** for incident speed: pin campaign, cycle dominant term, jump to verdict.

---

## 8. Performance — Making 15s Refresh Real Over 20k Cohorts

The hard constraint is interactive latency on a campaign that may touch thousands of cohorts, refreshing every 15s, possibly for several simultaneous incidents.

**Principles:**
1. **Never scan raw impressions live.** All incident panels read pre-aggregated rollups (§3.4) via `AggregatingMergeTree` materialized views maintained continuously. Raw is for offline forensics only.
2. **Pre-compute the identity terms, not just counts.** `campaign_cohort_minute` already stores supply/eligibility/reservation-share/win-rate/throttle, so the waterfall is a cheap `SUM ... GROUP BY term` over one campaign's cohorts — no wide joins at query time.
3. **Two query tiers per refresh:** a *cheap header/Step-1 query* (single campaign_minute scan, every 15s) and *heavier Step-2/3 queries* that run on focus and on a slightly slower cadence (e.g. 30s) or on demand. Big numbers stay live; deep panels don't all re-fire every 15s.
4. **Focus-narrowed continuous aggregation:** pinning a campaign registers its cohort set so background jobs keep that subset hot; queries hit a small partition, not the global 20k×campaigns space.
5. **ClickHouse-friendly schema:** order keys `(campaign_id, toStartOfMinute(ts), cohort_id)`; partition by day; projections on commonly-grouped dimensions (market/device/placement) so the group-by toggles in 3a use projections, not full re-aggregation.
6. **Audit events are annotations, not joins:** fetched by `(campaign_id, time-range)` from an indexed events table and overlaid client-side. Cheap and decoupled from the heavy delivery queries.
7. **Forecast vintages stored explicitly** (forecast keyed by `(cohort, horizon, vintage_ts)`) so the A-vs-B comparison is a lookup, not a recomputation.
8. **Pre-computed attribution job:** the sequential waterfall attribution per focused campaign runs in a small worker every 30s and is cached, so opening the panel is instant and the verdict draft is ready. Avoids Shapley-style math in the browser per refresh.

**Budget target:** Step-1 header < 300ms p95; full incident view first paint < 2s; 15s refresh touches only the cheap tier.

---

## 9. Beyond the Single Incident

- **Verdict telemetry**: every resolved incident's A–H tag + dominant term is logged. A small trend panel ("recurring root causes this week/month") tells leadership whether the system is structurally under-forecasting (B), the solver is unstable (G), or pacing is mis-tuned (E) — turning one-off firefighting into systemic fixes.
- **MTTD/MTTR tracking** on this dashboard's own usage: are on-calls reaching a verdict faster over time? Validates the design.
- **Calibration loop**: feed confirmed-B (forecast error) incidents back to the forecasting team's accuracy dashboards, keyed by cohort, so the worst-calibrated cohorts get attention.

---

## 10. Explicitly Out of Scope / Known Limitations

- **Attribution is an approximation.** The waterfall's term-by-term loss depends on decomposition order; we fix and document the order and label it "indicative." When the gap splits evenly across terms, the panel says so rather than forcing a single cause.
- **No automated remediation.** The dashboard diagnoses and hands off; it does not bump priority, edit reservations, or re-pace. (A deliberate boundary — remediation actions need their own guardrails.)
- **Billing/measurement reconciliation** (viewability, IVT, final billable counts) lives elsewhere; here we use serving-side counts, which is correct for *diagnosing* delivery but not for contractual settlement.
- **Cold cohorts / brand-new campaigns** with little history have weak baselines; the supply/win-rate baselines degrade gracefully to "insufficient history" rather than showing misleading comparisons.
- **The taxonomy is opinionated.** If real incidents keep landing as "other," that's a signal to extend Section 2 — the design assumes the taxonomy is a living artifact.

---

## 11. Summary

The dashboard is a **top-down diagnostic funnel** organized around a fixed root-cause taxonomy (A–H) and a single **delivery-decomposition identity**. It (0) verifies data trust, (1) frames severity and urgency, (2) **attributes the delivery gap to a specific term via a waterfall** — the centerpiece that converts "underdelivered" into "underdelivered because," (3) localizes it in cohort-space and time with planner-audit overlays, and (4) confirms the verdict in a cause-specific drill, then hands off with a tagged, permalinked evidence package. Pre-aggregated ClickHouse rollups and focus-narrowed continuous aggregation make the 15s incident refresh feasible over 20k cohorts.
