# Success metrics

Load in Phase 5 (MEASURE). A dashboard is an instrument; state how you'd know it works. The metrics here measure *decision value*, not popularity — and the distinction is the point.

## The metrics that matter

| Metric | What it measures | How to read it |
|---|---|---|
| **Time-to-decision** | From "open the surface" to "know what to do." | The core metric. A pacing dashboard that takes 5 minutes to answer "are we on track" has failed regardless of how it looks. |
| **Time-to-root-cause** | From "an anomaly is flagged" to "we know why." | Measures the drill path. If the path from Tier 1 to root cause is long or broken, this metric exposes it. |
| **Anomaly-detection rate** | Fraction of real incidents the surface surfaced (vs found by a user complaint). | The leading indicator of whether monitoring works. Misses here are the silent-failure stories. |
| **Detection lead time** | How long *before* impact the surface flagged the risk. | Catching forecasted underdelivery 6 hours out beats confirming actual underdelivery after the fact. |
| **Mis-triage reduction** | Fewer wrong root-cause conclusions / wrong pages. | Measures explainability — a surface that points the on-call at the wrong cause is worse than none. |

## Vanity metrics — the ban

Do **not** measure the dashboard by page views, session length, click counts, or "engagement." A dashboard that's viewed a lot might be viewed a lot *because it's hard to read*. Session length going up is as likely to mean "the on-call is confused" as "the on-call is engaged." These metrics measure the dashboard's popularity, not whether it accelerates a correct decision — and optimizing them actively harms the design (engagement-maximizing dashboards add sticky decoration, not signal).

The honest measurement is decision-outcome-based: did the right person reach the right conclusion faster, and did fewer incidents go undetected. When those can't be measured directly, proxy them with structured exercises (below), not with traffic.

## How to measure when you can't instrument outcomes directly

- **Timed task studies.** Give the target persona real questions ("which cohort is driving the underdelivery, and why") and time them to a correct answer, against the current surface as baseline. Small-n is fine; the effect sizes are usually large.
- **Incident retro coverage.** For each past incident, ask "would this surface have flagged it, and led to the right cause?" A surface that whiffs on the last quarter's incidents isn't ready.
- **Drill-path click count.** Instrument the path length from anomaly to root cause; ≤3 clicks (`17-analytics-ux.md`) is the target. This one *is* a usage metric, but it measures friction, not popularity.

## How this feeds OUTPUT

The design doc's "success metrics" section names the two or three that fit the persona (time-to-root-cause for an SRE surface; detection lead time for monitoring; time-to-decision for exec), states the current baseline if known, and the target. A design with no success metric is a design no one can later prove worked — and the next person rebuilds it on taste.
