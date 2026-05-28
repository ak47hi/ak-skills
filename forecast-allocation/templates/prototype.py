"""
forecast-allocation prototype skeleton.

Runs unmodified with stdlib + numpy + scipy. Three swappable interfaces
(Forecaster, Planner, TrafficSource) plus a Simulator event loop and a
run.py-style __main__ that prints the two-table report.

Replace each stub with a real implementation as the design demands; the
TODO markers point at the matching reference.

Dependencies:
    numpy >= 1.24
    scipy >= 1.10
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
from scipy.optimize import linprog


# ---------------------------------------------------------------------------
# Forecaster
# ---------------------------------------------------------------------------

class Forecaster(Protocol):
    """Produces per-cohort, per-horizon forecasts. See references/10-forecast.md."""

    def fit(self, history: np.ndarray, features: np.ndarray | None = None) -> None: ...

    def predict(self, t: int, horizon: int) -> np.ndarray: ...

    def predict_quantiles(
        self, t: int, horizon: int, quantiles: list[float]
    ) -> np.ndarray: ...


class SeasonalNaiveForecaster:
    """
    Trivial baseline forecaster: predicts y_{t+h} = y_{t+h-period} per cohort.

    Quantile predictions come from the residual distribution observed on the
    in-sample seasonal-naive predictions — sufficient to demo the pipeline.
    Replace with a real model (GBDT / TFT / DeepAR) per references/10-forecast.md.
    """

    def __init__(self, period: int = 24):
        self.period = period
        self._history: np.ndarray | None = None
        self._residual_quantiles: dict[float, float] = {}

    def fit(self, history: np.ndarray, features: np.ndarray | None = None) -> None:
        # history shape: (n_ticks, n_cohorts)
        self._history = history.astype(float)
        if history.shape[0] > self.period:
            in_sample_pred = history[: -self.period]
            in_sample_true = history[self.period :]
            residuals = (in_sample_true - in_sample_pred).reshape(-1)
            # Cache empirical residual quantiles; conformal-ish.
            for q in (0.1, 0.25, 0.5, 0.75, 0.9):
                self._residual_quantiles[q] = float(np.quantile(residuals, q))

    def predict(self, t: int, horizon: int) -> np.ndarray:
        assert self._history is not None, "fit() first"
        n_ticks, n_cohorts = self._history.shape
        out = np.zeros((horizon, n_cohorts))
        for h in range(horizon):
            ref_idx = (t + h - self.period) % n_ticks
            out[h] = self._history[ref_idx]
        return out

    def predict_quantiles(
        self, t: int, horizon: int, quantiles: list[float]
    ) -> np.ndarray:
        point = self.predict(t, horizon)
        # shape: (n_quantiles, horizon, n_cohorts)
        out = np.zeros((len(quantiles), *point.shape))
        for qi, q in enumerate(quantiles):
            shift = self._residual_quantiles.get(q, 0.0)
            out[qi] = np.maximum(0.0, point + shift)
        return out


# TODO(forecast): swap SeasonalNaiveForecaster for a global GBDT with cohort
# features + lag features + calendar features. See references/10-forecast.md.
# TODO(cohort): if cohort cardinality is combinatorial, factorize the forecast
# into per-(market, locale, device, placement, time) buckets and aggregate to
# cohort supply at query time. See references/12-cohort.md.
# TODO(uncertainty): wire in conformal prediction or quantile GBDT for properly
# calibrated intervals. See references/14-uncertainty.md.


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class Planner(Protocol):
    """Allocates supply forecast to commitments. See references/13-allocation.md."""

    def allocate(
        self,
        forecast: np.ndarray,
        demand: np.ndarray,
        constraints: dict,
    ) -> np.ndarray: ...


@dataclass
class ProportionalPacer:
    """
    Forecast-proportional pacer: per-tick spend ∝ forecast share of remaining supply.

    Strong baseline; oscillates under noisy forecasts (no replan-churn control).
    Replace with dual-decomposed online pacer for production use.
    """

    def allocate(
        self,
        forecast: np.ndarray,         # (horizon, n_cohorts)
        demand: np.ndarray,           # (n_commitments,) cumulative target
        constraints: dict,            # eligibility: (n_commitments, n_cohorts) {0,1}
    ) -> np.ndarray:
        eligibility = constraints.get("eligibility")
        assert eligibility is not None, "eligibility matrix required"
        horizon, n_cohorts = forecast.shape
        n_commitments = demand.shape[0]
        alpha = np.zeros((horizon, n_commitments, n_cohorts))

        remaining = demand.copy()
        for h in range(horizon):
            for i in range(n_commitments):
                if remaining[i] <= 0:
                    continue
                eligible_supply = (eligibility[i] * forecast[h]).sum()
                if eligible_supply <= 0:
                    continue
                future_eligible = (
                    eligibility[i] * forecast[h:].sum(axis=0)
                ).sum()
                if future_eligible <= 0:
                    rate = 1.0
                else:
                    rate = float(eligible_supply / future_eligible)
                spend_h = remaining[i] * rate
                eligible_in_h = eligibility[i] * forecast[h]
                if eligible_supply > 0:
                    alpha[h, i] = spend_h * (eligible_in_h / eligible_supply)
                remaining[i] -= spend_h
        return alpha


@dataclass
class LPPacer:
    """
    Single-shot LP pacer over the full horizon. Solves once at t=0, uses solution
    as the allocation plan. Per-tick reallocation would warm-start from this.

    For commitment i over cohort c over tick t:
        minimize  Σ_i u_i                  (under-delivery slack)
        s.t.      Σ_{t, c eligible} α_{t,i,c} + u_i ≥ D_i
                  Σ_i α_{t,i,c} ≤ forecast[t, c]
                  α ≥ 0, u ≥ 0

    Uses scipy.optimize.linprog (HiGHS). Suitable for small/medium problems.
    """

    def allocate(
        self,
        forecast: np.ndarray,
        demand: np.ndarray,
        constraints: dict,
    ) -> np.ndarray:
        eligibility = constraints["eligibility"]
        horizon, n_cohorts = forecast.shape
        n_commitments = demand.shape[0]

        n_alpha = horizon * n_commitments * n_cohorts
        n_u = n_commitments
        n_vars = n_alpha + n_u

        # Objective: minimize Σ u_i
        c = np.zeros(n_vars)
        c[n_alpha:] = 1.0

        def alpha_idx(t: int, i: int, k: int) -> int:
            return t * n_commitments * n_cohorts + i * n_cohorts + k

        def u_idx(i: int) -> int:
            return n_alpha + i

        # Capacity per tick × cohort: Σ_i α_{t,i,k} ≤ forecast[t,k]
        A_ub_rows = []
        b_ub = []
        for t in range(horizon):
            for k in range(n_cohorts):
                row = np.zeros(n_vars)
                for i in range(n_commitments):
                    row[alpha_idx(t, i, k)] = 1.0
                A_ub_rows.append(row)
                b_ub.append(forecast[t, k])

        # Eligibility: α_{t,i,k} = 0 if eligibility[i,k] == 0 (handled via upper bound)
        bounds = [(0.0, None)] * n_vars
        for t in range(horizon):
            for i in range(n_commitments):
                for k in range(n_cohorts):
                    if eligibility[i, k] == 0:
                        bounds[alpha_idx(t, i, k)] = (0.0, 0.0)

        # Delivery: Σ α_{t,i,k} + u_i ≥ D_i  =>  -Σα - u ≤ -D
        A_ub_deliv = []
        b_ub_deliv = []
        for i in range(n_commitments):
            row = np.zeros(n_vars)
            for t in range(horizon):
                for k in range(n_cohorts):
                    row[alpha_idx(t, i, k)] = -1.0
            row[u_idx(i)] = -1.0
            A_ub_deliv.append(row)
            b_ub_deliv.append(-float(demand[i]))

        A_ub = np.vstack(A_ub_rows + A_ub_deliv)
        b_ub_full = np.array(b_ub + b_ub_deliv)

        res = linprog(c, A_ub=A_ub, b_ub=b_ub_full, bounds=bounds, method="highs")
        if not res.success:
            # Fallback: zero allocation. The simulator will record underdelivery.
            return np.zeros((horizon, n_commitments, n_cohorts))

        alpha = res.x[:n_alpha].reshape((horizon, n_commitments, n_cohorts))
        return alpha


# TODO(planner): replace ProportionalPacer with the dual-decomposed online pacer
# from references/11-pacing.md for production-scale multi-commitment problems.
# TODO(planner): for LPPacer, add a replan loop with warm-start + trust-region
# control to manage replan churn. See references/13-allocation.md.


# ---------------------------------------------------------------------------
# Traffic source
# ---------------------------------------------------------------------------

class TrafficSource(Protocol):
    """Realized per-tick supply per cohort. See references/15-simulation.md."""

    def realize(self, t: int) -> np.ndarray: ...

    def reveal_truth(self) -> np.ndarray: ...


@dataclass
class SyntheticTrafficSource:
    """
    Calendar-driven Poisson-ish synthetic traffic. Replace with a replay source
    backed by historical logs for production-credible eval.
    """

    n_ticks: int
    n_cohorts: int
    period: int = 24
    seed: int = 0
    _truth: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        rng = np.random.default_rng(self.seed)
        # base rate per cohort
        base = rng.uniform(50, 200, size=self.n_cohorts)
        # daily seasonality
        hours = np.arange(self.n_ticks) % self.period
        season = 1.0 + 0.5 * np.sin(2 * np.pi * hours / self.period - np.pi / 2)
        # outer product + Poisson noise
        mean = season[:, None] * base[None, :]
        self._truth = rng.poisson(mean).astype(float)

    def realize(self, t: int) -> np.ndarray:
        return self._truth[t]

    def reveal_truth(self) -> np.ndarray:
        return self._truth


# TODO(simulation): swap SyntheticTrafficSource for a replay source over real
# historical traffic to validate against production baselines. See
# references/15-simulation.md.


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    underdelivery_pct: np.ndarray            # per commitment
    smoothness: float
    replan_churn: float
    forecast_rmse: float
    forecast_bias: float

    def report(self) -> str:
        lines = [
            "=" * 60,
            "Simulation report",
            "=" * 60,
            "",
            "Forecast metrics (Table 1)",
            f"  RMSE                   : {self.forecast_rmse:.3f}",
            f"  Bias                   : {self.forecast_bias:+.3f}",
            "",
            "Planner metrics (Table 2)",
            f"  Underdelivery % (mean) : {self.underdelivery_pct.mean() * 100:.2f}%",
            f"  Underdelivery % (p95)  : {np.quantile(self.underdelivery_pct, 0.95) * 100:.2f}%",
            f"  Smoothness (Σ Δα²)     : {self.smoothness:.2f}",
            f"  Replan churn           : {self.replan_churn:.2f}",
            "",
            "(Replace placeholder forecaster / planner per the TODO markers"
            " in the source for real results.)",
        ]
        return "\n".join(lines)


class Simulator:
    """
    Tick-by-tick event loop. At each tick:
        1. Forecaster predicts the supply over the remaining horizon.
        2. Planner re-allocates supply against commitments.
        3. Realized supply arrives; allocation is executed (clipped to realized).
        4. Metrics recorded.
    """

    def __init__(
        self,
        forecaster: Forecaster,
        planner: Planner,
        traffic_source: TrafficSource,
        n_ticks: int,
        n_cohorts: int,
        n_commitments: int,
        demand: np.ndarray,
        eligibility: np.ndarray,
        history: np.ndarray,
    ):
        self.forecaster = forecaster
        self.planner = planner
        self.traffic = traffic_source
        self.n_ticks = n_ticks
        self.n_cohorts = n_cohorts
        self.n_commitments = n_commitments
        self.demand = demand
        self.eligibility = eligibility
        self.history = history

    def run(self) -> SimulationResult:
        self.forecaster.fit(self.history)
        delivered = np.zeros(self.n_commitments)
        per_tick_alloc = []
        replan_total = 0.0
        last_plan = None
        forecasts_made = []
        truths_seen = []

        for t in range(self.n_ticks):
            horizon = self.n_ticks - t
            forecast = self.forecaster.predict(t, horizon)
            forecasts_made.append((t, forecast[0].copy()))
            plan = self.planner.allocate(
                forecast,
                self.demand - delivered,
                constraints={"eligibility": self.eligibility},
            )
            if last_plan is not None:
                # measure replan churn as L1 distance between successive plans on the
                # overlap of the planning horizons
                overlap_h = min(plan.shape[0], last_plan.shape[0] - 1)
                if overlap_h > 0:
                    diff = np.abs(plan[:overlap_h] - last_plan[1 : overlap_h + 1]).sum()
                    replan_total += float(diff)
            last_plan = plan

            realized = self.traffic.realize(t)
            truths_seen.append(realized.copy())
            # First-tick allocation is what actually executes.
            alloc_now = plan[0]                      # (n_commitments, n_cohorts)
            # Clip by realized supply per cohort (Σ_i alloc ≤ realized).
            total_per_cohort = alloc_now.sum(axis=0)
            scale = np.where(
                total_per_cohort > 0,
                np.minimum(1.0, realized / np.maximum(total_per_cohort, 1e-9)),
                0.0,
            )
            alloc_executed = alloc_now * scale[None, :]
            delivered += alloc_executed.sum(axis=1)
            per_tick_alloc.append(alloc_executed.sum(axis=1))

        per_tick_alloc = np.array(per_tick_alloc)         # (n_ticks, n_commitments)

        # Metrics
        underdelivery_pct = np.maximum(0.0, 1.0 - delivered / np.maximum(self.demand, 1e-9))
        smoothness = float((np.diff(per_tick_alloc, axis=0) ** 2).sum())

        # Forecast metrics on the first-tick forecasts vs the corresponding truth.
        f_arr = np.array([f for _, f in forecasts_made])
        t_arr = np.array(truths_seen)
        forecast_rmse = float(np.sqrt(np.mean((f_arr - t_arr) ** 2)))
        forecast_bias = float(np.mean(f_arr - t_arr))

        return SimulationResult(
            underdelivery_pct=underdelivery_pct,
            smoothness=smoothness,
            replan_churn=replan_total / max(self.n_ticks - 1, 1),
            forecast_rmse=forecast_rmse,
            forecast_bias=forecast_bias,
        )


# TODO(simulation): add a perturbation grid runner that injects forecast noise at
# configurable magnitudes (0%, 5%, 10%, 20%) and reports planner metrics across
# the grid. See references/15-simulation.md.
# TODO(simulation): add an oracle planner baseline (uses revealed truth as the
# forecast) to compute planner regret. See references/91-eval-metrics.md.


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(42)
    n_ticks = 48           # 2 days of hourly ticks
    n_cohorts = 8
    n_commitments = 4

    # Construct synthetic history (1 prior day) + traffic source for next 2 days
    traffic = SyntheticTrafficSource(
        n_ticks=n_ticks + 24, n_cohorts=n_cohorts, period=24, seed=0
    )
    history = traffic._truth[:24]
    # Slice traffic to the simulation window only:
    sim_traffic = SyntheticTrafficSource(n_ticks=n_ticks, n_cohorts=n_cohorts, period=24, seed=1)

    # Eligibility: each commitment is eligible for a random ~half of cohorts.
    eligibility = (rng.random((n_commitments, n_cohorts)) > 0.5).astype(float)
    eligibility[eligibility.sum(axis=1) == 0, 0] = 1.0  # ensure every commitment can serve somewhere

    # Demand: per-commitment total = some fraction of the eligible total supply
    total_supply = sim_traffic.reveal_truth().sum(axis=0)
    demand = (eligibility * total_supply).sum(axis=1) * 0.4

    forecaster = SeasonalNaiveForecaster(period=24)
    planner = ProportionalPacer()

    sim = Simulator(
        forecaster=forecaster,
        planner=planner,
        traffic_source=sim_traffic,
        n_ticks=n_ticks,
        n_cohorts=n_cohorts,
        n_commitments=n_commitments,
        demand=demand,
        eligibility=eligibility,
        history=history,
    )
    result = sim.run()
    print(result.report())


if __name__ == "__main__":
    main()
