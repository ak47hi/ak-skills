import { useEffect } from 'react';
import { DashboardShell } from './components/DashboardShell';
import { useUiStore } from './store';

export function App() {
  // Global keyboard shortcuts (references/17-analytics-ux.md). '/' focuses the
  // cohort filter — the single most-used action. Extend with j/k, [ ], Esc, ?.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === '/' && !(e.target instanceof HTMLInputElement)) {
        e.preventDefault();
        document.querySelector<HTMLInputElement>('.shell__filter')?.focus();
      }
      if (e.key === 'Escape') {
        useUiStore.getState().selectCohort(null);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return <DashboardShell />;
}
