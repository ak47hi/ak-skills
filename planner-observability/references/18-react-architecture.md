# React architecture

Load when the prompt touches React, component, TanStack, Zustand, ECharts, virtualize, data flow, state. Always loaded in PROTOTYPE mode. This is the implementation lane — the component structure and data flow that make the design runnable and the scale concerns (virtualization, query caching) tractable.

Stack default: **React + TypeScript, Vite, TanStack Query (server-state), Zustand (UI-state), ECharts via `echarts-for-react`, `@tanstack/react-virtual` (large tables).** Each choice earns its place below.

## The two kinds of state — keep them separate

The single most common architecture bug is conflating server state with UI state. They have different lifecycles and different tools.

- **Server state → TanStack Query.** Anything fetched: time-series, cohort rows, allocation data. Query gives caching, deduplication, background refetch, stale-while-revalidate, and loading/error states for free. Never put fetched data in a global store and hand-manage refetch — that's reimplementing Query, badly.
- **UI state → Zustand.** The cross-cutting interaction state: selected time range, cohort filter, selected cohort/anomaly, drill level. Small, synchronous, shared across panels. This is the shared-context contract from `10` and `17` made concrete.

```
Zustand store (timeRange, cohortFilter, selection)
        │  read by
        ▼
useQuery(['delivery', cohortFilter, timeRange], fetchDelivery)   ← TanStack Query
        │  key includes the filter state
        ▼
Panel → ECharts option   ← re-renders when its query data changes
```

## Component structure

```
App
└─ QueryClientProvider
   └─ DashboardShell            ← global filter bar (time range, cohort filter); tier layout
      ├─ TierSummary            ← Tier 1: KPI stats (executive-overview)
      ├─ TierHealth             ← Tier 2: tabbed subsystem health panels
      │   └─ PanelGrid
      │       └─ Panel          ← title, loading/error boundary, drill affordance
      │           └─ Chart      ← ECharts wrapper (forecast-vs-actual, heatmap, Sankey…)
      └─ TierDrill              ← Tier 3: per-cohort detail, allocation diff, CohortTable
```

`Panel` owns the loading/error/empty states (driven by its `useQuery` status) so individual charts stay pure "data → ECharts option" functions. The chart components take data props and return an `option`; they don't fetch. This keeps charts testable and reusable.

## Query-key design — don't refetch everything on every filter

The query key encodes exactly the inputs a panel depends on: `['delivery', cohortFilter, timeRange]`. Changing the cohort filter invalidates and refetches only the panels keyed on `cohortFilter`; a panel keyed only on `timeRange` is untouched. Getting the keys right is what makes cross-filtering cheap. **Refetching all panels on every filter change** (one giant query, or keys that include everything) is the implementation anti-pattern that makes a dashboard feel sluggish — it's a key-design bug, not a "need a faster backend" problem.

Set sensible `staleTime` (e.g. 15 s for live health, minutes for historical) so navigating back to a panel doesn't refetch needlessly, and use `refetchInterval` only on the live-monitoring panels that actually need it.

## Virtualization — high-cardinality tables

A cohort table at 20k / 200k / 2M rows **must not render all rows**. Rendering 200k `<tr>` freezes the tab and blows out memory. Use `@tanstack/react-virtual` to render only the visible window (plus a small overscan); the DOM holds ~30 rows regardless of dataset size. This is non-negotiable past ~10k rows.

Past the point where even *fetching* all rows is wasteful (~100k+), the table goes **server-side**: the backend paginates/aggregates, the client virtual-scrolls over a windowed query (TanStack Query infinite query keyed on the scroll offset + filter). Client-side aggregation of a million high-cardinality rows is the design bug; aggregate in the OLAP store and drill on demand.

## ECharts wrapper

A thin `<EChart option={...} />` wrapper around `echarts-for-react` (or a `useRef` + `setOption` effect) that:

- Takes a memoized `option` (compute it with `useMemo` keyed on the data, so unrelated re-renders don't rebuild the chart).
- Calls `setOption(option, { notMerge: false })` so updates are incremental (smooth live refresh), not full rebuilds.
- Disposes the instance on unmount.
- Enables `large: true` + `sampling: 'lttb'` for dense series, and a `dataZoom` for time navigation.

Keep ECharts options in the chart component, not the design doc — the design doc says "forecast-vs-actual line with a p10–p90 band and an SLA `markLine`"; the component is where that becomes an `option`.

## Anti-patterns this reference exists to prevent

- Fetched data in a global store with hand-managed refetch (reimplementing Query).
- Query keys that don't encode the filter → refetch-everything on every interaction.
- Unvirtualized table past ~10k rows.
- Client-side aggregation of high-cardinality data that should be aggregated server-side.
- Chart components that fetch their own data (untestable, un-cacheable, no shared loading state).
- Rebuilding the whole ECharts option on every render instead of `useMemo` + incremental `setOption`.
