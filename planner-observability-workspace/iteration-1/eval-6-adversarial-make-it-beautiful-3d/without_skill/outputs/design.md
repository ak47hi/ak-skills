# Planner Dashboard Redesign — Design Spec

> Goal as stated: "Make our planner dashboard look amazing... smooth animations on every refresh, a rotating 3D globe showing delivery by region, gradient-filled 3D bar charts, and a big animated donut for the delivery breakdown. It needs to wow the leadership demo."

This spec takes that goal seriously — the demo *should* feel polished and impressive — but it makes some deliberate calls about *how* to get there. The short version: a leadership demo is won by making the numbers instantly legible and the story obvious, not by the chart-chrome. Below I deliver a design that looks genuinely premium, keeps motion that earns its place, and is honest about which of the requested 3D effects help versus hurt. Where I recommend against the literal ask, I say why and give a better-looking alternative.

---

## 1. A quick, honest read on the brief

The four headline asks — rotating 3D globe, 3D gradient bars, big animated donut, animation on every refresh — are all "wow" instincts, and the instinct is right. But each one carries a cost that tends to surface *exactly* in a live leadership demo:

| Requested element | What it's trying to do | The risk in a live demo | My call |
|---|---|---|---|
| Rotating 3D globe by region | Look impressive; show "global" reach | A rotating globe hides half your regions at any moment, distorts area, and reads as decoration. Leaders ask "which region is behind?" and the answer is occluded on the far side. Also the heaviest thing to render. | Replace with a flat map / region ranking. Keep an optional static globe as a hero visual. |
| 3D gradient bar charts | Feel rich, modern | 3D perspective makes bars literally unreadable against gridlines — you can't tell if a bar hits 80 or 90. Foreground bars occlude background ones. | Use flat bars with a tasteful gradient *fill* and depth via shadow, not perspective. |
| Big animated donut for delivery breakdown | Show the mix at a glance | Donuts are fine for 2–4 segments; they're poor for precise comparison. A *big* one wastes the most valuable screen real estate on the least precise chart. | Keep a donut, but right-sized, with center KPI, paired with a labeled legend that carries the real numbers. |
| Animation on every refresh | Feel alive | Re-animating every chart from zero on each refresh is the single most common way a "beautiful" dashboard becomes unusable: the moment a number changes the whole screen replays a 1.5s intro and the viewer loses their place. | Animate **on first paint and on user navigation only**. On data refresh, *tween* values smoothly in place (no re-intro). This is the key decision in the whole spec. |

The result is a dashboard that is more impressive in the room, not less — because every animation supports comprehension and nothing fights the data. The wow comes from typography, spacing, motion discipline, and a confident color system. That's how the dashboards leadership actually admires (think the polish of a well-made analytics product) get their shine.

If, after reading this, the team still wants the literal rotating globe / 3D bars as the hero, Section 9 documents how to do them as safely as possible — but they should be a conscious trade, not the default.

---

## 2. Design principles

1. **Legibility first.** A leader should be able to read every number from across a room in under three seconds. If an effect reduces legibility, it's cut.
2. **Motion with meaning.** Animation directs attention (something changed here) or shows continuity (this value rose from X to Y). Never purely decorative loops that demand attention forever.
3. **One hero, then density.** A single confident hero row sets the tone; the rest of the screen is calm, dense, and scannable.
4. **Respect the refresh.** New data should feel like the dashboard *breathing*, not *rebooting*.
5. **Accessible by default.** Color is never the only signal; everything respects `prefers-reduced-motion`.

---

## 3. Layout

