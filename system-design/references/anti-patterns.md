# Anti-patterns

Load during **JUSTIFY** (greenfield) and **CRITIQUE** (review). Walk the catalogue against the proposed or existing design; each pattern that fires is a finding to challenge or fix.

These aren't refusals. They're prompts to **name the binding constraint that would force the choice**, or to step back to the simpler alternative.

## How to use this file

Each entry has the same shape:

- **Symptom** — what the design or proposal looks like when the anti-pattern is present.
- **Why it's an anti-pattern** — the cost, the failure mode, or the constraint that's being mishandled.
- **The question to ask instead** — what surfaces the real constraint (or its absence).

Walk every entry that's plausible for the design. The smell is fired by symptom alone; the action depends on the user's answer.

---

## Architectural over-reach

### Premature microservices

**Symptom.** "Let's split this into services" without an explicit team-coupling, deploy-coupling, or scaling-isolation reason. The system is a single team with one deploy cadence and modest traffic.

**Why it's an anti-pattern.** Microservices replace in-process function calls (nanoseconds, type-checked, transactional) with network calls (milliseconds, untyped JSON, eventually-consistent). The cost is permanent: every cross-service operation is now a distributed-systems problem. The benefit (independent deploy, independent scaling, team autonomy) only matters if those are actual constraints. For most teams, a modular monolith captures the benefits without the cost.

**Ask instead.** What coupling problem is the monolith causing? Is it team coupling (two teams stepping on each other in one repo)? Deploy coupling (deploys are slow or risky)? Scaling coupling (one component needs to scale 10× while others don't)? If none of those, the binding constraint is missing.

### Premature sharding

**Symptom.** "We need to shard the database" before exhausting vertical scaling, read replicas, and caching.

**Why it's an anti-pattern.** Sharding is a **one-way door** for the shard key. Picking it wrong is painful; reverting is enormous. Operational cost multiplies permanently (every operation may touch multiple shards; cross-shard transactions need sagas; resharding is its own project). A Postgres primary on a 16xlarge with PgBouncer + read replicas + Redis cache handles workloads most teams will never exceed.

**Ask instead.** What's the current write QPS, sustained? How does it project at 12 months? What's been tried (PgBouncer, instance size, replicas, caching)? If writes aren't the limit, sharding doesn't help.

### Distributed monolith

**Symptom.** Multiple services that must deploy together, share a database, or call each other synchronously in a tight chain. Splitting the code into services without splitting the operational concerns.

**Why it's an anti-pattern.** All the costs of microservices (network, observability, distributed debugging) without any of the benefits (independent deploy, independent failure). Often worse than a monolith because failures are now distributed and harder to reason about.

**Ask instead.** Can each service deploy independently without breaking the others? Does each service own its own data? If not, what would have to change for that to be true — and is doing that work worth it, vs. consolidating back into a modular monolith?

### Microservices for a small team

**Symptom.** A 3–5 engineer team running 10+ services.

**Why it's an anti-pattern.** Each service has operational surface (CI, deploy, monitoring, on-call, dependency upgrades). Three engineers can't operate ten services well; something will be neglected, and the neglected one is what pages at 3am.

**Ask instead.** What's the team-to-service ratio? Below ~1.5 services per engineer, operational quality suffers. Could the same logical separation live as modules in one service?

---

## Messaging and async over-reach

### Kafka for low-volume async work

**Symptom.** "Let's put Kafka in front of this" for ~hundreds or low thousands of messages per hour.

**Why it's an anti-pattern.** Kafka is a real distributed system to operate (cluster, partitions, ZooKeeper or KRaft, consumer offsets, schema registry). The operational cost is large; the workload doesn't earn it. Postgres `SELECT ... FOR UPDATE SKIP LOCKED`, SQS, or RabbitMQ handle this with a fraction of the cost.

**Ask instead.** What's the sustained message rate? Do you need replay/backfill? Do multiple independent consumers need the same stream? Below ~5–10k messages/sec sustained, or without replay/fan-out needs, Kafka's cost isn't earned.

### Async-as-default

**Symptom.** Every internal boundary is "we put it on a queue / log." Synchronous calls between services are treated as the rare case.

**Why it's an anti-pattern.** Each async hop adds latency, adds a failure mode (broker down, message lost, message duplicated, message out of order), and reduces observability (one request now spans multiple traces). Synchronous is the default; async is earned by a load shape that requires it.

**Ask instead.** Is the user literally waiting for this work? If yes, sync. Is there a real burst-absorption need or a real decoupling need? If no, the async layer is buying nothing and costing complexity.

### Dual-write for keeping stores in sync

**Symptom.** The design says "we write to Postgres and then write to Elasticsearch (or Redis, or Kafka)" without a transactional outbox or CDC.

**Why it's an anti-pattern.** The two writes will eventually fail independently. One will succeed, the other won't. The stores will diverge permanently. There is no manual fix that scales.

**Ask instead.** What's the sync mechanism? "Outbox" (write to PG transactionally with a row in an `outbox` table; a separate process publishes from outbox) or "CDC" (stream PG WAL into Kafka via Debezium, project into ES/cache) are the answers. "Synchronous dual-write" is not.

### Exactly-once delivery claims

**Symptom.** The design claims a broker provides "exactly-once delivery" and reasons from there.

**Why it's an anti-pattern.** Exactly-once delivery is not achievable in distributed systems. What IS achievable is **exactly-once processing** via idempotency. Designs that reason from "exactly-once" usually have a duplicate-processing bug waiting to happen.

**Ask instead.** Where are the idempotency keys? What's the dedup window? If a consumer sees the same message twice, what happens?

---

## Datastore over-reach

### Polyglot persistence without justification

**Symptom.** The design includes Postgres + Redis + Elasticsearch + a graph DB + a time-series DB.

**Why it's an anti-pattern.** Each additional store is a new operational pager, a new failure mode, and a new consistency boundary. The number of pairwise consistency boundaries grows quadratically with stores. Most "polyglot is more capable" designs reduce to "Postgres with extensions would have worked."

**Ask instead.** Count the consistency boundaries. For each pair of stores, how does data stay in sync (outbox / CDC / acceptable divergence)? For each store, what specific access pattern justifies it that Postgres + the right extension wouldn't handle?

### MongoDB because "schemas are restrictive"

**Symptom.** Document store chosen for greenfield with the rationale "we don't want a schema yet."

**Why it's an anti-pattern.** Six months in, the team realizes they DID want a schema; the validation logic ends up in application code (where it's harder to enforce and slower to evolve). Postgres JSONB gives most of the flexibility with the relational machinery still available.

