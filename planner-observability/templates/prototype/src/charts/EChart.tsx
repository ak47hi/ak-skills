import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

// Thin ECharts wrapper (the "useRef + setOption effect" form from
// references/18-react-architecture.md). Keeps chart components as pure
// data -> EChartsOption functions; this handles instance lifecycle, incremental
// updates, resize, and disposal.

interface EChartProps {
  option: echarts.EChartsOption;
  height?: number;
  // Accessibility: a text summary of the chart's takeaway for screen readers
  // (references/94-accessibility.md). ECharts also emits its own aria, but an
  // explicit, decision-oriented label is better.
  ariaLabel: string;
  onEvents?: Record<string, (params: unknown) => void>;
}

export function EChart({ option, height = 280, ariaLabel, onEvents }: EChartProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  // Create / dispose the instance.
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: 'canvas' });
    chartRef.current = chart;
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  // Incremental update — notMerge:false so live refreshes are smooth, not full
  // rebuilds (references/18-react-architecture.md).
  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: false });
  }, [option]);

  // Bind events (e.g. click-to-drill).
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !onEvents) return;
    for (const [evt, handler] of Object.entries(onEvents)) {
      chart.on(evt, handler as (p: unknown) => void);
    }
    return () => {
      for (const evt of Object.keys(onEvents)) chart.off(evt);
    };
  }, [onEvents]);

  return (
    <div
      ref={ref}
      role="img"
      aria-label={ariaLabel}
      style={{ width: '100%', height }}
    />
  );
}
