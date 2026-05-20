# Failure modes

Load when entering **Phase 6 (Failure modes)**. Goal: for each external dependency, ask **slow / down / wrong** and define the system's behavior in each case. Every dependency is a potential cliff; the design must say what the system does at the edge.

The defining sentence: **untested failover is not failover.**

## Failure taxonomy

The named patterns that recur in production post-mortems. Build the design to defend against each one that's plausible for the workload.

### Cascading failure

One service slows down. Callers' requests pile up; they retry; the slow service slows further or crashes. The failure radiates outward through retry chains until the whole system is on fire.

**Where it starts:** any service without timeouts, or with retry without backoff, or with insufficient backpressure.

### Retry storm

A downstream blip causes every caller to retry simultaneously. The downstream gets `N` retries on top of the natural request rate the moment it recovers, immediately re-crashes.

**Where it starts:** clients without jitter in retry backoff; clients retrying non-idempotent operations.

### Thundering herd

Many clients wake up at the same moment and all hit the same resource. Variant: cache stampede (all clients miss the same expired key); cron-like wake-up storms; reconnect storms after a network blip.

**Where it starts:** synchronized timers; aligned TTLs; no backoff on reconnect.

### Hot shard / hot key

One partition (or one key in a partitioned system) takes a disproportionate share of traffic and saturates while peers are idle. Common when shard key correlates with usage (sharding by user ID when one user is a celebrity).

### Resource exhaustion

The system runs out of one finite resource: file descriptors, database connections, thread/goroutine count, ephemeral ports, memory, disk space, log volume. The other resources are healthy but the saturated one stops the whole system.

### Slow / gray dependency

A dependency isn't down — it's degraded. Returns successfully but slowly. Callers wait, accumulate, exhaust their own thread pools. Fail-stop is much easier to handle than fail-slow.

### Split brain

Two halves of a system, partitioned from each other, both think they're the leader. Both accept writes. Reconciliation when the partition heals is impossible without data loss or merge conflicts.

**Where it starts:** custom leader-election; multi-leader replication with no conflict policy; failover scripts that promote without fencing the old leader.

### Poison message

A message in a queue can't be processed (deserialization error, schema mismatch, application bug on this specific payload). Without a dead-letter queue, the consumer retries forever and head-of-line-blocks the queue.

### Head-of-line blocking

The slow request at the front of a queue blocks everything behind it. Common in single-threaded consumers; common in HTTP/1.1 pipelines.

### Backpressure overflow

The system can't slow producers when consumers fall behind. The queue grows unbounded, the broker fills up, eventually the producer is also affected (or the broker dies).

### Snowball / death spiral

The system has a positive feedback loop under stress: stress causes more stress. Example: GC pauses → request latency rises → connections accumulate → memory pressure increases → more GC pauses. Once started, hard to stop without intervention.

## Mitigations

The catalogue. Apply each to the right place.

### Timeouts on every cross-process call

- **Every** call to another process or network resource has an explicit timeout. No infinite waits. Ever.
- Set the timeout based on **the slowest acceptable behavior** for that dependency, not its happy-path latency.
- **The timeout cascade:** if the API has a 5 s budget and calls 4 services, each downstream call should time out well before 5 s (so the API can still respond). Inner timeouts are tighter than outer.

### Retry with exponential backoff and jitter

- Retry only **idempotent** operations. Retrying a non-idempotent operation (a payment, an order placement without an idempotency key) creates duplicate effects.
- **Exponential backoff:** wait `2^n` seconds before retry `n`. Don't retry tightly.
- **Jitter:** randomize the delay (e.g., uniform between 0 and `2^n`). Without jitter, all callers retry at exactly the same moment — a retry storm.
- **Cap the retries** (typical: 3–5). After the cap, fail fast and surface the error.
- **Don't retry on 4xx** unless it's explicitly retryable (429 with Retry-After). 400/401/403/404 retries are pure overhead.

### Circuit breaker

