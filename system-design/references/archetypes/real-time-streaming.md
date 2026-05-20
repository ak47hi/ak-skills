# Real-time streaming

Load when the prompt describes continuous event processing: Kafka/Kinesis/Pulsar consumers, Flink/Spark Streaming/Beam pipelines, "events as they happen," windowing, watermarks, sub-minute processing latency.

The defining concern: **stateful processing of unbounded event streams with ordering, late arrival, and exactly-once-processing constraints.**

## When this archetype fires

Signal cues:
- "Stream processing" / "real-time pipeline" / "event-driven analytics"
- "Kafka" / "Kinesis" / "Pulsar" / "Pub/Sub" as the backbone
- "Flink" / "Spark Streaming" / "Beam" / "ksqlDB" as processors
- "Windowing" / "tumbling window" / "sliding window" / "session window"
- "Watermarks" / "late events" / "out-of-order events"
- "Exactly-once" / "at-least-once delivery"
- "Sub-second" / "low-latency" pipeline requirements

Non-signals:
- A queue for background work (email sends, image processing) — that's not streaming, that's async job processing; see `references/patterns.md` "Queue vs log."
- A scheduled batch job that runs every 5 minutes — that's `batch-etl`, even if the cadence is short.
- A real-time API (request/response) — that's a synchronous service, not a streaming pipeline.

## Additional elicitation (beyond the universal seven)

1. **End-to-end latency budget.** From event ingest to final sink, what's the SLA? Sub-second is much harder than 30s; 30s is much harder than 5min.
2. **Event volume shape.** Steady-state events/sec, peak events/sec, average event size, max event size. Streaming throughput is partition-bound.
3. **Ordering requirements.** Must events within a key be processed in order? Across keys? Globally? Global ordering is rarely required and very expensive.
4. **Exactly-once semantics.** Exactly-once **delivery** is a fantasy; exactly-once **processing** is achievable for specific source/sink combinations. Which sinks need it (financial events, billing) and which can tolerate at-least-once with idempotency (analytics counts)?
5. **Windowing semantics.** Tumbling (fixed non-overlapping), sliding (fixed overlapping), session (gap-bounded). Per-aggregation, the window choice changes results.
6. **Late event tolerance.** Events arrive late (network delays, mobile clients, batch sources). How late is "still relevant" — 1 minute, 1 hour, 1 day? Watermarks too tight drop legitimate events; too loose holds state forever.
7. **State size per operator.** Stateful operators (joins, windowed aggregates, sessionization) hold state proportional to active keys × per-key state. Will this fit in memory? On local SSD? Need RocksDB?
8. **Reprocessing strategy.** When a bug ships in the processing logic, how do you reprocess past events? Replay from Kafka offset? From a checkpointed source? Days or weeks of replay?
9. **Schema evolution.** How do you add a field to an event type without breaking consumers? Schema registry with compatibility rules, or schema-on-read?

## Recurring failure modes

### Backpressure overflow

**Symptom.** Consumers fall behind producers. Broker queues fill. Eventually the producer blocks, drops events, or the broker rejects writes.

**Why it happens.** Producer rate exceeds sustained consumer rate. Often a deploy makes consumers slower; a traffic spike outpaces consumer scaling; a downstream sink degrades.

**Mitigation.** Monitor consumer lag as a first-class metric (Kafka lag in seconds, not just message count). Alert on growing lag, not just zero capacity. Auto-scale consumers based on lag. For unavoidable load, shed at the producer (drop low-priority events) rather than blocking everything.

### Hot partition / key skew

**Symptom.** One partition has 100× the traffic of others. Its consumer is saturated; others are idle. Cluster utilization looks fine on average but one consumer is the bottleneck.

**Why it happens.** Partition key chosen for ordering convenience without distribution analysis. Common: `tenant_id` when one tenant is a celebrity; `user_id` when there's a power user; `null`/empty-string as default values.

**Mitigation.** Analyze key distribution before deploying. For unavoidable hot keys, secondary partitioning (`tenant_id + hash(record_id) % 10` for the hot tenant); a separate dedicated partition for known hot keys.

### State explosion

**Symptom.** Stateful operator (windowed aggregation, dedup, join) holds unbounded state. Memory grows until OOM; checkpoints get larger until they time out.

**Why it happens.** No TTL on state, infinite watermark patience, or a key cardinality much higher than expected (e.g., aggregating by `user_id × hour` for 1B users × 720 hours/month).

**Mitigation.** Always TTL stateful operator state. Tighten watermarks until late events are negligible (or accept the dropped events). Profile state size in dev under realistic key cardinality.

### Out-of-order events processed in wrong order

**Symptom.** Event B (caused by A) is processed before A. Downstream sees the effect without the cause. Aggregations are wrong.

**Why it happens.** Across-partition ordering doesn't exist in most brokers. Within-partition ordering is preserved only if the partition key correctly groups causally related events.

