import { useEffect } from 'react';
import { useUiStore } from '../store';
import { useCohorts, useForecastSeries } from '../queries';
import { Panel } from './Panel';
import { CohortTable } from './CohortTable';
import { ForecastVsActualChart } from '../charts/ForecastVsActualChart';

// The shell: a global filter bar (cohort filter) backed by Zustand, a master
// (cohort table) / detail (forecast chart) layout. This is a single-category
// slice (forecast-explorer) of the three-tier hierarchy
// (references/10-information-arch.md) — extend with TierSummary / TierHealth.

export function DashboardShell() {
  const cohortFilter = useUiStore((s) => s.cohortFilter);
  const setCohortFilter = useUiStore((s) => s.setCohortFilter);
  const selectedCohortId = useUiStore((s) => s.selectedCohortId);
  const selectCohort = useUiStore((s) => s.selectCohort);

  const cohortsQ = useCohorts();
  const forecastQ = useForecastSeries(selectedCohortId);

  // Default the selection to the top (most anomalous) cohort once loaded.
  useEffect(() => {
    if (!selectedCohortId && cohortsQ.data && cohortsQ.data.length > 0) {
      selectCohort(cohortsQ.data[0].cohortId);
    }
  }, [selectedCohortId, cohortsQ.data, selectCohort]);

  return (
    <div className="shell">
      <header className="shell__bar">
        <h1 className="shell__title">Forecast Explorer</h1>
        <input
          className="shell__filter"
          type="search"
          placeholder="Filter cohorts (e.g. US-mobile)…  [press /]"
          aria-label="Filter cohorts"
          value={cohortFilter}
          onChange={(e) => setCohortFilter(e.target.value)}
        />
        <span className="shell__hint">
          mock data · {cohortsQ.data ? cohortsQ.data.length.toLocaleString() : '…'} cohorts
        </span>
      </header>

      <div className="shell__grid">
        <div className="shell__col shell__col--list">
          <Panel
            title="Cohorts"
            status={cohortsQ.status}
            isEmpty={(cohortsQ.data?.length ?? 0) === 0}
            emptyHint="No cohorts match the filter."
          >
            {cohortsQ.data && <CohortTable rows={cohortsQ.data} />}
          </Panel>
        </div>

        <div className="shell__col shell__col--detail">
          <Panel
            title="Forecast vs actual"
            status={selectedCohortId ? forecastQ.status : 'success'}
            isEmpty={!selectedCohortId || !forecastQ.data}
            emptyHint="Select a cohort to see its forecast."
          >
            {forecastQ.data && <ForecastVsActualChart series={forecastQ.data} />}
          </Panel>

          {/* TODO: add the error-decomposition panel (bias/variance + attribution
              heatmap) — references/12-forecast-explainability.md, panel 2. */}
          {/* TODO: add the calibration view (PIT + per-tier coverage trend) —
              references/12-forecast-explainability.md. */}
          {/* TODO: add the planner-impact overlay tying forecast error to the
              delivery curve — references/12 panel 4 + references/13. */}
        </div>
      </div>
    </div>
  );
}
