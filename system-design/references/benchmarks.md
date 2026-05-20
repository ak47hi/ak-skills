# Benchmarks

Load when an estimate needs sharper anchor numbers than the order-of-magnitude figures in `estimation.md`. This file gives **calibrated throughput ceilings, latency profiles, and known scaling cliffs** per common component, so estimates and recommendations aren't guesses.

**Last reviewed: 2026-05.** Hardware, software, and managed-service limits shift; re-check annually. Numbers below should be treated as **order of magnitude with one significant digit of precision** — they're sanity anchors, not benchmarks for production sizing. Always validate against the team's own workload before committing.

## Methodology and provenance

These figures synthesize public sources: vendor documentation (AWS, GCP, Azure, official Postgres / Kafka / Redis docs); published engineering posts from teams operating at scale (Discord, Stripe, Uber, Shopify, Cloudflare, GitHub, Netflix, etc.); community benchmark tools (pgbench, sysbench, YCSB, k6, wrk); and well-known academic / industry reports. Specific URLs intentionally not cited inline — they rot. The skill should remind users that **production sizing requires the team to benchmark their own workload**; this file's job is to make the first-pass estimate defensible.

When a number is unusually sensitive to workload shape (e.g. Postgres write throughput depends heavily on row size + index count + WAL config), it's flagged with a range and the dominant variable.

---

## Network and latency anchors

The cross-region latencies that decide whether synchronous calls work.

| Hop | Typical RTT |
|---|---|
| Within a host (loopback) | < 0.1 ms |
| Within an AZ (same DC) | 0.3 – 0.8 ms |
| Cross-AZ within a region | 1 – 3 ms |
| US-east ↔ US-west | 60 – 80 ms |
| US-east ↔ EU-west (Ireland/Frankfurt) | 70 – 110 ms |
| US-east ↔ APAC (Singapore/Tokyo) | 150 – 220 ms |
| Intercontinental worst case (e.g. Sydney ↔ São Paulo) | 250 – 320 ms |

**Bandwidth ceilings (per NIC, single instance):**

| Instance class | NIC bandwidth | Realistic throughput |
|---|---|---|
| Small (general purpose, ~4 vCPU) | 5–10 Gbps | ~600 MB/s – 1.2 GB/s |
| Medium (16–32 vCPU) | 10–25 Gbps | ~1.2–3 GB/s |
| Large (network-optimized, e.g. c6in/c7gn) | 50–200 Gbps | ~6–25 GB/s |

**Practical implication.** A 10k QPS service returning 10 KB responses needs ~100 MB/s outbound, comfortably within a single small instance. A 50k QPS service returning 100 KB responses needs ~5 GB/s — beyond a single NIC, must distribute.

---

## Storage primitives

### Local disk

| Storage type | Random IOPS (4K) | Sequential read | Sequential write |
|---|---|---|---|
| Local NVMe SSD (recent) | 500k – 1M+ | 3 – 7 GB/s | 1 – 5 GB/s |
| Local SATA SSD | 50k – 100k | 500 MB/s | 400 MB/s |
| Cloud block storage (gp3 / pd-ssd, default) | 3000 baseline (provisionable to 16k) | 125 – 1000 MB/s | 125 – 1000 MB/s |
| Cloud block storage (io2 / extreme) | 64k – 256k per volume | 1000 – 4000 MB/s | 1000 – 4000 MB/s |
| Spinning disk (rare in cloud now) | ~150 | 100 – 200 MB/s | 100 – 200 MB/s |

**Practical implication.** "Disk is slow" usually means cloud-default volumes, not local NVMe. A Postgres on local NVMe behaves very differently from one on a default EBS volume.

### Object storage (S3 / GCS / Azure Blob)

| Metric | S3 default |
|---|---|
| GET requests per prefix per second | ~5500 |
| PUT/POST/DELETE per prefix per second | ~3500 |
| First-byte latency (single GET) | 50 – 200 ms |
| Throughput per request (with multipart, parallel) | up to ~1 GB/s |
| Aggregate throughput (with prefix sharding) | effectively unbounded |
| Per-object size limit | 5 TB |