**Ask instead.** Is the data genuinely document-shaped (entities with vendor-specific attributes, varying per row) or relational with some flexibility needs (most cases)? If the latter, JSONB on a Postgres column is the lower-cost path.

### Elasticsearch as system of record

**Symptom.** Primary data is written to Elasticsearch, not to a transactional store.

**Why it's an anti-pattern.** Elasticsearch is an index. It doesn't have transactional semantics; refresh latency is real; recovery from a corrupted index is rebuilding from the source of truth. If ES IS the source of truth, recovery is "hope."

**Ask instead.** What's the source of truth? ES should be a projection of it, rebuildable.

### Time-series DB at small scale

**Symptom.** Adopting InfluxDB / TimescaleDB / etc. for low-volume operational metrics or logs that could live in Postgres.

**Why it's an anti-pattern.** Another datastore to operate. Postgres with a partitioned table on `created_at` handles surprisingly large time-series workloads; specialized stores earn their place at high ingest rates or specific query shapes (downsampling, long retention with rollups).

**Ask instead.** What's the ingest rate? What's the retention? What queries actually run? Below ~10k inserts/sec sustained with simple time-range queries, Postgres handles it.

---

## Coordination and consensus

### Custom consensus / leader election

**Symptom.** The design says "we'll elect a leader using heartbeats" or "we'll coordinate via a custom protocol."

**Why it's an anti-pattern.** Distributed consensus has 50+ years of subtle bugs discovered the hard way. The Jepsen reports are the documented record. Rolling your own creates a class of bugs that surface only in production, under load, at the worst possible time.

**Ask instead.** Why not etcd, ZooKeeper, Consul, or a cloud-managed equivalent (DynamoDB, Spanner, etc.)? The answer should be "we genuinely cannot use any of those," not "we want to learn."

### Multi-region active-active without RTO/RPO forcing it

**Symptom.** "Let's go multi-region active-active for resilience."

**Why it's an anti-pattern.** Active-active is a fundamentally different system — every write is a cross-region coordination problem; conflict resolution is on the menu; cost is several times higher. Active-passive with a clear failover plan meets most resilience SLOs for a fraction of the cost.

**Ask instead.** What's the RTO (recovery time objective) and RPO (recovery point objective) that forces active-active? If RTO is "minutes" and RPO is "seconds," active-passive with regular replication usually meets it. Active-active is for "no measurable downtime" or "cross-region read latency under N ms."

---

## Resilience theater

### Retry without backoff, jitter, idempotency

**Symptom.** Calls are retried on failure but with no exponential backoff, no jitter, and no idempotency key.

**Why it's an anti-pattern.** A downstream blip becomes a retry storm: every caller retries at the same moment, multiplying load on the already-struggling downstream. Non-idempotent retries duplicate side effects (double payments, double sends).

**Ask instead.** What's the retry policy? Backoff multiplier and jitter range? Idempotency key? Cap on retries before failing?

### No bounded queues

**Symptom.** Internal queues (in-memory, broker, channel) have no maximum size.

**Why it's an anti-pattern.** Unbounded queue = memory leak with a friendly name. Under sustained overload, the queue grows until the process OOMs or the broker fills. The right answer is backpressure or load shedding — refuse work the system can't handle, rather than queueing it forever.

**Ask instead.** What happens when the queue is full? Drop? Shed at the boundary? Block the producer (with what timeout)? "We'd never overflow" is not an answer.

### Liveness and readiness conflated

**Symptom.** Health check fails when the DB is briefly unreachable, causing the orchestrator to restart the service.

