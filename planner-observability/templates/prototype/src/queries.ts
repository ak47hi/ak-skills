import { useQuery } from '@tanstack/react-query';
import {
  getForecastSeries,
  getCohorts,
  withLatency,
  type ForecastSeries,
  type CohortRow,
} from './data/mockAdapter';
import { useUiStore } from './store';

// TanStack Query hooks over the mock adapter. The KEY DESIGN is the point
// (references/18-react-architecture.md): each key encodes exactly the inputs the
// panel depends on, so changing the cohort filter refetches the cohort list but
// NOT the forecast series of an already-selected cohort, and vice versa. This is
// what makes cross-filtering cheap (anti-pattern IM1).

export function useForecastSeries(cohortId: string | null) {
  return useQuery<ForecastSeries | null>({
    queryKey: ['forecast', cohortId],
    queryFn: () =>
      cohortId ? withLatency(getForecastSeries(cohortId)) : Promise.resolve(null),
    enabled: cohortId !== null,
  });
}

export function useCohorts() {
  // Depends only on the filter — NOT on the selected cohort or time range, so
  // drilling into a cohort doesn't refetch the (large) list.
  const cohortFilter = useUiStore((s) => s.cohortFilter);
  return useQuery<CohortRow[]>({
    queryKey: ['cohorts', cohortFilter],
    queryFn: () => {
      const all = getCohorts();
      const filtered = cohortFilter
        ? all.filter((r) => r.cohortId.includes(cohortFilter))
        : all;
      // Sort by anomaly score so the worst cohorts surface first.
      filtered.sort((a, b) => b.anomalyScore - a.anomalyScore);
      return withLatency(filtered);
    },
  });
}
