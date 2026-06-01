import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { CohortRow } from '../data/mockAdapter';
import { useUiStore } from '../store';

// Virtualized cohort table — proves the high-cardinality path
// (references/18-react-architecture.md, anti-pattern IM2). The dataset is 20k
// rows; the DOM holds ~30. Selecting a row drives the shared selection state so
// every other panel (the forecast chart) follows — cross-filter / selection
// propagation (references/17-analytics-ux.md).
//
// Keyboard: ArrowUp/Down move selection, Enter confirms — the j/k spirit from
// references/17 mapped to arrows for the table.

export function CohortTable({ rows }: { rows: CohortRow[] }) {
  const parentRef = useRef<HTMLDivElement | null>(null);
  const selectedId = useUiStore((s) => s.selectedCohortId);
  const selectCohort = useUiStore((s) => s.selectCohort);

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 28,
    overscan: 12,
  });

  function move(delta: number) {
    const idx = rows.findIndex((r) => r.cohortId === selectedId);
    const next = Math.min(rows.length - 1, Math.max(0, (idx < 0 ? 0 : idx) + delta));
    const row = rows[next];
    if (row) {
      selectCohort(row.cohortId);
      rowVirtualizer.scrollToIndex(next, { align: 'auto' });
    }
  }

  return (
    <div>
      <div className="table__meta">
        {rows.length.toLocaleString()} cohorts · sorted by anomaly score · ↑/↓ to move
      </div>
      <div className="table__head" aria-hidden>
        <span>cohort</span>
        <span>delivery</span>
        <span>risk</span>
        <span>coverage</span>
        <span>anomaly</span>
      </div>
      <div
        ref={parentRef}
        className="table__scroll"
        tabIndex={0}
        role="listbox"
        aria-label="Cohorts, sorted by anomaly score"
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
          else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
        }}
      >
        <div style={{ height: rowVirtualizer.getTotalSize(), position: 'relative' }}>
          {rowVirtualizer.getVirtualItems().map((vi) => {
            const row = rows[vi.index];
            const selected = row.cohortId === selectedId;
            return (
              <div
                key={row.cohortId}
                role="option"
                aria-selected={selected}
                className={`table__row${selected ? ' table__row--selected' : ''}`}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${vi.start}px)`,
                  height: vi.size,
                }}
                onClick={() => selectCohort(row.cohortId)}
              >
                <span className="mono">{row.cohortId}</span>
                <span>{(row.deliveryPct * 100).toFixed(0)}%</span>
                <span>{(row.underdeliveryRisk * 100).toFixed(0)}%</span>
                <span>{(row.coverage * 100).toFixed(0)}%</span>
                {/* status uses color + a glyph, never color alone (AC1) */}
                <span className={anomalyClass(row.anomalyScore)}>
                  {anomalyGlyph(row.anomalyScore)} {row.anomalyScore.toFixed(2)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function anomalyClass(score: number): string {
  if (score >= 0.7) return 'anomaly anomaly--high';
  if (score >= 0.4) return 'anomaly anomaly--med';
  return 'anomaly anomaly--low';
}

// Glyph so the signal survives grayscale / colorblindness (references/94).
function anomalyGlyph(score: number): string {
  if (score >= 0.7) return '▲';
  if (score >= 0.4) return '◆';
  return '·';
}
