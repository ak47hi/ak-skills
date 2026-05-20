# Batch ETL

Load when the prompt describes scheduled, DAG-shaped data processing: nightly jobs, periodic warehouse loading, Airflow/Dagster/Prefect, "we run this every N hours," backfills, data quality checks.

The defining concern: **bounded-time, dependency-ordered processing of large datasets where idempotency, checkpointing, and lineage dominate the design.**

## When this archetype fires

Signal cues:
- "Nightly batch" / "scheduled job" / "every N hours"
- "Airflow" / "Dagster" / "Prefect" / "Argo Workflows" / "cron job"
- "ETL" / "ELT" / "data pipeline" / "warehouse loading"
- "DAG" / "dependency graph" / "upstream/downstream tasks"
- "Backfill" / "reprocess historical data"
- "Data warehouse" / "Snowflake" / "BigQuery" / "Redshift"
- "Spark job" / "dbt model" / "MapReduce"

Non-signals:
- A continuous event stream — that's `real-time-streaming`, even if the consumers run as long-lived jobs.
- A single ad-hoc analysis query — that's not a pipeline, that's a query.
- An async background job (email sending, image processing) — that's a queue, not ETL.

## Additional elicitation (beyond the universal seven)

1. **SLA per job.** When does this job have to finish by? "Before 9am for the morning dashboard" is a real SLA; "eventually" is not. SLA drives capacity planning and alert design.
2. **DAG shape and complexity.** How many tasks? How deep is the longest chain? How wide is the widest fan-out? Long chains amplify the impact of any single failure; wide fan-outs need resource coordination.
3. **Idempotency per task.** Can each task be safely re-run if a downstream task failed? "Insert the row" is non-idempotent; "upsert by primary key" or "delete-and-insert by partition" is.
4. **Data quality contract.** What checks gate each stage? Row count thresholds? Null-rate checks? Schema validation? Distribution checks? Are failures blocking (stop the pipeline) or alerting (continue, page someone)?
5. **Late-arriving data policy.** When data for day D arrives on day D+3, what happens? Reprocess D? Ignore? Add to D+3's partition?
6. **Backfill model.** Is backfilling the same code path as normal runs (good), or a separate one-off script (bad)? How are date ranges parameterized?
7. **Lineage / observability.** When the marketing dashboard is wrong, can you trace it back to which upstream tables/jobs are responsible? Without lineage, debugging is archaeology.
8. **Cost model.** Compute cost per run × runs per day matters at scale. A 1-hour Spark job on a big cluster, run daily, can dwarf the operational cost of the rest of the system.

## Recurring failure modes

### All-or-nothing job (no incremental checkpoint)

**Symptom.** A 4-hour job fails at hour 3. The retry runs from minute 0. Failures cascade through the day's pipeline.

**Why it happens.** Job logic processes the full dataset in a single transaction. No intermediate state is persisted.

**Mitigation.** Process in partitions (by date, by key range, by chunk). Checkpoint progress per partition. On retry, skip completed partitions. Spark and Beam do this naturally; custom jobs often don't.

### Cascade failure across the DAG

**Symptom.** One upstream task fails. Twenty downstream tasks fail because their inputs aren't there. The on-call engineer is paged twenty times for the same root cause.

**Why it happens.** No grouped alerting. The DAG framework reports each failure independently.

**Mitigation.** Alert at the SLA boundary, not the per-task level. "Marketing dashboard didn't update by 9am" is one alert; the specific failing upstream is found by investigation. Pause downstreams when an upstream fails (most DAG frameworks do this; verify yours does).

### Data quality issue caught downstream, not at source

**Symptom.** Bad data enters the pipeline at ingest. It propagates through 12 transformations. The marketing team notices "the conversion rate dropped 80% overnight" — and it's a bad source feed, not a real product change.

**Why it happens.** No data quality gates at the source. Each stage assumes its input is correct.

