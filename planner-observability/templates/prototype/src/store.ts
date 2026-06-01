import { create } from 'zustand';

// UI state shared across every panel and tier. This is the "context that must
// persist across the hierarchy" from references/10-information-arch.md and the
// cross-filter contract from references/17-analytics-ux.md: time range, cohort
// filter, and current selection follow the reader down every drill.
//
// Server data is NOT here — that's TanStack Query (src/queries.ts). This store
// holds only synchronous UI state. Query keys read from it so a filter change
// invalidates exactly the panels that depend on it.

export type TimeRange = { from: number; to: number };

export interface UiState {
  timeRange: TimeRange;
  cohortFilter: string; // substring match on cohort id; '' = all
  selectedCohortId: string | null; // the cohort the reader drilled into
  setTimeRange: (r: TimeRange) => void;
  setCohortFilter: (q: string) => void;
  selectCohort: (id: string | null) => void;
}

// Default window: a synthetic 48-tick horizon (see mockAdapter). Ticks are
// hours; the dashboard treats [from, to] as an inclusive tick range.
export const DEFAULT_RANGE: TimeRange = { from: 0, to: 47 };

export const useUiStore = create<UiState>((set) => ({
  timeRange: DEFAULT_RANGE,
  cohortFilter: '',
  selectedCohortId: null,
  setTimeRange: (timeRange) => set({ timeRange }),
  setCohortFilter: (cohortFilter) => set({ cohortFilter }),
  selectCohort: (selectedCohortId) => set({ selectedCohortId }),
}));