**Scaling cliff.** The per-prefix rate limit is real; high-volume workloads must shard the key prefix (`shard_id/object_key` instead of `object_key`). The 5500/3500 limits scale linearly with prefix count.

---

## Relational databases

### Postgres

Per single instance (community Postgres or RDS / Aurora / Cloud SQL on equivalent hardware). Auto-tuning, recent versions (≥ 15), modest schema.

| Instance class | Approx ceiling |
|---|---|
| Small (4 vCPU, 16 GB RAM) | ~5k read QPS / ~1k write QPS (cached workload) |
| Medium (8–16 vCPU, 32–64 GB RAM) | ~20k–50k read QPS / ~5k–15k write QPS |
| Large (32–64 vCPU, 128–256 GB RAM) | ~100k–200k read QPS / ~20k–40k write QPS |
| Largest single-instance (96+ vCPU, 768 GB+ RAM) | ~300k+ read QPS / ~50k+ write QPS for simple workloads |

**Read QPS** assumes warm cache (working set fits in `shared_buffers` + page cache). Cold cache or working-set-exceeds-RAM drops by 1–2 orders of magnitude.

**Write QPS** is for simple single-row writes with default WAL config. With `synchronous_commit = off`, write throughput can double; with COPY-style bulk insert, 5–10× higher row insertion rate. Each additional index multiplies write cost ~1.2–1.5×.

**Known scaling cliffs:**
- Connection saturation: default `max_connections` ~200; beyond this PgBouncer is mandatory. Real workloads should size connection pool 2–4× CPU count.
- WAL archiving on slow storage limits sustained write rate.
- VACUUM under heavy writes can starve foreground queries; tune `autovacuum_max_workers`.
- Table size > 100 GB and missing indexes turn into sequential scans → seconds-per-query.
- Replication lag grows nonlinearly under write load; tail latency on followers spikes during catch-up.

**Realistic single-primary ceiling:** ~50k–100k write QPS for sustained loads on the largest instances. Beyond, partition the table, push some writes to a read-replica-friendly OLAP store, or shard.

### MySQL / MariaDB

Similar shape to Postgres, with InnoDB-specific tradeoffs. Per-row-overhead and index cost roughly comparable; ProxySQL is the equivalent of PgBouncer. Group-replication lag profiles differ; consult MySQL operator docs before assuming Postgres-equivalent.

### Aurora / Cloud Spanner / CockroachDB

Managed distributed-SQL options trade per-row latency for horizontal scale. Aurora reads scale to 15 replicas; Spanner / CockroachDB scale writes across nodes. Per-node throughput is typically a fraction (30–60%) of a comparably sized Postgres for simple workloads, made up for by linear scaling. Latency for global / cross-region operations is dominated by inter-region RTT (see Network section).

---

## Key-value and cache

### Redis

| Setup | Approx ceiling |
|---|---|
| Single-thread Redis, single node | 80k – 200k ops/sec for simple GET/SET |
| Redis with I/O threading enabled | 200k – 500k ops/sec |
| Cluster mode (sharded) | Linear scaling; 1M+ ops/sec achievable |
| Latency p99 (same-AZ) | < 1 ms typical |

**Workload sensitivity:** mass operations (MGET, MSET, pipelined commands) hit 5–10× the per-command rate. Large values (> 100 KB) drop throughput substantially.

**Scaling cliffs:**
- Single-threaded execution: one slow command (e.g. `KEYS *`, large `SUNION`) blocks everything.
- Memory pressure: write performance degrades when memory exceeds `maxmemory` and eviction kicks in.
- Persistence (AOF/RDB) adds I/O overhead; AOF every-second is common compromise.

### Memcached

| Metric | Approx ceiling |
|---|---|
| Per-node ops/sec | 100k – 1M+ (multi-threaded; scales with cores) |
| Latency p99 | < 1 ms typical |