- Wraps a downstream call. States: **closed** (calls pass through, errors counted); **open** (calls fail fast without hitting the downstream, gives it time to recover); **half-open** (a few calls allowed through to check if it's recovered).
- **When to open:** error rate over a window exceeds a threshold (e.g., 50% errors in the last 100 calls).
- **What it prevents:** cascading failure, retry storms, wasted latency on doomed calls.
- **Recovery:** after a timeout, half-open lets a few requests through. If they succeed, close; if they fail, re-open.

### Bulkhead

- Isolate resources per dependency. If Service A and Service B both consume the same thread pool, Service A's slowness exhausts the pool and starves Service B.
- **Per-dependency thread pools / connection pools / rate-limit budgets** keep one bad neighbor from sinking the system.
- Named after ship bulkheads: a hull breach in one compartment doesn't sink the ship.

### Backpressure

- Signal upstream to slow down when the downstream is at capacity. Mechanisms: TCP-level (slow ACKs); HTTP-level (429 with Retry-After); message-broker-level (block / nack); application-level (reject new requests with 503).
- **The honest answer to overload is to refuse traffic**, not to queue forever. Queueing forever hides the problem until it explodes.

### Load shedding

- Drop low-priority work before high-priority work degrades. Examples: serve cached results to anonymous users while preserving fresh data for logged-in users; drop non-essential telemetry first; defer batch jobs.
- **Decide priorities at design time, not during the incident.**

### Dead-letter queue

- A "side queue" for messages that consistently fail to process. Move the poisonous message off the main queue; an operator inspects it later.
- **Discipline:** after N retries, the message must go to DLQ. **Without a DLQ, a poison message head-of-line-blocks the queue forever.**
- **Monitoring:** the DLQ depth is an alert. A growing DLQ means real bugs are silently accumulating.

### Idempotency

- Re-emphasized from `patterns.md`. Every consumer of at-least-once delivery (which is most consumers) needs an idempotency key or a dedup mechanism. This is what makes retries safe; without it, retries break invariants.

### Hedged requests

- For latency-critical reads, send the request to two replicas, take whichever responds first. Cancels the slower one.
- **Useful when:** the dependency has occasional tail-latency stragglers and you can afford ~2× the request rate to mask them.
- **Cost:** doubles the request rate on a slow day. Not a default; reserved for specific latency budgets.

### Bounded queues

- Every queue has a maximum length. When full, refuse new entries (backpressure) rather than grow unbounded.
- An unbounded queue is a memory leak with a friendly name.

### Health checks (deep enough to mean something)

- **Liveness:** is the process running? Restart if not. Should not check dependencies — that turns one downstream failure into a service restart loop.
- **Readiness:** is this instance ready to take traffic? *This* one can check dependencies (DB connection, cache reachability). Failing readiness removes the instance from the load balancer pool without restarting it.
- **Bad pattern:** combining the two so a DB blip causes a restart. The DB is fine; the service didn't need restarting.

### Timeouts at multiple layers (defense in depth)

- Client timeout > load balancer timeout > server request timeout > downstream call timeout > database query timeout. The outermost should be larger than the sum of the innermost. Otherwise the inner work continues after the client gave up (wasted work, potential consistency bugs).

## Degradation strategy

When something breaks, the system shouldn't fall over. It should **degrade**.

### Minimum viable function (MVF)

For every user-visible flow, define the smallest version of itself that still works:

- **Checkout** must work without recommendations, without promotions, without recent-views, without fraud-score live lookup (use a cached score). It must NOT work without inventory availability, without payment authorization, without order persistence.
- **Feed** must work without personalization (show chronological), without trending sidebar, without ads. It must NOT work without the post-fetch itself.
- **Search** must work without faceted filters, without spell-correction, without recommendations-alongside. It must NOT work without the basic search query against the index.

**Discipline:** when each dependency goes down, the system silently falls back to MVF. The user notices a less-good experience, not a 500.

### Fallback hierarchy

- **Cached value.** Last good response from the dependency.
- **Default value.** A reasonable static answer (e.g., "0 results" for a recommender that's down).
- **Empty / collapsed UI.** Hide the broken section; show the rest.
- **Read-only mode.** Disable writes; serve reads.
- **Maintenance page.** The last resort.

The design should explicitly say, per dependency: "if this is down, the system shows X." Not "we'll figure it out in an incident."

### Don't fallback to wrong data

For correctness-critical operations (payments, inventory decrement, security checks), failing is correct. **Don't approve a payment because the fraud service is down.** The fallback is a 503, not a free pass.

## Per-dependency resilience checklist (Phase 6 walk)

For each external dependency in the architecture, answer:

1. **Timeout?** What's the explicit timeout? How was it picked?
2. **Retry policy?** Idempotent? With backoff + jitter? Capped at how many retries?
3. **Circuit breaker?** When does it open? When does it close?
4. **Bulkhead?** Is this dependency's failure isolated from others (separate pool, separate budget)?
5. **Idempotency?** If the dependency may double-process, does the system handle that?
6. **Fallback?** What does the system do when this dependency is down? Cached value? Default? Empty? Read-only?
7. **MVF?** Is this dependency on the "must work" or "nice to have" side of the user-visible flow?
8. **Monitored?** Latency p50/p99, error rate, circuit-breaker state — is it on a dashboard?
9. **Alerting?** Who gets paged when this dependency degrades? What's the runbook?
10. **Runbook tested?** Has the failover been **actually executed** in a game-day or chaos exercise? Untested failover is not failover.
11. **Blast radius?** If this dependency fails, what percentage of user traffic is affected?
12. **Recovery procedure?** When the dependency comes back, does the system reconnect cleanly, or does it need an operator?

Walking this for every dependency surfaces the holes. Most "we're resilient" designs are resilient on 3 of these 12, not all.

## Common failure mode → mitigation map

A quick lookup. Each row's mitigation is necessary but not always sufficient — most real defenses combine multiple.

| Failure mode | Primary mitigation |
|---|---|
| Cascading failure | Timeouts + circuit breakers + bulkheads |
| Retry storm | Exponential backoff with jitter; cap retries |
| Thundering herd | TTL jitter; single-flight; staggered restarts |
| Hot shard / hot key | Re-shard within the hot partition; replicate hot keys |
| Resource exhaustion | Bounded queues; bulkheads; quotas per tenant |
| Slow dependency | Circuit breaker (opens on latency, not just errors); hedged requests for read paths |
| Split brain | Use a proper consensus system (etcd, ZooKeeper); fence old leaders before promoting new |
| Poison message | Dead-letter queue; retry cap |
| Head-of-line blocking | Parallel consumers; per-key ordering only when required |
| Backpressure overflow | Bounded queues; backpressure signals; load shedding |
| Snowball / death spiral | Circuit breakers; load shedding; rate limits; rollback to last known good |

## When the design says "we'll handle it manually"

Red flag. "We'll have an on-call engineer run the failover script" is fine **if** the script exists, has been tested in the last quarter, and the on-call engineer has run it before. Otherwise, the design has a hole.

**Untested failover is not failover.** Repeating because it's the most common production lie.