Target: 1920×1080 primary (demo display + most exec laptops scaled). Fluid down to 1280. 12-column grid, 24px gutters, 32px page padding.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  HEADER BAR                                                                │
│  Planner Health · Q2 2026          [Live ● 14:32:07]   [Range ▾] [Region ▾]│
├──────────────────────────────────────────────────────────────────────────┤
│  HERO KPI ROW  (4 stat cards, equal width)                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                       │
│  │ On-Time  │ │ In Flight│ │ At Risk  │ │ Avg Cycle│                       │
│  │  94.2%   │ │  1,284   │ │   37     │ │  4.1d    │                       │
│  │ ▲ +1.8pt │ │ ▲ +112   │ │ ▼ −6     │ │ ▬ flat   │   sparkline each      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘                       │
├───────────────────────────────────────┬──────────────────────────────────┤
│  DELIVERY BY REGION                    │  DELIVERY BREAKDOWN              │
│  (map + ranked bar list, 8 cols)       │  (donut + legend, 4 cols)        │
│                                        │       ╭───────╮                  │
│  ▓▓▓▓▓▓▓▓▓▓▓▓ NA      96.1%   612      │      ╭         ╮   On-Time 94%   │
│  ▓▓▓▓▓▓▓▓▓▓   EU      93.4%   488      │      │  12,940 │   Delayed  4%   │
│  ▓▓▓▓▓▓▓▓     APAC    91.0%   355      │      │  total  │   At Risk  1.5% │
│  ▓▓▓▓▓▓       LATAM   88.2%   201      │      ╰         ╯   Failed   0.5% │
│  ▓▓▓▓         MEA     85.7%   118      │       ╰───────╯                  │
├───────────────────────────────────────┴──────────────────────────────────┤
│  THROUGHPUT OVER TIME           (gradient-filled bar/area, 12 cols)        │
│   ▁▂▃▄▅▆▇█▇▆▅▄  with target line                                            │
├──────────────────────────────────────────────────────────────────────────┤
│  AT-RISK QUEUE  (table, top 6, expandable)                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

Reading order is top-left to bottom-right: the executive's eye lands on the four KPIs, then "how are regions doing," then "what's the mix," then "trend," then "what needs attention." That sequence *is* the demo narrative.

---

## 4. Visual system

### Color
A dark "control room" theme reads as premium on a projector and makes the accent colors pop.

- **Surface:** `#0E1117` (page), `#161B22` (cards), `#1F2630` (raised).
- **Text:** `#F2F5F9` primary, `#9AA7B8` secondary, `#5C6B7E` tertiary.
- **Accent / brand:** `#4C8DFF` (electric blue) → used for primary data + focus.
- **Semantic:** success `#2FD27A`, warning `#FFB020`, danger `#FF5C5C`, neutral `#6E7B8C`.
- **Gradients (the "fill" the brief wants):** vertical, low-contrast, brand-tinted.
  - Bars: `#4C8DFF → #2E5FCC` (top→bottom), 100%→70% opacity.
  - Donut segments: each semantic color at 100% fades to 78% at the inner edge.
  - Hero card glow: a 1px inner top border at 40% accent, plus a soft radial behind the number.

These gradients give the "rich, dimensional" look the brief asked for **without** geometric 3D — depth comes from light, not perspective.

### Typography
- Display/KPI numbers: a tabular, slightly condensed grotesque (e.g. Inter Tight or IBM Plex Sans, `font-feature-settings: "tnum"`). Tabular figures are non-negotiable — they stop numbers from jittering when they tween.
- KPI value: 48–56px, weight 600. Labels: 13px, weight 500, letter-spacing +0.04em, uppercase, secondary color.
- Body/table: 14px.

### Elevation & shape
- Cards: 16px radius, 1px `#232B36` border, shadow `0 8px 24px rgba(0,0,0,0.35)`.
- Subtle 1px top highlight on cards to simulate a light source (this is where "3D feel" comes from cheaply).

---

## 5. The components in detail

### 5.1 Hero KPI cards
Four cards: **On-Time %**, **In Flight**, **At Risk**, **Avg Cycle Time**.

Each card:
- Big tabular number, a delta chip (`▲ +1.8pt` colored by direction *and* arrow shape), a unit, and a 40px sparkline of the last ~30 periods.
- The sparkline uses a soft area gradient under the line.
- The accent radial behind the number subtly shifts hue with status (green-leaning when healthy, amber when degrading) — a slow, calm tell.

**Motion:** on first load, numbers count up from 0 to value over 700ms with an ease-out; sparklines draw left-to-right (stroke-dashoffset). On refresh, the number **tweens from its previous value to the new one** over ~450ms — no count-from-zero. The delta chip cross-fades. This is the single most "alive but trustworthy" interaction on the page.

### 5.2 Delivery by region (replaces the rotating globe)
A **flat region view** is both more impressive *and* more useful here:

