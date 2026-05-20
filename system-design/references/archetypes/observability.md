# Observability

Load when the prompt describes metrics/logs/traces platforms, SLO/SLI design, alerting, Prometheus/Grafana/OpenTelemetry stack, high-cardinality observability concerns, or "we can't see what's happening in prod."

The defining concern: **designing the observability system itself (cardinality control, retention tiering, sampling, alert design) — observability AS a system, not just adding metrics to a system.**

## When this archetype fires

Signal cues:
- "Metrics platform" / "logging platform" / "tracing platform"
- "SLO" / "SLI" / "error budget"
- "Alert design" / "alert fatigue" / "on-call paging"
- "Prometheus / Mimir / Cortex" / "Grafana" / "Loki" / "Tempo" / "OpenTelemetry"
- "High-cardinality" / "label explosion"
- "Distributed tracing" / "trace sampling"
- "We can't see what's happening in prod"

Non-signals:
- "We should add some metrics" to an existing service — that's instrumentation, not observability architecture. Use the universal foundation.
- A single dashboard request — operational, not architectural.
- General system monitoring (CPU, memory) — that's standard ops; this archetype is for designing the observability platform.

## Additional elicitation (beyond the universal seven)

1. **What's being instrumented.** App-level metrics? Infra metrics? Business metrics (revenue, conversion, signups)? Each has different cardinality, retention, and access patterns.
2. **Signal volume per service.** Metrics: how many active series per service? Logs: rate (lines/sec, bytes/sec) per service? Traces: requests/sec × sampling rate. Sum across the fleet.
3. **Retention per signal type.** Metrics: 30 days hot, 1 year warm? Logs: 14 days hot, 90 days warm, 7 years archived for compliance? Traces: 7–14 days typical. The retention spectrum drives cost.
4. **Cardinality budget.** Metrics with high-cardinality labels (user_id, request_id) blow up storage and query cost. What's the active-series limit per system? What labels are allowed?
5. **Sampling strategy** (traces, sometimes logs). 1% head sampling is common; tail-based (keep all traces for errored requests) is better but more complex.
6. **Query patterns.** Real-time dashboards (alert-driven, low-cardinality, recent data)? Ad-hoc investigation (high-cardinality drilldown, historical)? Both have different storage shapes.
7. **Alert design philosophy.** Page (wake-someone-up) vs ticket (notify-but-async) vs informational. What's the threshold for page vs ticket?
8. **Cost ceiling.** Observability platforms can cost more than the systems they observe. What's the budget? What signal types pay for themselves?
9. **Compliance retention requirements.** Audit logs may have legal minimums (years). Other signals don't. Tier accordingly.

## Recurring failure modes

### Cardinality explosion

**Symptom.** A metric has labels including `user_id` or `request_id`. The number of unique label combinations grows linearly with users / requests. Metric storage saturates; query cost explodes; the metric system itself becomes the slow service.

**Why it happens.** A developer added a high-cardinality label "for debugging." The cost compounds across millions of label combinations.

**Mitigation.** Cardinality budget per metric, enforced at instrumentation time. Labels are reviewed (which dimensions matter for aggregation? user_id rarely does for a fleet-wide metric). High-cardinality data goes to logs/traces (where cardinality is natural), not metrics.

### Log spam destroying retention

**Symptom.** Logs at INFO level produce 100GB/day. Retention budget allows 7 days at this rate. Real signal (errors, audit events) gets evicted with the noise.

**Why it happens.** "Log everything at INFO" without considering volume or value.

**Mitigation.** Log levels with discipline: ERROR/WARN are kept; INFO is sampled or per-service tunable; DEBUG is local-only. Separate audit logs (compliance retention) from app logs (operational).

### Alert fatigue

**Symptom.** Team gets 50 alerts/week, most of which are non-actionable. Engineers stop reading alerts. The one real alert that matters gets missed.

**Why it happens.** Alerts created for every metric that occasionally crosses a threshold. No discipline about "alert = action needed."

**Mitigation.** Every alert has a runbook describing the action. Alerts that fire and no action is taken get deleted or downgraded to informational. SLO-based alerting (alert on burn rate, not on every spike) reduces noise.

### Sampling that loses rare critical traces

**Symptom.** 1% trace sampling. A rare bug appears in 0.01% of requests. The traces of the buggy requests weren't sampled. Debugging is impossible.

**Why it happens.** Head-based sampling (decide at request start) doesn't know which traces will be interesting.

**Mitigation.** Tail-based sampling: hold all traces in memory; after the request completes, keep traces matching interesting criteria (errors, high latency, specific endpoint). Increases memory cost; decisively better quality.

### Observability of the observability platform

**Symptom.** The metrics system goes down. No one notices because the alerting system depends on the metrics system. The first symptom is users reporting the outage.

**Why it happens.** Self-referential dependency: observability platform watches everything except itself.

**Mitigation.** Out-of-band monitoring of the observability stack (external check, separate alerting path). The blast radius of an observability outage matters.

