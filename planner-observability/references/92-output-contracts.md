# Output contracts

Load in Phase 6 (OUTPUT). Defines what each mode's artifact must contain. Maps to `templates/`.

## DESIGN → `templates/design-doc.md`

Required sections (the ten from the OUTPUT EXPECTATIONS, in order):

1. **Personas** — who reads this, and the decision each makes. ≥1, named, with the decision (not "stakeholders").
2. **Workflows** — the top 2-3 investigations as step-by-step paths with decision points (e.g. the why-underdeliver sequence from `13`).
3. **Dashboard hierarchy** — the three-tier structure (`10`), what lives at each tier, one-dashboard-vs-many decision.
4. **Panel set with chart rationale** — each panel: decision served + chart type + at least one alternative considered and why rejected (`11`, `90`).
5. **Interaction model** — cross-filtering, linked brushing, keyboard nav, tooltip discipline, drill mechanics (`17`).
6. **Drill-down strategy** — the explicit path from anomaly to root cause for each top-level panel (`13`).
7. **Scalability** — behavior at the stated cohort cardinality / data volume; virtualization, rollups, query-key design (`18`, `90`).
8. **Accessibility** — colorblind-safe palette, contrast, keyboard nav, no color-only encoding, SR labels (`94`).
9. **Implementation** — component structure + data flow (server-state vs UI-state split), chart library, key dependencies (`18`).
10. **Success metrics** — time-to-decision / time-to-root-cause / detection lead time, baseline + target (`91`).

Plus an **appendix anti-pattern checklist** walked against `93-anti-patterns.md`.

Match depth to the request: a narrow question gets a chat-mode answer, not the full template. The full template is for "design the X dashboard," not "should this be a bar or a line."

## PROTOTYPE → `templates/prototype/`

A runnable Vite + React + TS app. Required:

- **Boots unmodified** with `npm install && npm run dev`; renders with **no backend** (deterministic mock adapter).
- **DashboardShell** with a global filter bar (time range + cohort filter) backed by a **Zustand** store.
- **≥1 ECharts panel** that is a forecast-vs-actual line with a **calibrated uncertainty band** (band + a coverage/calibration note) and an SLA `markLine`.
- **A virtualized cohort table** (`@tanstack/react-virtual`) — proving the high-cardinality path.
- **TanStack Query hooks** over the mock adapter, with query keys encoding the filter state.
- **Mock data adapter** — deterministic synthetic forecast / actual / pacing / cohort series so the app runs offline and reproducibly.
- **TODO markers** at each extension point pointing to the matching reference (mirror the design-doc's panels → references).
- A short **README** with the run command and a map of which file implements which concern.

The contract is "runs and demonstrates the load-bearing patterns" (calibrated band, virtualization, query-keyed cross-filter), not "production-complete." It's a skeleton the team extends, with the hard-to-get-right parts already right.

## AUDIT → `templates/audit-report.md`

Required:

- **Findings table** — each row: panel/area → anti-pattern fired (cite `93-anti-patterns.md` id) → why it harms the decision → the fix → severity.
- **Prioritized remediation** — ordered by decision-impact, not by ease. The pie chart that misleads on the headline metric outranks a contrast nit.
- **What to keep** — the parts that work, so the audit isn't read as "tear it all down." Credibility comes from precision about what's fine.

## Cross-mode rule

After emitting any artifact, **walk `93-anti-patterns.md`**. Every pattern that fires is fixed before emitting (DESIGN/PROTOTYPE) or *is the finding* (AUDIT). An artifact that ships with an un-walked anti-pattern is incomplete.