**Mitigation.** Choose the partition key so causally related events go to the same partition. For cross-key causal relationships, use event timestamps and processing-time vs event-time distinction (Flink's event-time + watermarks).

### Late event dropping

**Symptom.** A meaningful fraction of events arrive after the watermark and get silently dropped. Reports are wrong but no one knows.

**Why it happens.** Watermark policy too tight for the actual late-arrival distribution. Mobile events from poor-connectivity regions; batch-loaded historical events; clock skew on producers.

**Mitigation.** Measure the actual lateness distribution before setting watermarks. For occasional very-late events, side-output a "late events" stream rather than dropping silently; reprocess later.

### Exactly-once-delivery fantasy

**Symptom.** The design assumes a broker provides exactly-once delivery and skips idempotency.

**Why it happens.** Marketing language. Brokers can offer exactly-once *within their own boundaries*; end-to-end, retries and partial failures still produce duplicates somewhere.

**Mitigation.** Every consumer is idempotent. Idempotency keys, dedup windows, or upsert-shaped sinks. Treat duplicates as inevitable, not exceptional.

### Schema-incompatible deploy

**Symptom.** Producer ships a new event schema. Consumer (running the old version) crashes on the new field, or silently ignores it and processes incorrectly.

**Why it happens.** No compatibility contract. No schema registry. Producer and consumer evolve independently.

**Mitigation.** Schema registry (Confluent Schema Registry, Glue Schema Registry, etc.) with forward/backward/full compatibility rules. New fields are added as optional with defaults. Removed fields are deprecated for a release before removal.

## What god-tier designers always ask

1. **What's the partition key, and what's its distribution?** Without checking, you'll discover the hot partition in production.
2. **What's the watermark policy for late events?** Too tight loses events; too loose holds state forever. Measure first.
3. **How is operator state checkpointed and recovered?** A crash should not lose state if recovery semantics matter. Recovery time = checkpoint size / restore throughput; minutes is normal for large state.
4. **Reprocessing: replay from offset, or from a checkpointed source?** Kafka retention bounds replay; a checkpoint store (S3) doesn't but adds complexity.
5. **End-to-end exactly-once: which combinations support it?** Kafka → Flink → Kafka with transactions, yes. Kafka → custom HTTP sink, no — design idempotency into the sink.
6. **Schema evolution policy.** Optional fields with defaults; never remove without a deprecation cycle; schema registry enforced in CI.
7. **What's the failure mode when the broker is briefly unavailable?** Producer buffer fills; new events drop or block. Acceptable for analytics; not acceptable for billing.
8. **Lag SLO.** What's the maximum acceptable consumer lag (in seconds or events)? This is the streaming-specific availability metric.

## Common pitfalls

### Kafka as a database

**Symptom.** The design uses Kafka as the source of truth for application state, reading the full topic to reconstruct state on startup.

**Why it's wrong.** Kafka topics have retention; the "source of truth" is bounded by retention. Replaying terabytes of topics to bootstrap state on a restart is operationally painful. Kafka is a log; a database is a database.

**Fix.** A Kafka topic feeds a database (KV store, OLAP store, materialized view). State lives in the database; the topic carries change events.

### Treating "exactly-once delivery" as exactly-once processing

Already in `references/anti-patterns.md`; recurring here because streaming designs are especially prone.

### Coupling all consumers to one schema

A schema shared by 20 consumers means every schema change negotiates 20 consumer rollouts. Use schema evolution rules (additive only, optional with defaults) so consumers can stay on old versions.

### Ignoring partition count as a scaling lever

Partition count is the unit of consumer parallelism. Too few = consumer can't scale horizontally. Too many = per-partition overhead, slow rebalance, more metadata. Pick partition count based on max desired consumer concurrency, with 2–4× headroom for future growth.

### No DLQ for poison messages

A message that consistently fails to process (deserialization error, application bug on this specific payload) without a DLQ blocks the partition forever. Always: DLQ + alerting on DLQ depth.

### Mixing event-time and processing-time aggregations

Doing some aggregations in event-time and some in processing-time produces inconsistent results that are hard to reconcile. Pick one model per pipeline; default to event-time for correctness.

## Anchor numbers

These are rough order-of-magnitude figures; benchmark before relying on them.

- **Kafka broker throughput**: ~tens to low-hundreds of MB/s sustained writes per broker, depending on hardware and partition count. Easily ~100k+ messages/sec per broker for small messages.
- **Kafka partition throughput**: typically 10–50 MB/s per partition; this is the single-consumer ceiling for a partition. If you need more, increase partition count and consumer count proportionally.
- **Flink/Spark Streaming throughput**: highly operator-dependent. Simple pass-through can hit hundreds of K events/sec per task slot; complex stateful operators are an order of magnitude lower.
- **State size**: RocksDB-backed state in Flink scales to terabytes per task manager but checkpoint times grow accordingly.
- **Consumer lag**: < 1s lag is "real-time"; 1–10s is "near real-time"; > 10s is "we're falling behind, alert."
- **Watermark lateness tolerance**: usually 10s–10min for most workloads; > 1h means you're reprocessing batches inside a stream framework — consider whether batch is actually the right tool.

## Cross-archetype interactions

- **Streaming + multi-tenant**: partition by tenant for natural isolation, but watch for hot tenants. Separate topics per tenant tier (enterprise vs free) is sometimes warranted.
- **Streaming + write-heavy**: streaming is often the front door for write-heavy ingest pipelines. Reading the same archetype-list will sometimes show both apply.
- **Streaming + observability**: streaming pipelines need their own deep monitoring — consumer lag, partition skew, state size, checkpoint duration. Generic app metrics don't surface these.
