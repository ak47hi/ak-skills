# Analytics UX

Load when the prompt touches cross-filter, keyboard, tooltip, click path, drill mechanics, linked brushing. This is the interaction model — how a power user moves through the surface to a decision. Optimize for the operator who uses this dashboard fifty times a week, not the first-time visitor; minimize click paths and never make them reach for the mouse when a key would do.

## Cross-filtering and linked brushing

The whole surface is one filtered context. Setting a filter (time range, cohort, market) in any panel applies to all of them; the panels are *lenses on one dataset*, not independent widgets.

- **Linked brushing** — selecting a time window on one chart highlights the same window on all charts (shared `markArea` / brush state). Brushing the anomalous window on the delivery curve highlights it on the pacing trace and the forecast chart simultaneously, so the correlation is visible without re-navigating.
- **Selection propagates** — clicking a cohort in the heatmap filters the delivery curve, the allocation diff, and the reservation panel to that cohort. The investigation carries its subject from panel to panel.
- **Global filter bar** — time range + primary dimension filters live at the top, persistent, inherited by every tier and tab (the shared-state contract from `10-information-arch.md`).

## Keyboard navigation for power users

The on-call in an incident shouldn't be hunting menus with a mouse. Provide:

- **`/`** to focus search / cohort filter (the single most-used action).
- **`j` / `k`** to move through rows of the cohort table / anomaly list; **Enter** to drill into the selected row.
- **`[` / `]`** to step the time range backward/forward by one window.
- **`Esc`** to pop up one drill level (out of a cohort detail back to the heatmap).
- **`?`** for the shortcut overlay.

Keyboard nav is also an accessibility requirement (`94-accessibility.md`), not just a power-user nicety — every interactive element must be reachable and operable without a pointer.

## Tooltip discipline

- **Critical values are visible without hover.** If the reader *needs* a number to make the decision, it's a label or an axis tick, not buried in a hover tooltip. Hover is for secondary detail (the exact value at an arbitrary point), never for the headline. A dashboard where you must hover each bar to read it is a dashboard that's hostile to scanning.
- **Tooltips show context, not just the value** — value + delta vs target + the cohort/timestamp, so the hover answers "is this bad" not just "what is this."
- **One tooltip, aligned across linked charts** — hovering a time on one chart shows the crosshair value on all linked charts at that time (a synced axis-pointer), so the reader reads the whole system state at that instant.

## Drill mechanics: in-place over modal

- **Expand in place** — drilling into a cohort expands a detail region inline (or a side panel), keeping the overview visible for context. The reader sees where they came from.
- **Avoid modal drill** — a modal that covers the overview breaks the investigation flow and loses the surrounding context that made the anomaly legible. Modals are for confirmations, not for drill-down.
- **Breadcrumbs** — the drill path (overview → cohort X → allocation diff) is shown and clickable, so the reader can step back to any level. `Esc` pops one level.
- **Short paths** — the click path from "something's wrong" (Tier 1) to "here's the root cause" (Tier 3) should be ≤3 clicks. Count it; if it's longer, the hierarchy is wrong (`10-information-arch.md`).

## The investigation as the unit of design

Design the *path*, not the panels. Pick the top three questions the persona asks ("why did cohort X underdeliver," "is the forecast drifting," "what changed in the last replan") and make each a short, keyboard-drivable, context-preserving path from entry to answer. Panels are the stops on those paths; a panel that isn't on any path is decoration.

## Anti-patterns this reference exists to prevent

- No cross-filtering (panels as independent widgets; correlations invisible).
- Mouse-only (no keyboard nav) — slow for power users, inaccessible for others.
- Critical value hidden behind hover.
- Modal-heavy drill that breaks flow and loses context.
- A drill path longer than ~3 clicks from anomaly to root cause.
