# Forecast explainability

Load when the prompt touches actual-vs-forecast, uncertainty, error decomposition, feature attribution, or calibration. This is the *viz* lane — how to surface forecast quality so a human can reason about it. The modeling lane (how to build the forecaster, what loss to train) is `forecast-allocation`.

The job: make a forecast miss **explainable** before it becomes a delivery incident. A forecast that's silently miscalibrating for three weeks is the canonical failure (see `forecast-allocation`'s drift cases); the dashboard's job is to make that visible in hours.

## The four panels

A forecast-explorer surface is built from four panels, in this order of importance.

### 1. Actual vs forecast, with a calibrated band

- Overlay actual (solid) and forecast (dashed) on a shared time axis, with the **uncertainty band** shaded (e.g. p10–p90).
- The commitment/SLA as a `markLine`.
- **The band must carry a calibration note.** "p10–p90 band, empirical coverage 0.87 over trailing 14d (target 0.80)" — without it the band is decoration that invites false confidence. An uncalibrated band is worse than no band: the planner hedges against a lie. If coverage isn't measured, the panel says so loudly rather than implying the band is trustworthy.
- Drill: click a window where actual escaped the band → the error-decomposition panel for that window.

### 2. Error decomposition: bias vs variance vs attribution

A single error number (RMSE, "we were 8% off") is not actionable. Decompose it:

- **Bias** — signed mean error over the window. Persistent positive bias = systematic over-forecast = the planner systematically over-reserves. Show as a signed bar per cohort tier / per horizon, around a zero line (diverging scale).
- **Variance** — spread of the error. High variance with low bias is a different fix (noisy inputs, needs wider hedge) than high bias with low variance (systematic, needs a model correction).
- **Attribution** — *where* the error concentrates: which cohort decile, which horizon, which regime, which time-of-day. A heatmap of error over cohort × horizon localizes it. The decision "retrain everything" vs "fix the long-tail cohorts" lives here.

### 3. Feature / driver contribution

For the selected cohort or window, why did the forecast move? Surface the per-prediction driver contributions (SHAP-style if the model provides them, or the lag/calendar/regime feature values that changed). The on-call question at 3am is "which input blew up," and a black-box forecast makes incident response impossible (this is `forecast-allocation` anti-pattern F2 — debuggability — rendered as a panel). If the model can't attribute, the panel shows the raw input features that changed most vs the prior forecast.

### 4. Planner-impact overlay

The point of this skill: a forecast miss only matters through the planner. Overlay, on the delivery curve, **how the forecast error propagated** — the forecast-proportional pacer over-paced here because the forecast was high, leading to early exhaustion and end-of-window underdelivery. Annotate the causal chain (forecast high → over-pace → exhaust → underdeliver) with `markArea` regions. This is the panel that connects "the forecast was 8% off" to "we missed the commitment," which is the only reason anyone cares about forecast error.

## Calibration as a first-class view

Because uncalibrated uncertainty is the silent killer, the forecast-explorer carries a dedicated calibration view:

- **PIT histogram / reliability diagram** — is the predicted distribution honest? A U-shaped PIT = overconfident (bands too narrow); a hump = underconfident.
- **Per-quantile coverage** — does the p90 band actually cover 90%? **Per-cohort-tier**, not just marginal — marginal coverage can be 90% while the high-stakes cohort tier sits at 70% (this is `forecast-allocation` anti-pattern D4). Show coverage as a bar per tier against the target line.
- **Coverage trend over time** — the leading indicator of drift. Coverage drifting from 0.90 toward 0.75 over two weeks is the signal that would have caught the silent-miscalibration incident.

## Anti-patterns this reference exists to prevent

- Forecast line with no band (false certainty).
- Band with no calibration note (false confidence — the band lies).
- Single error number with no bias/variance split (not actionable).
- Marginal coverage reported as if it were per-cohort (hides the dangerous tail).
- Forecast error shown without the planner-impact link (error that no one can connect to an outcome).