### Retention tier confusion

**Symptom.** Engineer queries 6-month-old logs for an incident analysis. Query returns nothing because logs were aged to cold storage; the query tool only reads hot. No error, just empty results.

**Why it happens.** Retention tiers exist but the query interface doesn't expose which tier holds what.

**Mitigation.** Unified query interface that reads across tiers (with appropriate latency expectations). Documented retention map.

### Sampled metric used in a math operation

**Symptom.** A counter is sampled at 1% to reduce volume. Someone graphs it as "events per minute" without multiplying by 100. The graph shows 1% of reality.

**Why it happens.** Sampling is invisible at query time.

**Mitigation.** Sampled metrics labeled (`_sampled` suffix, metadata). Query tools that surface sampling rate. Avoid sampling on counters where possible; sample on rare/expensive ones.

## What god-tier designers always ask

1. **What are the SLOs and the SLIs that measure them?** Without SLOs, alerting is guessing. SLIs are the metrics; SLOs are the thresholds; error budgets are derived.
2. **Cardinality budget per metric.** How many active series per service is acceptable?
3. **Retention tier per signal type.** Hot (queryable in seconds), warm (queryable in minutes), cold (compliance retention only, hours to retrieve).
4. **Sampling strategy.** Head-based for traces (cheap, loses rare events); tail-based (expensive, keeps rare events); per-signal-type sampling.
5. **Alert design.** Page (wake someone up) vs ticket (work-in-business-hours) vs informational. Every page must have a runbook.
6. **Cost per signal type.** Metrics, logs, traces have very different cost profiles. Audit cost monthly.
7. **What instruments the instrumenter?** Out-of-band monitoring of the observability stack.
8. **High-cardinality drilldown story.** When an alert fires, can the on-call engineer dig into a single request? If only aggregates are available, debugging is guessing.
9. **Per-team budgets.** As the org grows, observability cost becomes the platform's problem. Per-team budgets force discipline.

## Common pitfalls

### High-cardinality labels on metrics

The classic. `user_id` as a label on a request counter. Storage and query cost explode. Don't.

### Logging everything at INFO

Disk fills. Real signal gets evicted. Set INFO conservatively; use DEBUG locally.

### Alerts without runbooks

Alert fires. On-call engineer doesn't know what to do. Either the alert isn't real (delete it) or the runbook is missing (write it).

### Sampling without preserving rare events

Head-based sampling misses the rare bugs you most want to find.

### Treating observability as one signal type

Metrics, logs, and traces complement each other. Picking only one (e.g., "logs are enough") loses important dimensions: metrics for aggregates and alerts, traces for individual-request debugging, logs for detail.

### No tier discipline

All data in hot tier. Costs are 10× what they should be. Cold-tier retrieval is "we don't have it."

### Alerting on every threshold crossing instead of SLO burn rate

Per-metric thresholds fire frequently and irregularly. SLO burn rate alerting (alert when error budget is being consumed too fast) fires when something actionable is happening.

### Tracing without correlation IDs in logs

Logs and traces are stored separately. Without a shared correlation ID, you can find a slow trace but can't find its logs. Always: trace ID in every log line.

## Anchor numbers

These are rough order-of-magnitude figures.

- **Prometheus active series**: single-instance design limit around **10M active series**; beyond, switch to Mimir / Cortex / Thanos.
- **Logs**: a moderate platform produces **100GB–1TB/day** total; storage cost dominates beyond ~1TB/day.
- **Traces**: per-request trace size **10KB–100KB** depending on span count; with 5% head sampling and 10k req/sec, that's **~5–50 GB/day**.
- **Alert rate**: aim for **< 5–10 actionable alerts/week/team**. Higher means alert fatigue is forming.
- **Tracing sample rate**: **1–5%** head-based common; tail-based "keep all errored traces + 1% of healthy" works well at moderate cost.
- **Retention typical defaults**:
  - Metrics: 30 days hot, 1 year warm.
  - Logs: 14 days hot, 30 days warm, 1 year cold (longer for compliance).
  - Traces: 7–14 days hot, occasional longer for specific investigations.
- **Cost ratio**: observability commonly costs **5–15% of total infrastructure**; much above suggests over-provisioning or undisciplined cardinality.

## Cross-archetype interactions

- **Observability + every other archetype**: each archetype has its own metrics that matter (consumer lag for streaming, replication lag for geo-distributed, prediction distribution for ML inference, cache hit rate for read-heavy). Build per-archetype dashboards, not just generic CPU/memory.
- **Observability + multi-tenant**: tenant_id as a metric label is dangerous for cardinality. Aggregate to top-N tenants + everyone-else. Per-tenant detail in logs/traces where cardinality is natural.
- **Observability + hot-cold-tiered**: observability IS a hot-cold problem. Recent data is hot; historical is cold. Compliance retention is cold archive.
- **Observability + write-heavy**: observability is itself write-heavy (every metric scrape, every log line, every span is a write). The platform sizing follows write-heavy patterns.