Memcached is simpler than Redis (no persistence, no data structures, just KV). Throughput per core is comparable; total throughput scales with cores natively.

### DynamoDB

| Metric | Per-partition limit |
|---|---|
| Reads (strongly consistent) | 1000 RCU/sec |
| Reads (eventually consistent) | 2000 RCU/sec |
| Writes | 1000 WCU/sec |
| Item size limit | 400 KB |
| Latency p99 (read) | single-digit ms |
| Latency p99 (write) | single-digit ms |

**Practical implication.** A partition is bound by these limits. Hot partition = throttling. DynamoDB auto-scaling redistributes partitions but has hours-of-warm-up; provision for peak, not average, for spiky workloads. Adaptive capacity (newer feature) handles short hot-partition bursts.

**Aggregate throughput** scales linearly with provisioned capacity, no soft ceiling.

---

## Document and wide-column

### MongoDB

Single-node Mongo (recent version, WiredTiger):

| Operation | Approx ceiling |
|---|---|
| Reads (cached) | ~30k–100k QPS |
| Writes (single doc) | ~10k–30k QPS |

Replica set adds reads scalability (secondaries serve reads); sharded cluster scales writes. Per-shard throughput similar to single-node. Aggregation pipelines (especially `$lookup`) can dominate latency and CPU; sharded `$lookup` is particularly expensive.

### Cassandra / ScyllaDB

| Operation | Per-node ceiling |
|---|---|
| Writes | 30k – 100k+ QPS (Cassandra) / 100k+ (Scylla) |
| Reads | 20k – 80k+ QPS |

Linear horizontal scaling is the design goal; per-node ceilings can be added to cluster scale. Scylla (Seastar-based) is 2–5× higher per-node throughput than Cassandra at similar latency. Both have tunable consistency (QUORUM, ONE, ALL); tail latency dominated by slowest replica at the chosen consistency level.

**Scaling cliffs:**
- Compaction can cause latency spikes; tune compaction strategy per workload.
- Wide partitions (> 100 MB) cause GC pressure and slow reads.
- Repair is operationally expensive; cluster size and repair window must be planned.

---

## Messaging

### Kafka

| Setup | Approx ceiling |
|---|---|
| Per broker (recent version, multi-disk, 10 GbE) | 100k – 1M+ messages/sec |
| Per partition (single producer / consumer) | 10 – 50 MB/sec, ~10k–100k msg/sec for small messages |
| Producer batching enabled | 5–10× higher throughput vs unbatched |
| Latency end-to-end p99 (tuned) | 10 – 100 ms typical |

**Scaling cliffs:**
- Per-partition throughput is a hard ceiling for a single consumer; horizontal scale = more partitions.
- Replication factor multiplies broker write load by RF.
- Consumer rebalances during scaling pause processing briefly.
- Too many partitions (10k+ per broker) slows controller operations; rebalance becomes expensive.

**Aggregate cluster throughput:** linearly scalable up to "many millions of msg/sec" at the cost of operational complexity. Past ~1k partitions across cluster, expect dedicated Kafka operations team.

### Kinesis

| Metric | Per-shard limit |
|---|---|
| Write throughput | 1 MB/sec or 1000 records/sec |
| Read throughput | 2 MB/sec aggregate across consumers |
| Latency end-to-end | ~70 ms – 200 ms typical |

Kinesis is shard-bound; throughput scales with shard count. Provisioned cost is per-shard regardless of utilization. Enhanced Fanout provides per-consumer 2 MB/sec dedicated throughput at additional cost.

### SQS

| Metric | Standard queue | FIFO queue |
|---|---|---|
| Send/Receive/Delete API rate | Effectively unlimited (no documented soft cap) | 300/sec without batching, 3000/sec with batching, per message group |
| Message size limit | 256 KB (extend with S3 to 2 GB) | Same |
| Visibility timeout | 0 to 12 hours | Same |
| Latency p99 | < 100 ms typical | < 100 ms typical |

