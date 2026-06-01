# Accessibility

Load in Phase 5 (MEASURE). Accessibility is not a compliance afterthought on an operational dashboard — the on-call reading it at 3am on a glare-y screen, the colorblind engineer, and the keyboard-only user are all *primary* users. These rules also make the dashboard more legible for everyone.

## No color-only encoding

The most common and most damaging violation. Under/over-delivery, healthy/breaching, anomaly/normal must **never be conveyed by color alone**. ~8% of men have red-green color vision deficiency; every grayscale print and every projector with bad color loses the signal entirely.

Pair color with a second channel:
- **Shape** — ▲ over-delivery, ▼ under-delivery, alongside the color.
- **Label** — the status word or the number, not just the hue.
- **Position** — above/below a zero line for signed values.
- **Pattern** — hatching for one state in a filled region.

A red cell in a heatmap is fine *if* the value is also the magnitude on a labeled, perceptually-uniform scale that a colorblind reader can still order.

## Color palettes

- **Sequential magnitude** — perceptually-uniform (viridis, magma, cividis). Cividis is explicitly colorblind-optimized.
- **Diverging (signed)** — a colorblind-safe diverging pair (e.g. blue↔orange, not red↔green) around a meaningful midpoint.
- **Categorical series** — a colorblind-safe qualitative palette (e.g. Okabe-Ito 8-color), and don't rely on color alone to distinguish lines — use direct labels at the line ends and/or distinct dash patterns.

## Contrast (WCAG AA)

- **Text** — ≥4.5:1 against its background (≥3:1 for large text).
- **Graphical objects** (lines, bars, key chart elements) — ≥3:1 against the background and adjacent elements. The common failure is thin light-gray series on white; thicken and darken them.
- Verify the on-call dark theme separately — contrast that passes on light often fails on dark.

## Keyboard-first navigation

Every interactive element reachable and operable without a pointer (this is also the power-user requirement from `17-analytics-ux.md`):
- Logical tab order; visible focus indicators (never `outline: none` with no replacement).
- The shortcut set (`/ j k Enter [ ] Esc ?`) operable from the keyboard.
- Drill, filter, and time-range controls all keyboard-operable — not just hover/click.

## Screen-reader / non-visual access

Charts are canvas/SVG — opaque to screen readers unless you provide a text alternative:
- An `aria-label` or caption summarizing the chart's takeaway ("Delivery 92% of commitment, falling since 14:00").
- A **toggleable data table** behind each chart — the underlying numbers in an accessible `<table>`. This doubles as the accessibility fallback *and* the "I want the exact numbers" power-user feature.
- Announce live updates politely (`aria-live="polite"`) so a refresh doesn't spam the SR or get missed.

## Motion

- Respect `prefers-reduced-motion` — disable chart entrance animations and transitions for users who set it.
- Don't animate on every data refresh; motion that fires every 15 s is a distraction, not an explanation (this overlaps the "explainability over animation" stance).

## How this feeds OUTPUT

The design doc's accessibility section names the palette choice, the no-color-only-encoding rule applied to the status panels, the contrast target, the keyboard map, and the data-table fallback. In AUDIT mode, AC1–AC3 in `93-anti-patterns.md` are graded against these.