**Mitigation.** Quality gates at every stage, especially the first one. Row count checks (expect ~N rows ± 20%), null-rate checks (expect < X% nulls), schema checks (expect these columns with these types), distribution checks (expect the value range to look like yesterday's). Fail the pipeline on egregious deviations; alert on moderate ones.

### Backfills colliding with current pipeline

**Symptom.** Someone runs a backfill for 2023-01 through 2023-06. The backfill writes to the same tables the current pipeline writes to. Concurrent writes cause race conditions or partial overwrites.

**Why it happens.** No partition-level isolation between backfill and current. No backfill convention.

**Mitigation.** Backfill writes to a staging partition; promotion is atomic (rename partition). Or: backfill writes to a separate table, then merge. Never let backfill mutate the same rows current runs are touching.

### Late data invalidating already-computed outputs

**Symptom.** Day D's aggregations are computed at D+1 morning. On D+3, data for D arrives. The downstream consumers have already cached D's aggregations.

**Why it happens.** Late data is a fact of life (network delays, batch sources, vendor exports); the pipeline didn't plan for it.

**Mitigation.** Define a "settled" cutoff (e.g., D + 3 days). Aggregations before the cutoff are provisional and recomputed when new data lands; after the cutoff, immutable.

### "It works on my dev cluster" — production scale failure

**Symptom.** The Spark job is fine on a 10GB sample. It OOMs on the 500GB production dataset. Skew, shuffle size, or memory tuning is wrong.

**Why it happens.** Dev environments don't replicate production scale. The expensive operations (shuffles, broadcasts, sorts) only fail at large data sizes.

**Mitigation.** Test against representative samples (a real day's data, not a synthetic toy). Plan capacity for skew (the 99th-percentile key, not the average). Monitor task-level skew in the Spark UI; redesign joins/aggregations when one task is 100× the others.

### Vendor dependency outage

**Symptom.** The pipeline depends on a daily file from a third party. The third party is down. The pipeline waits forever, then fails, then a 2am page.

**Why it happens.** Synchronous dependency on an external system without timeout, retry, or fallback.

**Mitigation.** Time out the external dependency. Retry with backoff. If still failing, use yesterday's data (with a clear "stale" indicator) or fail with a clear alert. Don't silently wait.

## What god-tier designers always ask

1. **What's the SLA, and what's the headroom?** A 1-hour job with a 2-hour SLA has 50% headroom — fine. A 6-hour job with a 7-hour SLA has 15% — one bad day and you miss SLA.
2. **What's the checkpoint strategy?** Per-partition? Per-task? End-of-job-only? Restart cost is checkpoint-frequency-dependent.
3. **What's idempotency look like for each writing task?** Upsert by PK? Partition-replace? Append + dedup downstream? "Insert" is rarely idempotent.
4. **How does backfill work — same code, same DAG, different parameters?** Or one-off scripts every time? The latter is unsustainable.
5. **Data quality gates — at which stages?** Source ingest is non-optional. Cross-stage gates are valuable. End-of-pipeline gates catch the dashboard breakage before users do.
6. **Late-arriving data: window or reprocess?** Define the "settled" cutoff and the policy explicitly.
7. **Lineage observability: can you trace dashboard wrongness back to source?** dbt, OpenLineage, Marquez, Atlas — pick one.
8. **What's the cost per run, and does it scale linearly with data?** A "free" pipeline at 10GB can be $thousands/month at 10TB.

## Common pitfalls

### Treating idempotency as optional

If a task isn't idempotent, retry is broken; backfill is broken; partial-failure recovery is broken. Idempotency is not an optimization — it's the basis for everything that comes after.

### Manual backfills via one-off scripts

Every backfill written as a script that imitates the pipeline's logic. Drifts from the real pipeline. Bugs in backfill scripts produce wrong historical data that's hard to detect. Backfill must use the same code as normal runs, parameterized by date range.

### No data quality gates between stages

The pipeline assumes its own outputs are correct because the code "worked." Bad inputs produce bad outputs silently. Even simple gates (row count, null rate, schema) catch a meaningful fraction of issues.

### DAGs with hundreds of tasks per pipeline

The DAG framework lets you express any graph. That doesn't mean you should. A pipeline with 500 tasks is unobservable, undebuggable, and likely has a few critical-path bottlenecks doing 90% of the work. Refactor to coarser stages.

### Pipeline-as-code without test coverage

Production pipelines transform business-critical data. They get edited as casually as any other code. A bug ships, the dashboard is wrong for two weeks before someone notices, the finance team's monthly close is delayed. Test data transformations like production code: unit tests on transform functions, integration tests on sample data, regression tests on known outputs.

### Ignoring schema evolution

The source data schema changes. The pipeline silently picks up the new column (or fails to). Downstream consumers either get the new field (and break, expecting old schema) or don't (and miss data). Define schema evolution rules; enforce them in CI.

### Shared state between tasks (anti-pattern)

Task B reads task A's output from a known file path; task A's output isn't versioned by run. Concurrent runs of the DAG (or a backfill running alongside) corrupt each other. Use run-scoped paths or atomic partition writes.

## Anchor numbers

- **Spark on a moderate cluster** (8–32 nodes): handles **TB-scale daily batches** in a few hours. Beyond ~10TB single-job, partition strategy starts dominating performance.
- **dbt on a cloud warehouse** (Snowflake, BigQuery): sub-TB transformations in minutes. Warehouse cost grows with compute time × cluster size.
- **Airflow DAG complexity**: keep under **~100–200 tasks per DAG** for sustainable operations. Beyond, split into sub-DAGs or refactor.
- **Job duration**: aim for individual tasks to complete in **5–30 minutes**. Shorter = framework overhead dominates; longer = retry cost grows.
- **Backfill duration**: a 1-year backfill of a daily pipeline (365 runs) at 30 minutes each = ~180 hours sequential. Plan for parallelization or accept the time cost.
- **Data quality false-positive tolerance**: gates that fire too often get muted. Aim for < 1 false positive per quality gate per month, or the gate is doing more harm than good.

## Cross-archetype interactions

- **Batch ETL + streaming**: a "lambda architecture" pattern where streaming gives low-latency approximate results and batch gives correct results. Increasingly replaced by "kappa" (streaming-only with replay) but lambda still exists.
- **Batch ETL + observability**: pipeline jobs themselves need monitoring (run duration, success rate, data quality gate firing rate, cost per run). The pipeline produces observability data; it also IS observability data.
- **Batch ETL + multi-tenant**: per-tenant aggregation jobs scale with tenant count. Watch for the "10,000 small batch jobs" anti-pattern; consolidate into per-tenant-partition jobs.
- **Batch ETL + hot-cold tiered**: pipelines often shuffle data across tiers (hot → cold for old data; cold → hot for retrieval). The pipeline IS the lifecycle mechanism.
