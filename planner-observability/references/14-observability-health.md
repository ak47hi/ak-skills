# Observability & health

Load when the prompt touches health, latency, drift, SLA, anomaly, alert, uptime, staleness, oscillation. This is the operational-monitoring lane: is the system healthy *right now*, and will the on-call find out before the user does.

Four subsystems to monitor — planner, forecast, allocation, pacing — each with its own health signals, plus cross-cutting anomaly detection and alert design.

## Health signals per subsystem

| Subsystem | First-class signals |
|---|---|
| **Planner** | Solve latency (p50/p95/p99), replan frequency, solve failures / timeouts, allocation success rate, constraint-violation count. |
| **Forecast** | Accuracy vs baseline, calibration / coverage trend (the drift leading indicator), staleness (age of the serving forecast), retrain success/failure, input feature drift (PSI/KS). |
| **Allocation** | Reservation success rate, reservation failures by reason, supply utilization, spillover rate, contention rate. |
| **Pacing** | Pace-rate stability (oscillation amplitude), under/over-delivery rate, smoothness, dual-variable convergence. |

## Latency: percentiles, never the mean

Show latency as **p50 / p95 / p99**, not the mean. A mean of 80 ms hides a p99 of 4 s that's timing out the planner on the tail. Plot the percentiles as separate lines with the SLA as a `markLine`; the gap between p50 and p99 is the tail-risk signal. Mean-only latency is an anti-pattern precisely because it launders the tail that causes incidents.

## SLA reference lines everywhere

Every health time-series carries its SLO as a `markLine` (and the error budget / burn region as a `markArea`). A latency chart without "the SLA is 500 ms" drawn on it forces the reader to remember the threshold — the reference line turns "the number is 480" into the instant judgment "we're near the edge." This is what makes a time-series a *decision* surface rather than a data display.

## Anomaly detection, overlaid not siloed

Anomalies belong **on the primary chart they perturb**, not in a separate "anomaly tab." The reader looking at the delivery curve should see the anomalous window shaded (`markArea`) and the anomalous point flagged (`markPoint`) right there — context is the whole value. A siloed anomaly list divorced from the metric forces the reader to re-correlate "anomaly at 14:32" with "what was the metric doing at 14:32," which is exactly the work the overlay does for them.

Detection method scales with sophistication available: a static SLO threshold is the floor; seasonal/STL residual bounds catch deviations a flat threshold misses; the method matters less than putting the result *on the metric* with the **attribution** attached (which cohort, which input) — an anomaly with no attribution is an alarm with no address.

## Alert design — avoiding fatigue

Alerts are the part of observability that fails most often, by crying wolf. An on-call paged for every blip learns to ignore the page, and then misses the real one. Discipline:

- **Severity tiers.** Page only for SLO-threatening conditions; everything else is a ticket or a dashboard annotation. Not every anomaly is a page.
- **Alert on symptoms, not causes.** Page on "underdelivery p95 breaching SLO," not on "forecast coverage dropped" — the latter is a dashboard signal that *explains* the page, not a page itself. (Google SRE: alert on the user-visible symptom.)
- **Burn-rate / multi-window thresholds.** "p95 underdelivery > 2% for 10 consecutive minutes" or an SLO error-budget burn-rate alert, not "any single tick over threshold." Single-tick alerts are noise.
- **Dedup + grouping.** One incident across 50 cohorts is one page, not 50. Group by root-cause dimension.
- **Every alert links to its drill path.** The page deep-links into the root-cause surface (`13-planner-debugging.md`) at the right time range and filter. An alert that doesn't tell you where to look is half an alert.

See `99-citations.md` for the Google SRE alerting-on-SLO / burn-rate material.

## A health-overview panel

The Tier-2 system-health surface is a compact grid: one stat-with-sparkline per subsystem signal, colored by SLO status (with shape/label too — not color alone), each drilling into its detail. The on-call's first glance answers "which of the four subsystems is unhealthy" in under a second, then drills. This is the operational entry point that the executive-overview (`16`) links down into.

## Anti-patterns this reference exists to prevent

- Mean-only latency (hides the tail).
- Health chart with no SLA reference line (forces the reader to remember the threshold).
- Anomalies in a separate tab, divorced from the metric.
- Anomaly flagged with no attribution.
- Alert-on-every-blip; no severity tiers; no dedup; alerts that don't link to a drill path.
