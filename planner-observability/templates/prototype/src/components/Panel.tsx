import type { ReactNode } from 'react';

// Panel owns loading / error / empty states so chart components stay pure
// (references/18-react-architecture.md). Pass the TanStack Query status in.

interface PanelProps {
  title: string;
  status?: 'pending' | 'error' | 'success';
  isEmpty?: boolean;
  emptyHint?: string;
  children: ReactNode;
}

export function Panel({ title, status = 'success', isEmpty, emptyHint, children }: PanelProps) {
  return (
    <section className="panel" aria-label={title}>
      <header className="panel__header">{title}</header>
      <div className="panel__body">
        {status === 'pending' && <div className="panel__state">Loading…</div>}
        {status === 'error' && (
          <div className="panel__state panel__state--error" role="alert">
            Failed to load.
          </div>
        )}
        {status === 'success' && isEmpty && (
          <div className="panel__state">{emptyHint ?? 'No data.'}</div>
        )}
        {status === 'success' && !isEmpty && children}
      </div>
    </section>
  );
}
