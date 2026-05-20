# Estimation

Load when entering **Phase 2 (Estimate)**. Goal: produce four numbers (peak QPS, storage at 12 months, bandwidth, working-set size), then run the **single-machine baseline check** before any architecture is drawn. An estimate that fits one box reshapes the design.

## The latency ladder (orders of magnitude that matter)

Memorize the ratios, not the exact nanoseconds. The exact numbers shift with hardware; the **ratios** decide design.

| Operation | Order of magnitude | Ratio to L1 |
|---|---|---|
| L1 cache reference | ~1 ns | 1× |
| Branch mispredict | ~5 ns | 5× |
| L2 cache reference | ~5 ns | 5× |
| Mutex lock/unlock (uncontended) | ~25 ns | 25× |
| Main memory reference | ~100 ns | 100× |
| Compress 1 KB (snappy/lz4) | ~1–3 µs | ~1000× |
| Send 1 KB over 1 Gbps network (same DC) | ~10 µs | 10,000× |
| Read 1 MB sequentially from RAM | ~25 µs | 25,000× |
| SSD random read (4 KB) | ~100 µs | 100,000× |
| Round trip within same datacenter | ~500 µs | 500,000× |
| Read 1 MB sequentially from SSD | ~1 ms | 1,000,000× |
| Disk seek (spinning) | ~10 ms | 10,000,000× |
| Read 1 MB sequentially from disk | ~20 ms | 20,000,000× |
| Round trip cross-region (US east ↔ west) | ~70 ms | 70,000,000× |
| Round trip intercontinental | ~150 ms | 150,000,000× |

The two ratios that decide most architectures:

- **Memory vs SSD: ~1000×.** Caching works because of this gap. The whole point of Redis in front of Postgres is to skip a few hundred SSD reads.
- **Same-DC vs cross-region: ~140×.** Synchronous calls across regions are a different system than synchronous calls within one. Active-active geo replication is a fundamentally different problem from intra-region HA.

## Data-size cheat sheet

Powers of two are the unit of capacity. Don't carry exact bytes in your head — carry these.

| Notation | Bytes | Practical meaning |
|---|---|---|
| 1 KB | ~10³ | a short tweet, a row in a small table |
| 1 MB | ~10⁶ | a high-res photo, a few hundred rows |
| 1 GB | ~10⁹ | a small DB, an hour of HD video |
| 1 TB | ~10¹² | a medium prod DB, a few thousand hours of video |
| 1 PB | ~10¹⁵ | a large platform's analytical store |

Useful conversions:
- Seconds in a day: ~86,400 (call it 10⁵).
- Seconds in a year: ~3.15 × 10⁷ (call it 3 × 10⁷).
- "Daily" → "per second": divide by 10⁵; "yearly" → "per second": divide by 3 × 10⁷.

## Capacity formulas

### Peak QPS

```
peak_QPS = (DAU × actions_per_user_per_day × peak_factor) / 86,400
```

- `peak_factor` ≈ 2–3× for general human-traffic systems with a clear daily pattern. Higher (5–10×) for systems with launch spikes, news events, or scheduled fan-out.
- Peak QPS is what the system must absorb, not what it averages.

### Storage per year

```
storage_per_year = events_per_day × 365 × avg_event_bytes × (1 + index_overhead) × replication_factor
```

- `index_overhead`: 0.3–1.0× the data size for a write-heavy table with a few indexes; can exceed 1× for heavily indexed analytical tables.
- `replication_factor`: 2× for primary + warm standby; 3× for typical distributed-DB defaults (Cassandra, MongoDB, HDFS).
- Multiply by retention years if the system keeps history.

### Bandwidth

```
peak_bandwidth = peak_QPS × avg_payload_bytes
```

Per direction (inbound and outbound usually differ). Output bandwidth is often where small services first hit a NIC limit — a 10 KB response × 50k QPS = 500 MB/s = a 4 Gbps link saturated.

### Working set

The portion of data that's actively read in a given window (an hour, a day). The working set should fit in RAM (cache or DB buffer pool) for the system to behave well. If working set > RAM, the system pages from SSD and latency degrades nonlinearly.

```
working_set ≈ active_entities × bytes_per_entity
```

For social feeds: active users × content × fan-out. For e-commerce: active SKUs × catalog row size. For analytics: query-touched rows × row size.

## Little's Law

`L = λW`

