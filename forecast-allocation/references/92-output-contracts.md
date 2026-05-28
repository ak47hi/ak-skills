# Output contracts

Load during **Phase 6 (OUTPUT)**. Defines what each mode's artifact must contain, in order.

## DESIGN mode → `design-doc.md`

The deliverable when the user asks for a design. Sections must appear in order; an empty section is a deliberate "n/a" with one-line justification, not an omission.

### Required sections

1. **Problem framing.** One paragraph: what the system has to do, what it consumes, what it produces, where it sits operationally (between which producer and which planner-consumer).
2. **Constraints + assumptions.** The seven dimensions from `00-elicitation.md`. Every inferred value flagged as an assumption.
3. **Mathematical framing.** Formal objective(s), loss(es), constraints. Symbols defined. The math sets up the comparison that follows.
4. **Approach comparison.** ≥2 candidate approaches, each with: one-paragraph description, scalability behavior, sparsity behavior, planner-coupling behavior, ops cost. Comparable structure across candidates.
5. **Recommended approach.** Which candidate ships. The binding constraint that picked it. The sacrifice accepted.
6. **Scalability analysis.** Memory + compute at the cohort cardinality and event rate from ELICIT. Identifies the binding bottleneck. (Mirrors `system-design`'s SCALE phase.)
7. **Data requirements.** History depth, feature pipeline, label availability, retraining cadence.
8. **Failure modes.** Per dependency / per assumption: how does it fail? What's the blast radius? What's the degradation strategy? (Mirrors `system-design`'s FAILURE phase.)
9. **Evaluation plan.** Forecast metrics + planner metrics tables (per `91-eval-metrics.md`). Baselines named. Slices named.
10. **Simulation strategy.** Which sim strategy (`15-simulation.md`), perturbation grid, what's being measured.
11. **Open questions.** Inferred constraints to confirm. Deferred decisions with a trigger.

### Length

A design doc for a real production decision is usually 800-2000 lines. Narrower questions (one targeted decision) bypass this template entirely and emit a chat-mode answer; see `01-routing.md` Example 4.

### Walks anti-patterns

After emitting, walk `references/93-anti-patterns.md` against the design. Each pattern that fires is either fixed in the design or called out in **Open questions**.

## PROTOTYPE mode → `prototype.py` package

The deliverable when the user asks for code they can run.

### Required modules

`templates/prototype.py` contains a header docstring + three Python modules concatenated, or (preferred) a small package laid out as:

```
prototype/
├── forecaster.py
├── planner.py
├── simulator.py
└── run.py            # entry point
```

The emitted artifact MUST:

- **Run unmodified** with `python run.py`. No external deps beyond stdlib + numpy + scipy.
- **Print baseline metrics** (underdelivery %, smoothness, replan churn) when run.
- **Have swappable interfaces** so the user can replace `forecaster` or `planner` without touching the simulator.

### `forecaster.py` contract

```python
class Forecaster(Protocol):
    def fit(self, history: np.ndarray, features: np.ndarray | None = None) -> None: ...
    def predict(self, t: int, horizon: int) -> np.ndarray: ...
    def predict_quantiles(self, t: int, horizon: int, quantiles: list[float]) -> np.ndarray: ...
```

Ship one concrete implementation (`SeasonalNaiveForecaster` or similar trivial stub) so the package runs.

### `planner.py` contract

```python
class Planner(Protocol):
    def allocate(
        self,
        forecast: np.ndarray,
        demand: np.ndarray,
        constraints: dict,
    ) -> np.ndarray: ...   # per-tick allocation per commitment
```

Ship one concrete implementation (proportional pacer or `scipy.optimize.linprog`-based LP allocator).

### `simulator.py` contract

```python
class Simulator:
    def __init__(self, forecaster, planner, traffic_source, horizon, n_ticks): ...
    def run(self) -> SimulationResult: ...        # records forecast, allocation, realized, metrics per tick
```

Result includes per-tick logs and aggregate metrics (per `91-eval-metrics.md`).

### `run.py`

Wires defaults, runs one simulation, prints the two-table report.

### TODO markers

Each module ends with TODO markers pointing at the references:

```python
# TODO(forecast): replace stub with a GBDT (LightGBM) — see references/10-forecast.md
# TODO(uncertainty): wire in conformal intervals — see references/14-uncertainty.md
# TODO(planner): replace proportional pacer with dual-decomposed — see references/11-pacing.md
```

These are the user's next moves; the skeleton is intentionally not the final implementation.

## EVALUATE mode → `eval-plan.md`

The deliverable when the user asks how to evaluate or stress-test.

### Required sections

1. **Hypothesis.** What the eval is testing. Stated as a falsifiable claim ("Pacer A has lower replan churn than Pacer B under 10% forecast error at p95 of cohort-tier-1 deliveries").
2. **Baselines.** Production / even-pacing / oracle, plus any specified.
3. **Datasets / simulation harness.** Replay vs Monte Carlo vs synthetic vs counterfactual (per `15-simulation.md`). What's held fixed, what varies.
4. **Forecast metrics table.** Per `91-eval-metrics.md` Table 1. Slices named.
5. **Planner metrics table.** Per `91-eval-metrics.md` Table 2. Slices named.
6. **Ablation grid.** Components to ablate. Hyperparameter sensitivity.
7. **Perturbation grid.** Forecast error magnitudes, drift scenarios, traffic shocks.
8. **Statistical significance protocol.** Paired bootstrap / permutation / sample sizes / pre-registered hypotheses if applicable.
9. **Reporting format.** What gets emitted (heatmap, two tables, summary paragraph), where it lives, who reviews.
10. **Decision rule.** What outcome ships the change. What outcome reverts. Stated **before** running the eval.

### Length

200-600 lines depending on scope. An eval plan for a single pacer A/B is shorter than one for a new forecast family.

## Cross-cutting rules

- **No artifact without ELICIT having run** (inferred + flagged is fine).
- **Every significant choice in the artifact ties to a binding constraint and a sacrifice** (per `90-tradeoffs.md`).
- **Anti-pattern walk is part of OUTPUT, not a separate step.** Each pattern that fires is recorded in the artifact.
- **Match user depth.** A narrow question gets a narrow answer — do **not** emit a full design-doc template for "should I use quantile or RMSE here?"
- **Cite the reference.** Every section that summarizes a reference cites it ("per `11-pacing.md`") so a reader can chase the source.
