# Planner-observability prototype — Forecast Explorer

A runnable Vite + React + TS skeleton emitted by the `planner-observability` skill
(PROTOTYPE mode). It boots with **no backend** against a deterministic mock adapter
and demonstrates the load-bearing patterns so you extend the parts that are hard to
get right, already correct.

## Run

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check + production build
```

## What it demonstrates (the parts that are easy to get wrong)

| Pattern | Where | Reference |
|---|---|---|
| **Calibrated** forecast-vs-actual band + SLA `markLine` | `src/charts/ForecastVsActualChart.tsx` | `12-forecast-explainability.md` |
| Server-state / UI-state split (Query vs Zustand) | `src/queries.ts`, `src/store.ts` | `18-react-architecture.md` |
| Query keys scoped so a filter doesn't refetch everything | `src/queries.ts` | `18` (IM1) |
| Virtualized 20k-row cohort table | `src/components/CohortTable.tsx` | `18` (IM2) |
| Selection propagation / cross-filter | `store.ts` → chart + table | `17-analytics-ux.md` |
| Keyboard nav (`/`, `Esc`, ↑/↓) | `src/App.tsx`, `CohortTable.tsx` | `17`, `94` |
| No color-only encoding (anomaly glyphs) | `CohortTable.tsx`, `index.css` | `94-accessibility.md` (AC1) |

## File map

```
src/
  main.tsx                     QueryClient + providers
  App.tsx                      global keyboard shortcuts
  store.ts                     Zustand UI state (timeRange, cohortFilter, selection)
  queries.ts                   TanStack Query hooks (keyed on filter/selection)
  data/mockAdapter.ts          deterministic synthetic forecast/cohort data
  components/
    DashboardShell.tsx         filter bar + master/detail layout
    Panel.tsx                  loading/error/empty boundary
    CohortTable.tsx            virtualized, keyboard-navigable, selection-driving
  charts/
    EChart.tsx                 ECharts lifecycle wrapper (useRef + setOption)
    ForecastVsActualChart.tsx  forecast + calibrated band + SLA line
```

## Extend it

The `TODO` markers in `DashboardShell.tsx` point at the next panels (error
decomposition, calibration view, planner-impact overlay) and the reference that
governs each. Swap `data/mockAdapter.ts` for real API calls — the query hooks and
components don't change.
