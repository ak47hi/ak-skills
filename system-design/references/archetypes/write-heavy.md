# Write-heavy

Load when the prompt describes ingest pipelines, telemetry firehoses, IoT events, ad-tech impressions, log aggregation, or any system where sustained write throughput is the binding scaling concern.

The defining concern: **absorbing writes at rate without losing data, with sharding, batching, append-only patterns, and read-pattern-aware index minimalism dominating the design.**

## When this archetype fires

Signal cues:
- "Ingest pipeline" / "telemetry" / "events firehose" / "IoT events"
- "Ad impressions" / "ad-tech" / "click stream" / "impression log"
- "High write throughput" / "write QPS in the hundreds of thousands"
- "Append-only" / "immutable log" / "time-series ingest"
- "Log aggregation" / "audit log" / "trace ingest"

Non-signals:
- A standard OLTP app with normal write rate (hundreds to a few thousand writes/sec) — not this archetype; the universal foundation handles it.
- A streaming pipeline (events flow through processing stages) — that's `real-time-streaming`, even if it includes writes.
- A batch-loading job — that's `batch-etl`, even if it writes large volumes.

## Additional elicitation (beyond the universal seven)

1. **Sustained vs burst write rate.** A system with 10k QPS steady-state and 100k QPS peak-burst is very different from one with sustained 100k QPS. Burst can be absorbed with queueing; sustained requires actual capacity.
2. **Per-write durability requirement.** Must each write be durable before acknowledging the client (synchronous, slower), or can the system buffer and acknowledge optimistically (faster, with edge-case loss possibility)? Different per data class.
3. **Read pattern over the writes.** Immediately read back (transactional)? Analytical batch reads (warehouse)? Lookups by primary key only? Range scans? Never read (write-only audit log)? The read pattern is the binding constraint for index strategy.
4. **Acceptable late / out-of-order writes.** Telemetry from mobile clients arrives delayed and out-of-order. Is that fine, or must the system reject them? How late is "still acceptable"?
5. **Dedup requirements.** The same event arriving twice (client retry, broker redelivery) — what should happen? Keep both (count is now wrong)? Dedup (idempotency key + dedup window)? Latest-wins?
6. **Retention policy.** Append-only data grows forever without retention. Daily? Yearly? Indefinitely? Cold-tier after N days? The retention strategy is part of the design, not an afterthought.
7. **Per-record write amplification.** A single logical write may become multiple physical writes (every index updated, replication factor multiplier, WAL write). Counting these matters at high throughput.
8. **Schema flexibility.** Are the writes schema-locked (every event has the same fields) or schema-flexible (events of many types)? Schema-flexible storage (JSONB, document) is more accommodating but slower per write.

## Recurring failure modes

### Hot shard / hot partition

**Symptom.** One partition or shard takes 80% of write traffic. That node saturates while others are idle. Adding more nodes doesn't help; the hot one is still the bottleneck.

**Why it happens.** Shard key chosen for ordering or query convenience without analyzing distribution. Worst case: timestamp as shard key — all current writes go to the latest range.

**Mitigation.** Hash the shard key (or hash a prefix); analyze distribution before deployment. For unavoidable hot keys (a celebrity user, a high-volume tenant), secondary sharding within the hot partition.

### Write amplification

**Symptom.** Each logical write turns into 5–20 physical writes (1 row to the table + 5 index updates + 3 replicas of each + WAL). DB CPU and I/O are saturated at a logical write rate well below the documented capacity.

**Why it happens.** Many indexes, high replication factor, synchronous WAL. The amplification multiplies.

**Mitigation.** Audit indexes; remove unused ones. Async replication where consistency allows. Batched writes (group commits) so WAL fsync amortizes over many rows.

### Monotonically increasing partition key

**Symptom.** Shard key is `created_at` or auto-incremented ID. All current writes hit the same shard (the latest). Older shards are read-only. Storage utilization across shards is uneven (newest fills up; oldest is empty).

**Why it happens.** Designer picked the natural key without thinking about distribution.

**Mitigation.** Hash-prefix the key (`hash(record_id) % 16 + ":" + record_id`). Or partition by hash of a high-cardinality field that doesn't correlate with time.

### Synchronous replication overwhelms write rate

**Symptom.** Synchronous replication (write to N replicas before ACK) means every write waits for the slowest replica. Tail latency goes through the roof under load.

**Why it happens.** Strong durability needs were assumed without measuring the cost.

**Mitigation.** Async replication where loss-on-failure is acceptable; quorum replication (W=2 of N=3) for compromise; only the most durable data (financial state) gets full synchronous everywhere.

### Disk fill from append-only without retention

**Symptom.** Storage grows linearly forever. Eventually fills. Operational scramble to expand or delete.

**Why it happens.** Retention was an afterthought. Or retention rules exist but lifecycle never runs.

**Mitigation.** Retention policy defined at table creation time. Partitioned tables with explicit drop-old-partition jobs. Monitoring on storage growth rate and projected fill date.

### Backpressure overflow downstream

