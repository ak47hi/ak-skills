# Patterns

Load when entering **Phase 5 (Scale the bottleneck)**. Goal: find the **single binding bottleneck** and apply the smallest pattern that resolves it. Scaling everything is over-engineering. Each step below has a binding constraint that justifies it; if that constraint hasn't been hit, the step is premature.

## Scaling in order of reach

Step in this order. **Do not skip steps without naming the constraint that forces the skip.**

```
1. Vertical (bigger box)
2. Horizontal stateless (more replicas behind a load balancer)
3. Read replicas (read-heavy workloads)
4. Caching (read-heavy with locality)
5. Sharding (write-bound or per-tenant isolation)
```

### 1. Vertical

- Move to a bigger instance. CPU, RAM, NIC, SSD all scale together.
- **When it fails:** single-instance cost curve steepens (4xlarge → 16xlarge → bare metal); single-box SPOF doesn't meet availability SLO; one machine has a hard ceiling on the resource that actually limits you (writes per second on a single Postgres primary, for instance).
- **Don't skip this.** Vertical is the cheapest in engineering time. A 32-vCPU Postgres absorbs an enormous range of small-to-medium workloads.

### 2. Horizontal stateless

- Multiple replicas of the service behind a load balancer. State lives in the database, not in the service.
- **Constraint to make this work:** the service is genuinely stateless. Sessions in process memory break this; sticky sessions paper over it; the right fix is to externalize state to Redis or the DB.
- **When it fails:** the bottleneck moves to the database. The next step is replicas + caching, not yet sharding.

### 3. Read replicas