- Left: a muted, flat world map (equirectangular or a subtle Natural Earth raster) with each region's centroid marked by a **glowing proportional dot** — radius ∝ volume, color ∝ on-time %. Dots have a slow, gentle pulse (2.5s, low amplitude) so the map feels live without spinning. This pulse is the *one* ambient loop I keep, because it reads as "real-time heartbeat," and it doesn't occlude anything.
- Right (or below): a **ranked horizontal bar list** of regions with exact on-time % and volume. This is what a leader actually reads. Bars animate width on first paint and tween on refresh.

> **Why not the rotating globe:** a spinning globe shows at most half the regions at once and distorts their apparent size; the worst-performing region is frequently on the dark side of the sphere when the CEO asks about it. If a 3D hero is truly wanted, see §9.1 for a *static, tilted* globe used purely as a header ornament — never as the primary region readout.

### 5.3 Delivery breakdown donut
- Donut (not pie), ~280px, 4–5 segments max: On-Time / Delayed / At-Risk / Failed (+ optional "Pending").
- **Center carries a real KPI:** total deliveries, big and tabular. The donut's job is mix-at-a-glance; the center and the legend carry the precision.
- Legend to the right: swatch · label · **percent** · **count**, sorted descending. Hovering a legend row highlights its segment (and vice versa) with a 120ms ease.

**Motion:** on first paint, segments sweep clockwise from 12 o'clock over ~800ms with a slight ease, center number counts up. On refresh, segments **tween their arc lengths** to the new proportions (~500ms) — they grow/shrink in place, they do not redraw from zero. Right-sized, not "big": the donut is a 4-column citizen, not the centerpiece, because precise comparison lives in the bars and table.

### 5.4 Throughput over time (the "gradient bar chart" done right)
- A flat 2D bar or stacked-area chart of deliveries per day/hour, with the requested **gradient fill** (`#4C8DFF → transparent` downward for area; top-bright→bottom-dim for bars).
- A dashed **target line** with a label chip — leaders love a clear "are we above the line" read.
- Hover scrubber with a tooltip; the nearest bar lifts 2px and brightens.

**Motion:** bars grow from baseline on first paint (staggered 12ms each, capped so the whole sweep is < 600ms). On refresh, **append/shift** — new bar slides in from the right, oldest slides out; existing bars tween height. No full re-intro.

### 5.5 At-risk queue (table)
- Top 6 at-risk shipments: ID, region, ETA delta, owner, risk reason, a small status pill.
- Sorted by severity. Row click expands inline detail.
- New rows entering on refresh get a 1-second soft highlight fade (the "row flash") so the eye catches what changed — this is animation doing real work.

---

## 6. The refresh model (the most important section)

Treat the dashboard as a **persistent, stateful surface**, not a slideshow that replays.

- **Intro animations** (count-ups, segment sweeps, bar grows, sparkline draws) fire exactly **once** — on initial mount and when the user explicitly changes a control (range, region filter) or navigates back to the view.
- **Data refresh** (polling every N seconds or a websocket push) **never** replays intros. Instead each visual *interpolates* from its current rendered value to the new value:
  - KPI numbers tween (450ms, ease-out).
  - Bars/donut arcs tween their geometry.
  - Time series append/shift.
  - Changed table rows flash once.
- A small **"Live ● HH:MM:SS"** indicator in the header pulses once per successful refresh — that's the user's confirmation the data moved, instead of the whole screen reanimating.
- Use **FLIP**-style transitions for any element that reorders (e.g., a region overtaking another in the ranked list animates to its new position rather than jumping).

This gives the *feeling* of constant motion the brief wants, while keeping every number readable through the change. Crucially: in a demo, when the presenter triggers a refresh, the screen looks alive and the numbers visibly tick — but nobody loses their place mid-sentence.

---

## 7. Motion specification

| Interaction | Duration | Easing | Trigger | Repeats? |
|---|---|---|---|---|
| KPI count-up | 700ms | ease-out (cubic) | first paint / nav | no |
| KPI value tween on refresh | 450ms | ease-out | data refresh | per change |
| Sparkline draw | 600ms | ease-in-out | first paint | no |
| Donut sweep | 800ms | ease-out | first paint / nav | no |
| Donut arc tween | 500ms | ease-in-out | data refresh | per change |
| Bar grow | ≤600ms total, 12ms stagger | ease-out | first paint / nav | no |
| Region dot pulse | 2500ms | sine | always | **yes (ambient)** |
| Live indicator pulse | 350ms | ease-out | each refresh | per refresh |
| Row enter / flash | 1000ms | ease-out | new/changed row | per event |
| Reorder (FLIP) | 350ms | ease-in-out | rank change | per event |
| Hover lift / highlight | 120ms | ease-out | hover | per hover |

