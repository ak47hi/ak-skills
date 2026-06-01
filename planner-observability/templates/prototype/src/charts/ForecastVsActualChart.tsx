import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { EChart } from './EChart';
import type { ForecastSeries } from '../data/mockAdapter';
import { NOW_TICK } from '../data/mockAdapter';

// The load-bearing panel (references/12-forecast-explainability.md):
// actual vs forecast with a CALIBRATED uncertainty band + an SLA markLine.
// The band is rendered as a transparent lower bound + a stacked translucent
// (upper - lower) area, the standard ECharts confidence-band idiom.
//
// The calibration note is NOT optional. A band with no coverage statement is
// anti-pattern EX2 — it lies with confidence. We surface coverage vs target
// in the subtext and color the note when coverage is below target.

export function ForecastVsActualChart({ series }: { series: ForecastSeries }) {
  const option = useMemo<EChartsOption>(() => {
    const ticks = series.points.map((p) => p.tick);
    const lower = series.points.map((p) => p.lower);
    const bandHeight = series.points.map((p) => p.upper - p.lower);
    const forecast = series.points.map((p) => p.forecast);
    const actual = series.points.map((p) => (Number.isNaN(p.actual) ? null : p.actual));

    const undercovered = series.coverage < series.targetCoverage;
    const coveragePct = (series.coverage * 100).toFixed(0);
    const targetPct = (series.targetCoverage * 100).toFixed(0);

    return {
      // Decision-oriented title + the mandatory calibration note as subtext.
      title: {
        text: `Forecast vs actual — ${series.cohortId}`,
        subtext:
          `p10–p90 band · empirical coverage ${coveragePct}% (target ${targetPct}%)` +
          (undercovered ? ' — UNDER-COVERED, band too narrow' : ' — calibrated'),
        subtextStyle: { color: undercovered ? '#d1495b' : '#3f7d4e', fontWeight: 600 },
        left: 8,
        top: 4,
        textStyle: { fontSize: 14 },
      },
      grid: { left: 56, right: 16, top: 64, bottom: 56 },
      tooltip: { trigger: 'axis' },
      legend: { data: ['actual', 'forecast'], top: 4, right: 8 },
      xAxis: {
        type: 'category',
        data: ticks,
        name: 'tick (hour)',
        nameLocation: 'middle',
        nameGap: 28,
      },
      yAxis: { type: 'value', name: 'supply', scale: true },
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 28 }],
      series: [
        // --- uncertainty band (lower transparent + stacked translucent height)
        {
          name: 'p10',
          type: 'line',
          data: lower,
          stack: 'band',
          lineStyle: { opacity: 0 },
          symbol: 'none',
          silent: true,
          z: 1,
        },
        {
          name: 'band',
          type: 'line',
          data: bandHeight,
          stack: 'band',
          lineStyle: { opacity: 0 },
          areaStyle: { color: 'rgba(70, 130, 180, 0.18)' },
          symbol: 'none',
          silent: true,
          z: 1,
        },
        // --- forecast median
        {
          name: 'forecast',
          type: 'line',
          data: forecast,
          showSymbol: false,
          lineStyle: { type: 'dashed', width: 2, color: '#4682b4' },
          z: 3,
          // SLA / commitment reference line + the "now" divider as event markers
          // (references/14-observability-health.md OB2/OB5).
          markLine: {
            symbol: 'none',
            data: [
              {
                yAxis: series.commitment,
                name: 'commitment',
                label: { formatter: 'commitment', position: 'insideEndTop' },
                lineStyle: { color: '#d1495b', type: 'solid' },
              },
              {
                xAxis: NOW_TICK,
                name: 'now',
                label: { formatter: 'now', position: 'insideEndBottom' },
                lineStyle: { color: '#888', type: 'dotted' },
              },
            ],
          },
        },
        // --- observed actual (solid, stops at "now")
        {
          name: 'actual',
          type: 'line',
          data: actual,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 2, color: '#222' },
          z: 4,
        },
      ],
    };
  }, [series]);

  return (
    <EChart
      option={option}
      height={320}
      ariaLabel={
        `Forecast versus actual supply for cohort ${series.cohortId}. ` +
        `Band coverage ${(series.coverage * 100).toFixed(0)} percent against a ` +
        `target of ${(series.targetCoverage * 100).toFixed(0)} percent.`
      }
    />
  );
}