- One leader takes writes, N followers serve reads.
- **When to reach:** read:write ratio is heavily read (90:10 or more); reads are tolerant of seconds of staleness (most browsing, search, recommendations).
- **Hazards:**
  - **Replication lag:** followers fall behind under write load. Read-your-writes breaks (`estimation.md`'s replication-lag-bug section).
  - **Failover:** promoting a replica requires DNS / connection-pool reconfiguration and there's a window of write outage.
  - **Some queries still can't go to replicas:** anything with `FOR UPDATE`, anything that immediately reads back a just-written row.
- **When it fails:** writes are the bottleneck, not reads. Adding replicas doesn't help.

### 4. Caching

- Layer a fast store (Redis, Memcached, CDN) in front of the database.
- **When to reach:** there's a small hot set of frequently-read data; reads dominate; cache hits can absorb most of the load.
- **Critical:** caching is the second-line response, not the first. If you can avoid the read entirely (better query, pagination, indexed lookup), do that. Caching adds a layer of bugs.
- See "Caching" section below for placement and hazards.

### 5. Sharding

- Partition the data across multiple writable nodes. See `datastores.md` for shard-key strategies.
- **When to reach:** writes have exceeded what a single primary handles even after vertical scaling, partitioning the table, and writing-through-cache.
- **Cost, permanently:** every cross-shard query is a fan-out. Every cross-shard transaction is a saga or a two-phase commit. Resharding (changing shard count) is operationally expensive. **Shard key is a one-way door.**
- **Most teams shard too early.** Read replicas + caching usually defer sharding by years.

## Caching

### Placement layers

| Layer | What it caches | Latency | Notes |
|---|---|---|---|
| Client / browser | Per-user state, assets, API responses with proper headers | ~0 (already there) | Cache-Control / ETag / immutable assets. The cheapest cache. |
| CDN (edge) | Static assets; sometimes API responses | ~10 ms (POP-local) | Use for global users; invalidation is the headache. |
| API gateway / service-local | Hot lookups, auth tokens | ~1 ms (in-process) | Process-local; restart drops it; per-replica divergence. |
| Distributed cache (Redis, Memcached) | Shared hot set across replicas | ~1 ms (same DC) | One source of truth across the fleet. |
| Database buffer pool | Recently-accessed pages | ~0–100 µs | Free, already happening; size the RAM appropriately. |

A "warmed buffer pool" is a cache. Tuning Postgres `shared_buffers` is often cheaper than adding Redis.

### Strategies

- **Cache-aside (lazy load).** App reads cache; if miss, reads DB, populates cache. Most common. Hazard: thundering herd on cache cold start or eviction.
- **Write-through.** App writes to cache and DB in the same call; DB is source of truth. Hazard: latency penalty on writes; if cache write fails, you have divergence.
- **Write-behind (write-back).** App writes to cache; cache flushes to DB asynchronously. Hazard: data loss if the cache dies before flushing. Reserved for low-durability data (counters, view tracking).
- **Refresh-ahead.** Cache proactively refreshes hot entries before they expire. Mitigates stampede; adds complexity.

### Hazards (every cache has these)

- **Invalidation.** Phil Karlton's joke — "There are only two hard things in Computer Science: cache invalidation and naming things." It is, in fact, the hard one. Mitigations: TTLs (accept some staleness), event-driven invalidation (you publish a "user-X updated" event and every cache layer purges), versioned keys (key = `user:42:v17`, so old versions go cold and get evicted).
- **Stampede / thundering herd.** A popular key expires and 10k requests miss simultaneously, all hitting the DB. Mitigations:
  - **TTL jitter:** randomize TTLs ±10% so keys don't expire in lockstep.
  - **Single-flight / request coalescing:** only one request per cache key may go to the DB; others wait for the result.
  - **Soft TTL with background refresh:** serve the stale value while a single async refresh runs.
- **Hot key.** One key gets thousands of QPS while others are cold. The cache node holding it saturates. Mitigations: replicate the hot key across multiple cache nodes (read from any); use local in-process cache layered on top of Redis for the hottest keys; rate limit reads of the key.
- **Cold start.** Cache is empty (deploy, restart, eviction storm). The DB takes the full load. Mitigations: pre-warm with critical keys before serving traffic; rolling restart so only a fraction of cache is cold at once; rate limit cold-start traffic until warm.

### "Don't cache what you can compute fast enough"

If the underlying query is < 1 ms uncached, adding a cache often makes the system worse (cache lookup is also ~1 ms, plus a class of bugs). Cache the expensive thing, not everything.

## Async and messaging

### Sync vs async per boundary

Default boundaries to **sync**. Move a boundary to **async** when:

- The downstream work is slow and the upstream caller doesn't need the result immediately.
- The downstream work can fail without the user noticing (and you have a retry mechanism).
- The upstream system needs to absorb a burst that the downstream can't handle at full rate.

**Rule:** keep async off the synchronous critical path of a user-visible request. If the user is waiting for the response, the work is sync. If you can return "OK, we'll do it" and process later, it's async.

### Queue vs log

- **Queue (RabbitMQ, SQS, ActiveMQ):**
  - Messages are consumed by one of many workers; once acknowledged, deleted.
  - Use when work items are independent and the system just needs to process each one once.
  - Ordering is per-queue or weak; replays are not the model.
- **Log (Kafka, Kinesis, Pulsar, Redpanda):**
  - Messages are appended to a partitioned log; multiple consumers each track their own offset.
  - Use when: multiple downstream systems consume the same stream; you need replay for backfill/recovery; ordering within a partition matters.
  - Operationally heavier than a queue. Pick when the replay or fan-out is genuinely needed, not by default.

### What async buys

- **Burst absorption.** A spiky producer + a flat-rate consumer pool smooths load on downstream systems.
- **Decoupling.** The producer doesn't need to know who consumes; consumers come and go.
- **Retry / dead-letter.** Failed work is retried automatically and parked when it can't succeed.

### What async costs

- **Operational surface.** A broker is a service to run, monitor, upgrade, page on.
- **Ordering hazards.** Without a partition key, messages can be reordered. "Exactly-once delivery" is a marketing claim; **exactly-once *processing*** is achievable through idempotency (see below), not through the broker.
- **Visibility.** Sync errors surface immediately; async errors surface eventually, often via DLQ inspection.
- **Backpressure complexity.** If the broker fills up, the producer must choose: block (defeating async), drop (lose data), or shed somewhere upstream.

### Async-as-default smell

If every internal boundary is "we put it on Kafka," the design is probably wrong. Async layers add latency between phases of work; each one is a place messages can be lost, reordered, or duplicated. Use async where the load shape genuinely requires it.

## CQRS and event sourcing (adopt deliberately)

Both solve real problems and create severe new ones. Adopt only when the binding constraint forces it.

### CQRS (Command Query Responsibility Segregation)

- Separate write model and read model. Commands mutate the write model; queries read from a separate read model populated asynchronously from writes.
- **When to reach:** writes and reads have fundamentally different scaling profiles (low-volume writes, high-volume complex reads); the read model needs a different shape (denormalized, search-indexed) than the write model.
- **What it costs:** two models to maintain; replication lag is now user-visible; debugging crosses the write→read boundary.
- **What to budget for:** sync mechanism (outbox or CDC), monitoring of read-model lag, runbook for "read model is stale, how do we rebuild."

### Event sourcing

- Persist the sequence of events that changed state, rather than the current state. Rebuild current state by replaying events.
- **When to reach:** auditability is a hard requirement (financial systems, healthcare); the domain genuinely is event-shaped (orders move through statuses; the history matters as much as the present); time-travel debugging would meaningfully improve operations.
- **What it costs:** schema evolution is hard (old events live forever); snapshots are required for performance; eventual consistency is now the default everywhere; querying "what's the current state of X" requires either snapshot or replay.
- **What to budget for:** event versioning strategy, snapshot policy, replay tooling, query-side projections (this is CQRS, so add CQRS's costs too).

**The warning:** event sourcing is fashionable and almost always wrong for general application state. The audit-log pattern (regular DB + an append-only events table for history) gives you most of the audit benefit with none of the complexity.

## Idempotency

**"Exactly-once delivery"** is a fantasy. Networks fail; retries duplicate. **"Exactly-once processing"** is achievable through idempotency.

### Idempotency keys

- Each request carries a unique key (UUID, client-generated). The server records the key on first processing. Subsequent requests with the same key return the cached result without re-executing.
- **Where to use:** any mutating operation that the client might retry (payment, order placement, queue consumers).
- **Storage:** the key + result lives in a fast store (Redis with TTL, or a DB table) with a TTL longer than the maximum possible retry window.

### Dedup windows

- For at-least-once message processing: the consumer records processed message IDs and skips duplicates.
- **TTL discipline:** the dedup store must outlive the broker's max-redelivery window. A 24h broker visibility-timeout + 7-day retry budget means the dedup TTL is at least 7 days.

### Outbox pattern (re-emphasized)

- Single source of truth for the side-effect-triggering event (the row in the `outbox` table) means the side effect (publish to broker, write to second store) is retried until it succeeds, and the original transaction is the only place that can "create" the side-effect intent. Dual-write divergence is eliminated.

### Idempotency at every async boundary

Every async consumer should be written assuming it will see duplicates. If "process this twice" is a bug, the consumer needs an idempotency key or dedup mechanism. This is non-negotiable for at-least-once systems (which is most of them).

## Coordination primitives

### Load balancing

- **L4 (TCP).** Round-robin or least-connections; doesn't inspect payload. Fast, simple, no protocol awareness. Use for plain TCP services.
- **L7 (HTTP).** Routes by header, path, method. Use for HTTP services where routing matters (`/api/v1/` to one set, `/admin/` to another).
- **Consistent hashing.** For stateful services (cache nodes, sharded services), the load balancer hashes the request key and picks a backend deterministically. Adding/removing backends moves only a fraction of keys. Used by Memcached clients, Cassandra coordinators, CDN edge routing.

### Rate limiting

- **Token bucket.** Allows bursts up to bucket size; refills at a steady rate. Most common; allows brief spikes within an overall budget.
- **Leaky bucket.** Smooths bursts to a strict steady rate. Output is constant; input bursts queue up to bucket size.
- **Sliding window log / counter.** Counts requests in the past N seconds. More accurate than fixed windows; more expensive (per-request state).

Rate limits live at the **edge** (API gateway, ingress) for incoming traffic. They also live at internal boundaries to prevent one client from saturating a downstream dependency.

### Consensus and leader election

- **Use battle-tested implementations.** Raft, Paxos, multi-Paxos. The reference implementations are etcd, ZooKeeper, Consul. Cloud-managed equivalents: AWS DynamoDB streams, Spanner, CockroachDB.
- **Never roll your own.** Distributed consensus has 50+ years of subtle bugs discovered the hard way. The Jepsen reports are required reading before you think otherwise.
- **What you actually use it for:** leader election (one node coordinates), lock service (distributed mutex), config that needs strong consistency (feature flags as the source of truth, cluster membership).

If a design includes "we'll just elect a leader using heartbeats," replace it with etcd or ZooKeeper.

## Bottleneck-finding discipline

Phase 5's job is to find *the* bottleneck, not list scaling options. The output should be:

1. **The binding resource.** What's the one thing that saturates first under projected load? (DB writes, NIC bandwidth, working set vs RAM, worker pool size, the rate-limited downstream API.)
2. **The smallest fix.** From the order-of-reach list, the next step that addresses it.
3. **What the fix doesn't fix.** Honest about which other constraints remain.
4. **What forces the next step after.** What signal in production would say "now we need the next pattern."

That's it. Anything beyond that is premature.