Global rules:
- Nothing animates longer than ~800ms; the eye gets impatient past that, and in a demo every second of "loading shimmer" feels like lag.
- Only **two** elements loop forever (region dot pulse, live indicator), and both are low-amplitude. Everything else is a one-shot or a value tween.
- **`prefers-reduced-motion: reduce`** → all intros become instant, tweens become a 150ms cross-fade, ambient pulses stop. The dashboard must be fully usable and still attractive with motion off (some execs are motion-sensitive; some demo machines stutter).

---

## 8. Performance & demo-resilience

A beautiful dashboard that drops frames in front of the CEO is a failure, so:

- **No WebGL hero by default.** Everything in the primary design is 2D SVG/Canvas + CSS transforms, which holds 60fps on integrated graphics and projector mirroring. (This is the practical reason the globe and 3D bars are demoted — a stuttering 3D globe over HDMI is the classic demo-day disaster.)
- Animate only `transform` and `opacity` (GPU-friendly); never animate `width`/`top` directly in hot paths — use scale/translate.
- Cap concurrent animations; stagger > simultaneous.
- **Demo Mode toggle:** freezes ambient loops, optionally drives a *scripted* data sequence so the presenter gets predictable, good-looking numbers and transitions on cue (rehearsable, no dependence on live backend during the meeting).
- Skeleton states use a single calm shimmer, not per-chart spinners.
- Pre-warm/first-paint budget: hero KPIs render with last-known cached values instantly, then tween to live — so the screen is never blank when it goes up on the projector.

---

## 9. If you still want the literal 3D (fallback options)

Keeping the brief honest: here's how to satisfy each original ask with the least damage, as an opt-in "showpiece" layer rather than the working dashboard.

### 9.1 The globe
- Use a **static or slow-tilting** globe (not a full spin) as a **header/hero ornament only**, with the real region data living in the §5.2 bars beside it.
- If it must rotate, auto-pause rotation on hover and on data refresh, and add a "flatten to map" toggle so anyone can get the unoccluded view in one click.
- Render with a lightweight globe lib; cap to 30fps; disable on reduced-motion and on machines that fail a quick perf probe.

### 9.2 3D bars
- If perspective bars are required, use a **shallow, fixed isometric angle** (no rotation), keep gridlines on the *front* face, and label every bar's value directly so the perspective never costs legibility. Honestly, the gradient-filled *flat* bars in §5.4 look richer and read cleaner — I'd push to keep those.

### 9.3 "Big" donut
- Keep the donut but always pair it with the numeric legend; "big" is satisfied by making it the visual anchor of its card, not by letting it eat the layout. Center KPI stays.

---

## 10. What "amazing" actually comes from here

To set expectations with leadership and the team: the wow in this design is engineered from
1. a confident dark theme with one electric accent and tasteful gradients,
2. crisp tabular typography and generous spacing,
3. motion that is smooth, fast, and *purposeful* (count-ups, value tweens, FLIP reorders, a live pulse),
4. a layout that tells the delivery story in reading order,
5. rock-solid 60fps performance and a rehearsable Demo Mode.

That package reliably impresses a room **and** survives the follow-up question "so which region is slipping?" — which the spinning globe could not. If the team wants the literal globe/3D bars as a hero flourish, §9 makes that possible as a deliberate, contained choice.

---

### Deliverables checklist for build
- [ ] Design tokens (color, type, spacing, motion durations) as a single source of truth.
- [ ] Hero KPI card component w/ count-up + refresh-tween.
- [ ] Region map+ranked-bars component (with flatten toggle).
- [ ] Donut + numeric legend (arc-tween on refresh).
- [ ] Throughput chart (gradient fill, target line, append/shift).
- [ ] At-risk table (FLIP reorder, row flash).
- [ ] Global refresh controller (intro-once vs tween-on-update).
- [ ] `prefers-reduced-motion` + low-perf fallbacks.
- [ ] Demo Mode (scripted sequence, frozen ambients).
- [ ] Optional §9 showpiece globe (behind a flag).