**Why it's an anti-pattern.** Liveness is "is the process alive" (restart if not). Readiness is "is this instance ready for traffic" (remove from LB if not). Combining them turns a transient DB blip into a restart loop, which destroys in-flight work and amplifies the original problem.

**Ask instead.** What does the liveness probe check? What does the readiness probe check? They should be different.

### Untested failover

**Symptom.** "We have a warm standby" or "we have multi-AZ" but no one on the current team has actually exercised the failover.

**Why it's an anti-pattern.** Untested failover is not failover. Database promotions have edge cases (replication lag, fencing, DNS, connection pool config) that surface only when you actually do the failover. The first time should not be 2am during an incident.

**Ask instead.** When was the failover last actually executed? Who ran it? Is there a runbook? Does the runbook still match reality?

### Synchronous dependency without timeout

**Symptom.** A cross-process call has no explicit timeout. The default is effectively "wait forever."

**Why it's an anti-pattern.** A slow dependency now takes the calling service down too. Cascading failure follows. Timeouts are non-optional.

**Ask instead.** What's the timeout on every cross-process call? How was it picked? Is it tighter than the outer request budget?

### No degradation strategy / no MVF

**Symptom.** The design has no statement of what happens when a non-critical dependency is down. Implicit answer: the user gets a 500.

**Why it's an anti-pattern.** Every dependency will be down sometime. Without a defined minimum-viable-function, the user-visible failure is "site is broken" rather than "recommendations are unavailable, everything else works."

**Ask instead.** For each user-visible flow, what's the minimum viable function? Which dependencies are on the must-work side and which can degrade gracefully?

---

## Premature optimization

### Caching everything

**Symptom.** The design includes a cache layer in front of every read, including reads that the underlying store already handles in <1ms.

**Why it's an anti-pattern.** Caching adds a layer of bugs (invalidation, stampede, hot key, cold start) for a latency win that may not exist. If the underlying read is already fast enough, the cache is pure cost.

**Ask instead.** What's the uncached latency of this read? What's the cache lookup latency? If the gap isn't material, the cache shouldn't exist.

### "Future-proofing" for hypothetical scale

**Symptom.** Architecture designed for 100× current load, when 10× would be aggressive.

**Why it's an anti-pattern.** Projections are wrong, often by an order of magnitude in some direction. Designing for projected scale means paying complexity cost now for a future that may never arrive. The right rule: build for current scale + one order of magnitude, no more.

**Ask instead.** What's the current scale? What's a realistic 12-month projection? What's the cost of being wrong by one order of magnitude in either direction?

### Resume-driven architecture

**Symptom.** The design includes a technology because it's interesting, fashionable, or career-relevant, not because the constraint demands it.

**Why it's an anti-pattern.** Operational cost is paid by the team forever; the resume benefit accrues to one person. Novel tech without operational maturity creates incidents.

**Ask instead.** If this were already running on Postgres + Redis + the standard cloud primitives, would we propose switching off them? If the answer is no, the choice is resume-driven.

---

## Process and discipline

### Decisions without ADRs

**Symptom.** Significant architectural choices are made and forgotten. New team members ask "why did we do it this way?" and no one remembers.

**Why it's an anti-pattern.** Implicit decisions don't survive team turnover. The rationale evaporates; the choice persists. Future decisions get made without the original context.

**Ask instead.** Where's the ADR for this? If a one-way-door choice doesn't have a written record, it should.

### ADRs without sacrifices

**Symptom.** The ADR's "Consequences" section is all positives. "We chose X because it's better in every way."

**Why it's an anti-pattern.** Every choice has a sacrifice. An ADR without a named sacrifice didn't analyze the choice; it advocated for it.

**Ask instead.** What's the sacrifice? What does this cost us? What would force a reversal?

### "We'll handle invalidation later"

**Symptom.** A cache is added with no plan for how stale data gets refreshed.

**Why it's an anti-pattern.** Cache invalidation is famously hard. "Later" means "never" until a customer-visible bug forces it. Plan it at design time.

**Ask instead.** How does an entry leave the cache when the underlying data changes? TTL? Event-driven invalidation? Versioned keys? Pick one explicitly.

### Designing for the happy path only

**Symptom.** The architecture describes how things work when everything's up. No paragraph on what happens when a dependency is down or slow.

**Why it's an anti-pattern.** The happy path is the easy part. The failure modes are where systems live or die. A design without explicit failure-handling for every dependency has implicit failure-handling, which is "we'll figure it out in the incident."

**Ask instead.** Per dependency: slow, down, wrong — what does the system do? What's the blast radius? What's the runbook?

---

## How to deliver findings from this catalog

When a pattern fires in a design (greenfield JUSTIFY or review CRITIQUE):

1. **Name the pattern.** "This looks like premature sharding."
2. **State why it's firing.** Quote the specific design choice that triggered the smell.
3. **Ask the question.** Not "you're wrong"; the question that surfaces the constraint.
4. **Wait for the answer.** If the user has a binding constraint, the ADR records it and moves on. If they don't, the choice gets revised.

This is a conversation, not a refusal. The catalog exists to make sure the conversation happens before the code ships.