**Scaling cliffs:**
- Standard SQS has at-least-once delivery and best-effort ordering — duplicates are real.
- FIFO ordering is per-message-group; one queue with one group is single-consumer-fast.
- Long polling (20s wait time) is cheaper than short polling for low-volume queues.

### RabbitMQ

| Setup | Approx ceiling |
|---|---|
| Single node | 20k – 50k messages/sec (with persistence) |
| Single node, in-memory only | 100k – 200k msg/sec |
| Cluster (mirrored queues) | 10k – 30k msg/sec sustained — mirroring costs throughput |

RabbitMQ favors flexibility (exchanges, routing, message TTL, priority queues) over raw throughput. For high-throughput use cases, Kafka is typically the better fit.

---

## Analytical / OLAP

### ClickHouse

| Operation | Per-node typical |
|---|---|
| Inserts (batched, 1k–10k rows per batch) | 100k – 1M+ rows/sec |
| Inserts (single-row) | < 1k rows/sec — single-row inserts are an anti-pattern in ClickHouse |
| Aggregation queries over TB | seconds, depending on filters |
| Concurrent queries per node | tens (low concurrency, high per-query) |

ClickHouse is designed for high-throughput inserts (batched) and fast aggregation; not for high-concurrency point lookups.

### BigQuery / Snowflake / Redshift

These are warehouse-style; sizing is by compute units (slots, warehouses, nodes). Per-query latency is seconds to minutes regardless of data size, dominated by query planning and parallelism. Cost models differ: BigQuery is per-data-scanned; Snowflake is per-compute-time; Redshift is per-provisioned-cluster-hour.

**Per-query latency anchors:**

| Query shape | Typical latency |
|---|---|
| Point lookup on small table | 200 ms – 2 sec |
| Aggregation over 100 GB | 2 – 30 sec |
| Aggregation over 10 TB | 30 sec – 5 min |
| Cross-table join, large | 1 – 30 min |

These are warehouse defaults; with proper partitioning, clustering, and materialized views, large queries can be 10× faster.

---

## Search

### Elasticsearch / OpenSearch

| Operation | Per-node typical (recent version, 16 vCPU) |
|---|---|
| Indexing rate | 5k – 50k docs/sec |
| Search QPS (warm cache, simple query) | 500 – 5000 QPS |
| Latency p99 (simple search) | 10 – 100 ms |
| Latency p99 (complex / aggregation) | 100 ms – seconds |

**Scaling cliffs:**
- Shard count: aim for shards of 10–50 GB; too many shards = overhead, too few = no parallelism.
- Heap pressure: ES heap is the constraining resource; > 30 GB heap = GC pauses.
- Field cardinality: high-cardinality fields explode index size and memory.
- Refresh interval: default 1s; increase to 30s for high-throughput indexing.

---

## Compute / serving

### HTTP service per-instance throughput (single instance, 8 vCPU)

| Runtime / framework | Simple-endpoint QPS ceiling |
|---|---|
| Go (net/http, no allocs in hot path) | 50k – 200k QPS |
| Rust (axum / actix-web) | 50k – 200k QPS |
| Node.js (express, no async I/O in hot path) | 10k – 30k QPS |
| Java (Spring Boot, default) | 10k – 50k QPS |
| Java (vert.x, Netty) | 50k – 150k QPS |
| Python (FastAPI / uvicorn, async) | 5k – 20k QPS |
| Python (Django / Flask, sync gunicorn) | 1k – 5k QPS |
| Ruby (Rails / puma) | 1k – 5k QPS |

These are "hello world" or "near-trivial endpoint" ceilings. Real endpoints with DB calls, serialization, auth, etc. typically run at 10–30% of this ceiling — the language matters less when the database is the bottleneck.

### Nginx as a reverse proxy / static server

| Mode | Per-instance ceiling |
|---|---|
| Static asset serving | 50k – 200k req/sec |
| HTTP reverse proxy | 30k – 100k req/sec |
| TLS termination (modern hardware) | 20k – 50k connections/sec |

### Lambda / cloud functions