- `L` = number of items in the system (queue depth, concurrent requests).
- `λ` = arrival rate (requests/sec).
- `W` = average time each item spends in the system (seconds).

Used in two directions:

**Sizing a thread/worker pool.** If a service handles 10k QPS with 50 ms average latency, you need at minimum `10,000 × 0.050 = 500` concurrent in-flight slots (threads, async tasks, goroutines, etc.). Add headroom; with no headroom, p99 queues up.

**Detecting saturation.** If queue depth keeps growing, `λ > 1/W` for your current capacity. Either reduce arrival rate (load shed), reduce service time (optimize the hot path), or add workers — but you must do *one* of those, not "just add a retry."

Little's Law also explains why retries are dangerous under load: a retry storm makes `λ` jump while `W` is degrading, so `L` explodes.

## The single-machine baseline

Before you sketch a distributed system, ask: **could this run on one box?**

Rough ceilings for a modern commodity instance (32 vCPU, 128 GB RAM, NVMe SSD, 10 Gbps NIC):

| Resource | Order-of-magnitude ceiling |
|---|---|
| Postgres read QPS (cached working set, simple queries) | 50k–200k QPS |
| Postgres write QPS (durable, single-row) | 5k–30k QPS |
| Redis ops/sec (single-threaded, in-memory) | 100k–500k ops/sec |
| Nginx static reverse proxy | 50k–200k req/sec |
| Stateless HTTP service (Go/Rust, simple endpoint) | 20k–100k req/sec |
| Local disk I/O (NVMe sequential) | 1–3 GB/sec |
| Network throughput | ~1–1.25 GB/sec (10 Gbps NIC) |
| Working set in RAM | ~100 GB |
| Storage on one disk | several TB |

These are not benchmarks; they're rough ceilings to sanity-check an estimate.

**The rule:** if the estimate fits one box with headroom (say, 30%), distribution must be justified by something **other than throughput**:

- **High availability** — single box is a SPOF; replicas exist for failover, not for throughput.
- **Geographic latency** — users on another continent need a local replica.
- **Blast-radius isolation** — one tenant can't take down all tenants.
- **Backup / DR posture** — read replica doubles as backup target.

If none of those apply, **start with one box.** Add a warm standby for HA. Reach for horizontal scale only when a binding constraint (not "future-proofing") forces it.

## Worked example: notification service, 5M users, launch spike

The estimate reshapes the design before any box is drawn.

**Inputs:**
- 5M registered users.
- Launch event: each user gets 1 push + 1 email within a 5-minute window.
- Average payload: 200 bytes per push, 5 KB per email (HTML body).

**Burst peak QPS:**
- 5M notifications × 2 channels = 10M dispatches.
- Over 5 minutes (300 sec) = ~33,000 dispatches/sec.
- This is the **burst peak**, not steady state. Steady state outside launch events is likely 100×–1000× lower.

**Burst bandwidth:**
- Push: 33k/sec × 200 B = ~6.6 MB/s.
- Email body: 33k/sec × 5 KB = ~165 MB/s.

**Storage for delivery logs (90-day retention, audit trail):**
- 10M events × 90 cycles is wrong — launches are episodic, not daily. If we assume 30 launches/quarter at this size: 10M × 30 × 4 = 1.2B events/yr.
- × 500 B per log row × 2 (replicated) ≈ ~1.2 TB/yr. Fits comfortably on one Postgres instance with retention pruning.

**What this changes about the design:**

1. **Steady state fits one machine, easily.** A single Postgres + a single worker pool would absorb non-launch load.
2. **Burst is the binding constraint, not scale.** 33k/sec for 5 minutes is a *burst-absorption* problem, not a "build a distributed system" problem. The right answer is **queue-and-drain**: SQS or a Postgres outbox absorbs the burst, a fixed worker pool drains it at the rate downstream providers (APNs, FCM, SendGrid) will accept. The system processes 5M notifications in 10–15 minutes rather than 5 — that's acceptable for a launch announcement.
3. **Email bandwidth is the gnarly one.** 165 MB/s of email content suggests you don't send the body — you send a template ID and personalization, the email provider assembles. This is an estimate-driven design decision: the bandwidth number forced a protocol change.
4. **No need for Kafka.** SQS / RabbitMQ / Postgres-as-queue handles this with comfortable headroom. Kafka would be over-engineered for the steady state.

The estimate ruled out three architectures (sharded queue, multi-region active-active, Kafka cluster) before any of them got drawn. That's the point of Phase 2.
