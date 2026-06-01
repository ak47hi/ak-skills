# Category: root-cause-analysis

**When it fires.** "Drill to root cause", "anomaly triage", "why did X happen", "incident investigation". Tier 3 — the terminal tier. Less a separate dashboard than the *spine* every anomaly drills into.

**Decision it serves.** Planner SRE mid-incident: from "a metric is red" to "here is the specific cause and the fix." The whole skill's drill paths converge here.

**Key panels + chart choices.** Assembled from the other categories along a path, not invented fresh:
- The **anomaly** in context — overlaid on the metric it perturbed (`14` OB3), with attribution (`14` EX3).
- The **localization** — cohort × time heatmap (cohort-explorer) narrowing to the affected segment.
- The **mechanism** — delivery curve + pacing trace (delivery-explorer) showing how it failed.
- The **planner decision** — allocation diff + trigger (planner-explorer) showing what changed.
- The **input** — forecast error decomposition + feature contribution (forecast-explorer) showing why.
- A **breadcrumb** of the path so the reader can step back up (`17`).

**The drill spine.** Standardize the path so every incident follows it:
```
overview anomaly → cohort heatmap (where) → delivery+pacing (how) →
allocation diff (what the planner did) → forecast/feature attribution (why) → cause
```
The design obligation: every anomaly the system can raise must have a route onto this spine. An anomaly with no drill route is a dead-end alert (SD4 / OB3).

**Recurring anti-patterns.** SD4 dead-end overview; OB3 anomalies siloed from metrics; EX3 anomaly with no attribution; IN4 modal drill that loses context; drill path > ~3 clicks (`17`).

**Anchor metrics.** Time-to-root-cause, mis-triage rate, drill-path length (`91`).