| Metric | Typical |
|---|---|
| Cold start latency (Node/Python, small package) | 200 – 1000 ms |
| Cold start latency (Java/.NET) | 1 – 5 sec |
| Warm invocation latency | 1 – 50 ms (excluding handler logic) |
| Max concurrent executions per account (AWS, default) | 1000 (raisable) |
| Max execution time | 15 min |
| Provisioned concurrency: cold-start eliminated, costs as if running |

**Scaling cliffs:**
- Cold start dominates for low-traffic, latency-sensitive workloads. Use provisioned concurrency or keep instances warm.
- Lambda is uneconomic vs always-on instances above ~50% utilization.

---

## Load balancers and CDN

### Application Load Balancer (ALB)

| Metric | Typical |
|---|---|
| Requests per second per ALB | Auto-scales; soft limit ~75k req/sec/ALB before contact-support |
| Connections per second | Tens of thousands |
| Latency added | < 5 ms typical |
| HTTPS termination | Built-in, free at this latency |

### Network Load Balancer (NLB)

| Metric | Typical |
|---|---|
| Millions of req/sec at low latency | Yes, but TCP-layer only |
| Latency added | < 100 µs |

### CloudFront / Cloudflare / Fastly CDN

| Metric | Typical |
|---|---|
| Edge cache hit latency | 10 – 50 ms (regional POP) |
| Origin fetch latency | depends on origin RTT |
| Throughput | effectively unbounded for cacheable content |
| Cache hit ratio | 90%+ for static; 50–80% for "dynamic but cacheable" content |

---

## Per-architecture-layer latency budgets

When p99 < 200 ms is the goal, the budget gets spent layer by layer. Realistic split for a typical web API request:

| Layer | Typical p99 cost |
|---|---|
| Network: user ↔ POP (CDN edge) | 20 – 80 ms |
| POP ↔ origin region (cache miss / dynamic) | 20 – 100 ms |
| ALB / API gateway | 1 – 5 ms |
| Application server handler | 5 – 50 ms |
| Database query (single-statement, indexed) | 1 – 20 ms |
| Cache lookup (Redis, same-AZ) | < 1 ms |
| Downstream service call (RPC, same-region) | 5 – 50 ms |
| Outbound TLS handshake (uncached) | 50 – 150 ms |

A request that crosses 5 services synchronously, each at 20 ms, is already at 100 ms before any DB work. The budget is consumed by **counting boundary crossings**.

**Practical implication.** Tightening p99 < 100 ms is mostly about removing sync boundary crossings, not optimizing individual steps. The cheapest 100 ms is the one you didn't spend.

---

## How to use these numbers in design

1. **For estimation: anchor, then validate.** Use these as the first-pass anchor for capacity questions ("can a single Postgres handle this workload?"). Validate against the team's actual workload before committing to a sizing.
2. **For "is one box enough" checks.** Most of these single-instance ceilings are surprisingly high. If the estimate sits at 30% of a single-instance ceiling, **distribution isn't earned by throughput** — it's earned by HA, geo, or blast radius (see `estimation.md`'s single-machine baseline section).
3. **For ADR alternatives.** When considering "should we move from X to Y," compare both at scaled capacity. Don't compare a small Postgres to a large Cassandra; compare like-sized.
4. **Don't quote these as hard limits.** Workload shape, version, hardware, and configuration shift these numbers by factors of 2–10. They're starting points, not contracts.

---

## How to update this file

Annually, or when a major version of a primary component ships:

1. Re-check vendor documentation for any published "per-resource limits."
2. Scan engineering blogs (Discord, Stripe, Netflix, Uber, Shopify, Cloudflare, etc.) for "we now do N at scale" posts that update the high-water marks.
3. For numbers that have shifted by > 2×, update inline. For numbers that have shifted by < 2×, leave them — within the file's "one significant digit" tolerance.
4. Update the **Last reviewed** date at the top of the file.
5. If a new service category emerges (e.g. vector databases reaching general adoption), add a section.

This file is calibration, not gospel. The numbers age; the methodology doesn't.
