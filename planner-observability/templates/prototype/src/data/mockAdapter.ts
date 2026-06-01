// Deterministic mock data adapter. The prototype runs with NO backend: every
// hook in src/queries.ts resolves against these functions. Determinism (a seeded
// PRNG) means the app renders the same thing every run — reproducible for demos
// and for the eval harness.
//
// Replace these functions with real API calls when wiring to a backend; the
// query hooks and components don't change (references/18-react-architecture.md).

// --- seeded PRNG (mulberry32) — deterministic, dependency-free ----------------
function mulberry32(seed: number): () => number {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export const HORIZON_TICKS = 48; // 48 hourly ticks

export interface ForecastPoint {
  tick: number;
  actual: number; // observed supply (null after "now")
  forecast: number; // median forecast
  lower: number; // p10
  upper: number; // p90
}

export interface ForecastSeries {
  cohortId: string;
  points: ForecastPoint[];
  commitment: number; // SLA / commitment level drawn as a reference line
  // Calibration metadata — the band is meaningless without it
  // (references/12-forecast-explainability.md).
  coverage: number; // empirical coverage of the p10-p90 band, trailing window
  targetCoverage: number; // nominal (0.80 for p10-p90)
}

export interface CohortRow {
  cohortId: string;
  market: string;
  device: string;
  deliveryPct: number; // delivered / commitment
  underdeliveryRisk: number; // forecasted risk, 0-1
  coverage: number; // forecast band coverage for this cohort
  anomalyScore: number; // 0-1; drives the heatmap / sort
}

const MARKETS = ['US', 'CA', 'UK', 'DE', 'FR', 'JP', 'BR', 'IN'];
const DEVICES = ['mobile', 'desktop', 'ctv', 'tablet'];

// "now" — actual is observed up to here, forecast extends beyond.
export const NOW_TICK = 32;

function seasonal(tick: number): number {
  // diurnal shape so the lines look like real traffic
  return 1 + 0.4 * Math.sin((tick / HORIZON_TICKS) * Math.PI * 2 - Math.PI / 2);
}

export function getForecastSeries(cohortId: string): ForecastSeries {
  const rnd = mulberry32(hashString(cohortId) ^ 0x9e3779b9);
  const base = 800 + rnd() * 1200;
  const points: ForecastPoint[] = [];
  for (let tick = 0; tick < HORIZON_TICKS; tick++) {
    const s = seasonal(tick);
    const trueVal = base * s;
    const noise = (rnd() - 0.5) * base * 0.12;
    const forecast = trueVal * (1 + (rnd() - 0.5) * 0.08);
    const spread = base * (0.1 + 0.15 * (tick / HORIZON_TICKS)); // widens with horizon
    points.push({
      tick,
      actual: tick <= NOW_TICK ? Math.max(0, trueVal + noise) : NaN,
      forecast,
      lower: forecast - spread,
      upper: forecast + spread,
    });
  }
  return {
    cohortId,
    points,
    commitment: base * 0.9,
    coverage: 0.72 + rnd() * 0.2, // some cohorts under-cover — the drift signal
    targetCoverage: 0.8,
  };
}

export function getCohorts(count = 20_000): CohortRow[] {
  // High-cardinality on purpose — proves the virtualization path
  // (references/18-react-architecture.md). In a real app this is a server-side
  // aggregated, paginated query past ~100k rows.
  const rows: CohortRow[] = [];
  for (let i = 0; i < count; i++) {
    const rnd = mulberry32(i ^ 0x85ebca6b);
    const market = MARKETS[i % MARKETS.length];
    const device = DEVICES[(i >> 3) % DEVICES.length];
    const cohortId = `${market}-${device}-${String(i).padStart(5, '0')}`;
    const deliveryPct = 0.6 + rnd() * 0.5;
    rows.push({
      cohortId,
      market,
      device,
      deliveryPct,
      underdeliveryRisk: Math.max(0, 1 - deliveryPct) * (0.5 + rnd()),
      coverage: 0.65 + rnd() * 0.25,
      anomalyScore: rnd() < 0.04 ? 0.7 + rnd() * 0.3 : rnd() * 0.4,
    });
  }
  return rows;
}

// Simulate network latency so loading states are exercised.
export function withLatency<T>(value: T, ms = 120): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}
