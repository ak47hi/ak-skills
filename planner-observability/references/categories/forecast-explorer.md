# Category: forecast-explorer

**When it fires.** "Actual vs forecast", "forecast accuracy", "calibration", "error decomposition", "feature attribution", "is the forecast drifting". Tier 2 → 3.

**Decision it serves.** Analytics engineer / DS: did the forecast miss, is it bias or variance, where does it concentrate, which input drove it, and did it hurt delivery? Plus the leading-indicator question — is calibration drifting *before* it becomes an incident.

**Key panels + chart choices** (governed by `12-forecast-explainability.md`).
- **Actual vs forecast + calibrated band** — multi-line + uncertainty band + SLA `markLine` + **calibration note**.
- **Error decomposition** — signed bias bar (diverging), variance, and an error attribution heatmap (cohort × horizon).
- **Feature/driver contribution** — per-prediction attribution for the selected cohort/window.
- **Planner-impact overlay** — the forecast→pacing→delivery causal chain annotated on the delivery curve.
- **Calibration view** — PIT/reliability + per-cohort-tier coverage + coverage trend over time.

**Drill paths.** Band escape → error decomposition for that window → feature contribution → planner-impact (did this miss cause a delivery miss). Coverage-trend dip → drift detail.

**Recurring anti-patterns.** EX1 no band; EX2 band with no calibration note; EX4 single error number; marginal coverage shown as per-cohort (`12`).

**Anchor metrics.** Calibration/coverage (per tier), signed bias, error concentration, forecast staleness.
