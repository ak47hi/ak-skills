# Category: simulation-explorer

**When it fires.** "Simulated vs actual", "replay the incident", "what-if", "counterfactual", "scenario compare", "test a pacer before shipping". Side surface, off the live path.

**Decision it serves.** Analytics engineer / planner owner: does a proposed change actually win (before shipping), or what exactly happened (reconstructing an incident)? Reasoning about planner behavior without touching production.

**Key panels + chart choices** (governed by `15-simulation-replay.md`).
- **Sim-vs-actual overlay** — sim output vs production actual on shared axes, with the reproduction-tolerance band. **Shown first** — if the sim doesn't reproduce the actual, it's uncalibrated and untrustworthy (`15`, FA E4).
- **Replay scrubber** — a timeline playhead driving shared time-selection; every panel re-renders to "state at tick t."
- **Counterfactual compare** — fixed traffic + forecast, swapped pacer; two delivery curves side by side, with "what's held fixed" explicit.
- **Perturbation sweep** — forecast-error magnitude (0/5/10/20%) vs the metric, showing degradation.
- **Scenario compare** — candidate vs baseline across the grid on **both** forecast and planner metrics (two-table discipline).

**Drill paths.** Scenario-compare regression → replay the failing scenario → scrub to the divergence tick → the panel showing why.

**Recurring anti-patterns.** What-if that doesn't pin held-fixed inputs (compares change + traffic); sim-vs-actual omitted; replay re-rendering one panel not the whole state; happy-path-only / forecast-metrics-only scenario compare.

**Anchor metrics.** Sim reproduction error, counterfactual delta (planner regret, underdelivery, churn), robustness across the perturbation grid.
