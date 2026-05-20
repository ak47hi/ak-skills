# Archetypes index

System-design problems cluster into recognizable shapes. A god-tier designer pattern-matches the prompt to one or more archetypes, brings the archetype-specific questions, then designs against the constraints.

This directory is the catalog. Each archetype file documents:

- **When this archetype fires** — signals in the prompt that route here.
- **Additional elicitation** — the archetype-specific questions to ask beyond the universal seven dimensions in `SKILL.md`'s Phase 1.
- **Recurring failure modes** — what tends to break in systems of this shape.
- **What god-tier designers always ask** — questions that catch common wrong defaults.
- **Common pitfalls** — archetype-specific anti-patterns (beyond `references/anti-patterns.md`).
- **Anchor numbers** — scale thresholds that help calibrate decisions.

## When to load an archetype

During **Phase 1 (ELICIT)** in any mode (greenfield / review / diagnose / evolve), after eliciting the universal constraints, check this index for signals. If one or more archetypes fire, load their files and run the archetype-specific elicitation.

If **no archetype fires**, the universal foundation in `SKILL.md` + the five core references handles it. Most systems are not exotic; don't force an archetype label.

If **multiple archetypes fire** (common — a system can be both multi-tenant AND geo-distributed AND read-heavy), load each. The skill walks each one's elicitation additions and integrates the answers. **Conflicts between archetypes are surfaced to the user**, not hidden — for example, "multi-tenant says isolate per tenant; geo-distributed says minimize cross-region writes; reconciling these constrains your tenant→region mapping."

## Routing table

| Signal cues in the prompt | Archetype |
|---|---|
| "B2B SaaS", "per-customer", "per-tenant", "our enterprise customers", "noisy neighbor", "isolation between accounts", "white-label", "per-customer SLA" | [multi-tenant-saas](multi-tenant-saas.md) |
| "stream processing", "real-time pipeline", "Kafka/Kinesis/Pulsar", "Flink/Spark Streaming", "events as they happen", "windowing", "watermarks", "exactly-once" | [real-time-streaming](real-time-streaming.md) |
| "nightly batch", "scheduled job", "DAG", "Airflow/Dagster/Prefect", "ETL", "data warehouse", "every N hours", "backfill" | [batch-etl](batch-etl.md) |
| "ML inference", "model serving", "feature store", "online prediction", "model versioning", "A/B test models", "feature serving", "real-time scoring" | [ml-inference](ml-inference.md) |
| "multi-region", "geo-distributed", "active-active", "active-passive", "RTO/RPO", "data residency", "GDPR locality", "regional failover" | [geo-distributed](geo-distributed.md) |
| "mobile app", "high read traffic", "feed", "global user base", "offline-first", "CDN", "edge caching", "cellular network constraints" | [read-heavy-mobile](read-heavy-mobile.md) |
| "high write throughput", "ingest pipeline", "telemetry firehose", "IoT events", "ad-tech impressions", "write QPS in the hundreds-of-thousands", "append-only" | [write-heavy](write-heavy.md) |
| "metrics", "logs", "traces", "observability platform", "SLO/SLI", "alerting", "Prometheus/Grafana/OpenTelemetry", "high-cardinality" | [observability](observability.md) |
| "data lifecycle", "archival", "cold storage", "hot tier", "S3 Glacier", "tiered retention", "GDPR delete", "rarely-accessed data" | [hot-cold-tiered](hot-cold-tiered.md) |

## Archetype list

| Archetype | One-line shape |
|---|---|
| [multi-tenant-saas](multi-tenant-saas.md) | Many customers share infrastructure; isolation, fairness, and per-tenant operations dominate the design. |
| [real-time-streaming](real-time-streaming.md) | Continuous event processing with windowing, watermarks, exactly-once processing, and backpressure. |
| [batch-etl](batch-etl.md) | Scheduled DAG-shaped pipelines with idempotency, checkpointing, late-arriving data, and lineage. |
| [ml-inference](ml-inference.md) | Online model serving with feature freshness, versioning, A/B routing, and tight latency budgets. |
| [geo-distributed](geo-distributed.md) | Multi-region deployment with RTO/RPO requirements, data residency, and active-passive vs active-active. |
| [read-heavy-mobile](read-heavy-mobile.md) | High-read workloads with caching layers, CDN, mobile constraints, and offline-first considerations. |
| [write-heavy](write-heavy.md) | High-write workloads (telemetry, IoT, ingest) with sharding, append-only patterns, deduplication. |
| [observability](observability.md) | Metrics/logs/traces with cardinality control, retention tiering, sampling, and alert design. |
| [hot-cold-tiered](hot-cold-tiered.md) | Data lifecycle with hot/warm/cold tiers, retrieval latency budgets, and compliance-driven deletion. |

## Anti-pattern: forcing an archetype that doesn't fit

The temptation is to label every system with an archetype because labels feel productive. Resist this. If the prompt is a generic CRUD app at modest scale, **no archetype fires** — the universal foundation handles it.

Signs you're forcing an archetype:

- You're loading an archetype file but skipping most of its elicitation questions as "not applicable."
- The archetype's failure modes don't match the user's concerns.
- The archetype's anchor numbers are several orders of magnitude away from the user's scale.

When this happens, drop the archetype and stay with the universal foundation.

## Anti-pattern: archetype as cookie-cutter design

Loading an archetype does **not** mean producing a canned design. The archetype brings questions and failure modes; the design still derives from the user's elicited constraints. Two multi-tenant SaaS systems with different scales, tenant size distributions, and operational realities will have different designs.

If the output looks like "the canonical multi-tenant SaaS architecture," something has gone wrong — that's pattern-matching the solution, not the problem.