**Symptom.** Ingest accepts writes happily. Downstream consumers (analytics jobs, indexers, aggregators) can't keep up. Queue grows, then catastrophically lags.

**Why it happens.** Ingest capacity isn't bounded by downstream capacity.

**Mitigation.** Either size ingest to downstream capacity, or accept fanout-with-bounded-buffers + shed at edges when full. Don't accept what you can't process.

### Duplicate writes (idempotency gap)

**Symptom.** Same event written twice due to client retry. Downstream counts are wrong; aggregations double-count.

**Why it happens.** No idempotency key on the write path. The write is at-least-once, but the consumer treats it as exactly-once.

**Mitigation.** Idempotency key on every write. Dedup window (the time during which duplicates are detected). For high-volume systems, Bloom filters or HyperLogLog approximate dedup if exact is too expensive.

## What god-tier designers always ask

1. **Shard key distribution — measured, not assumed.** Hash distribution? Range distribution? Where are the hotspots?
2. **Write batching — at the producer, at the broker, at the sink?** Batched writes are orders of magnitude more efficient. Each layer can batch independently.
3. **Index strategy — every index is a write amplifier. Which are non-optional?** Audit and remove the rest.
4. **Per-write durability — synchronous, quorum, or async?** Per data class, not globally.
5. **Retention policy — defined at design time?** Append-only without retention is a slow-motion outage.
6. **Read patterns over the writes — drives storage choice.** Append-only with no reads = log file; append-only with PK lookups = KV; append-only with range scans = wide-column / time-series.
7. **Backpressure — what does the system do at saturation?** Block producer (slow), drop oldest (data loss), drop newest (data loss), shed at edge (data loss but bounded)? Pick deliberately.
8. **Schema evolution — adding a field — what's the cost?**
9. **At-least-once vs exactly-once — and the idempotency story?**

## Common pitfalls

### Timestamp as shard key

The textbook anti-pattern. All current writes hit one shard.

### Synchronous dual-write to multiple stores

Already covered in `references/anti-patterns.md`; recurring here because high write rate makes the divergence faster and more catastrophic. Use outbox or CDC.

### Too many indexes on write-heavy tables

A write to a row with 8 indexes is 9 writes (1 row + 8 index updates). Each index needs to be earned by a real query.

### Synchronous replication for everything

Strong durability for every byte is rare. Differentiate: financial state synchronous, audit logs quorum, telemetry async.

### Single-row inserts at high rate

Inserting one row at a time costs N × (network round-trip + transaction overhead). Batch inserts (1000 rows in one statement, COPY, multi-value INSERT) are 10–100× more efficient. Always batch at the producer.

### Ignoring late writes

Mobile clients send delayed events. The aggregation pipeline only sees "today's" events. Yesterday's late events are dropped silently. Aggregations are slightly wrong, undetectable without comparison.

### No idempotency on the write path

The classic. Every consumer of an at-least-once system needs idempotency; the write path needs it too (clients retry).

### Disk space monitoring as an afterthought

Storage grows; alerts fire late; emergency capacity expansion is expensive. Project growth rate from current usage; alert at 60% utilization, not 90%.

## Anchor numbers

These are rough order-of-magnitude figures; specific workloads vary widely.

- **Postgres single primary, write QPS**: typically **5k–30k** for simple single-row inserts; batched COPY can reach **100k+ rows/sec**.
- **Cassandra / ScyllaDB per node**: **30k–100k+ writes/sec** for simple writes; linear horizontal scaling.
- **Kafka per broker**: **hundreds of thousands of messages/sec** for small messages; can reach **millions/sec** with batching and sufficient hardware.
- **InfluxDB / TimescaleDB**: **100k+ inserts/sec per node** with good schema design.
- **ClickHouse**: **millions of inserts/sec** with batching (it's designed for this; single-row inserts are an anti-pattern in ClickHouse).
- **Per-broker bandwidth ceiling**: **~1.25 GB/s** on a 10 Gbps NIC; bandwidth often the bottleneck before CPU for high-volume writes.
- **Write amplification**: typical Postgres table with 5 indexes and RF=3 (logical → physical write) is **15–30×**. Audit indexes ruthlessly at high write rates.
- **Realistic single-machine write ceiling**: **~100k writes/sec** for moderately complex writes; distributing only justified above this.

## Cross-archetype interactions

- **Write-heavy + real-time streaming**: ingest is often a streaming pipeline. Kafka/Kinesis as the buffer between producers and sinks absorbs burst writes.
- **Write-heavy + multi-tenant**: per-tenant sharding usually works well — tenants are natural shard boundaries with bounded growth. Watch for hot tenant skew.
- **Write-heavy + hot-cold-tiered**: write-heavy data quickly outgrows hot storage; tiered lifecycle is mandatory. Hot for recent N days, warm for analytical access, cold for compliance retention.
- **Write-heavy + observability**: write throughput, write latency p99, write amplification ratio, per-shard distribution are the metrics that matter; generic CPU/memory miss the binding constraints.
