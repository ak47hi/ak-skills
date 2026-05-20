# Tradeoffs

Load when entering **Phase 7 (Justify)**. Goal: produce an ADR-style record per significant choice. Every record names the binding constraint, the alternatives considered, and the sacrifice accepted. "Because it's standard" is not a justification; the constraint and the sacrifice are.

## The core tradeoff axes

Most architectural decisions sit on one of these axes. Naming the axis is the first step toward reasoning about the decision rather than asserting it.

### Consistency vs availability/latency

Stronger consistency requires coordination; coordination costs latency under normal operations and availability during partitions. Linearizable reads cost extra round-trips; multi-region writes cost extra cross-region latency.

The decision is **per operation**, not per system. Payment authorization wants linearizable. Trending-now is fine eventually consistent.

### Latency vs throughput

Pipelining, batching, and async processing raise throughput at the cost of per-request latency. A single user request sees worse latency in a batched system than in a per-request one; the system as a whole handles more.

Optimize for whichever the user notices. A search box optimizes for latency; an ETL job optimizes for throughput.

### Read-optimized vs write-optimized

A B-tree index on every column makes reads fast and writes slow (every write updates every index). A columnar store makes analytical reads fast and individual writes slow. Append-only logs are write-fast, read-slow without secondary structures.

The dominant access pattern picks the side of the axis. A 95:5 read:write system optimizes reads aggressively; the 5% of writes pay for it.

### Coupling vs cohesion (simplicity vs flexibility)

A monolith has high cohesion (logic is together) and high internal coupling (everything is in one process). Microservices reverse this: low coupling between services, lower cohesion per service.

The tradeoff: simplicity (one process to debug, one deploy) vs independent flexibility (services scale and deploy independently, teams own their slice).

**The right answer is usually a modular monolith** until a team-coupling or deploy-coupling constraint forces splitting. Microservices for "future-proofing" are over-engineering.

### Space vs time

Caches, denormalization, materialized views, search indexes: trade storage (and the cost of keeping the redundant copies in sync) for faster reads.

A precomputed leaderboard avoids running the query every read; the cost is recomputing it on each relevant write and storing the result.

### Cost vs reliability

Three nines costs less than four nines costs less than five nines, roughly logarithmically. Each additional nine is a new pattern (warm standby → active-passive → active-active → multi-region active-active) and a new operational burden.

**Don't aim for nines the business doesn't need.** Internal admin tools at 99.5% are fine. User-facing APIs at 99.95% are fine. Payment systems may need more. Match the SLO to the cost of being wrong.

### Boring vs novel tech

Postgres, Redis, Linux, HTTP, JSON, JWT. These have known operational characteristics. Their bugs are documented; their failure modes are familiar; on-call engineers know how to recover them.

Novel tech (new datastore, new framework, new programming model) has unknown failure modes, immature tooling, and a smaller community. Adopt only when the binding constraint genuinely forces it, and budget for the operational learning curve.

**Boring is a feature.**

### Time-to-market vs scalability

Building for current scale ships faster. Building for projected scale takes longer and is wrong as often as it's right (the projection is usually off by 10× in some direction).

**Build for current scale + one order of magnitude.** Beyond that, you're guessing.

## The 5-step method for reasoning about a tradeoff

For any architectural decision, walk these five steps. The output is the body of an ADR (next section).

### 1. Name the axis

Which tradeoff is this? "We're trading consistency for availability." "We're trading operational simplicity for write throughput." If you can't name the axis, you're not reasoning about a tradeoff — you're picking a tool.

### 2. State the binding constraint

The one constraint that doesn't bend. "Payment authorization requires linearizable consistency — anything less is incorrect." "The team is two engineers; we cannot run Cassandra." "p99 must be under 200 ms; cross-region synchronous calls are off the table."

A binding constraint is **specific** and **measurable**. "We need it to be fast" is not binding. "p99 must be under 200 ms" is.

### 3. List 2–3 realistic alternatives

Not strawmen. The alternatives are real options a thoughtful person would consider for this constraint. "We could pick MongoDB or Postgres" — yes. "We could pick Postgres or write our own DB" — no.

If you can't think of a real alternative, the decision is forced and doesn't need an ADR.

### 4. Pick and state the sacrifice explicitly

"We pick Postgres. The sacrifice is that horizontal write scaling will require sharding when we exceed ~10k sustained write QPS, which we don't expect to hit for 18 months."

The sacrifice is **named**, not hidden. If a decision has no sacrifice, you're either wrong (every choice has a cost) or the decision wasn't significant.

### 5. Note reversal cost — one-way or two-way door

- **Two-way door:** the decision can be reversed cheaply if you turn out to be wrong. Caching choices, framework versions, internal API shapes.
- **One-way door:** the decision is expensive to reverse. Shard key. Wire format on persisted data. Identifier scheme (UUID vs auto-increment, exposed to clients). Multi-region deployment.

**Spend more deliberation on one-way doors.** A two-way door is reversible; pick the simpler option and move on. A one-way door justifies more analysis and more reviewers.

State which kind of door this is and what would force a reversal.

## ADR template

Architecture Decision Records: short, durable, immutable. One ADR per significant decision; minor / two-way-door / fully reversible decisions don't need one.

```markdown
# ADR-NNN: <decision title>

Status: Proposed | Accepted | Superseded by ADR-MMM
Date: YYYY-MM-DD
Owner: <name or team>

## Context

What's the situation that demands a decision? What changed, what's the
binding constraint, what's the scope of the decision? 2–4 short paragraphs.
Numbers where relevant.

## Decision

What we're doing. One paragraph. Imperative voice. No hedging.

## Alternatives considered

For each alternative (2–3 of them):

- **<Alternative name>.** What it is. Why we didn't pick it — name the
  constraint it failed to satisfy, not a vague preference.

## Consequences

- **Positive.** What gets easier or better as a result.
- **Negative / new failure modes.** What's now harder, riskier, or
  newly possible to break. Be specific — "may have replication lag
  bugs" is more useful than "may have issues."
- **What to monitor.** The metrics or signals that would tell us
  this decision is working or breaking. The on-call dashboard
  rows this decision adds.
- **Reversal cost.** One-way door or two-way door? If one-way,
  what would force a reversal and what would the reversal involve?

## Open questions

Things we deferred. Each open question has a deadline or a trigger
("revisit when write QPS exceeds 10k"). Open questions without
triggers rot.
```

### Filling it out — concrete example

```markdown
# ADR-007: Use Postgres as the queue for background jobs

Status: Accepted
Date: 2026-05-20
Owner: Platform team

## Context

We need a job queue for background work: email sends, image
processing, webhook deliveries. Current peak is ~200 jobs/hour;
12-month projection is ~2k jobs/hour. The team has deep Postgres
operational experience and no Kafka or RabbitMQ experience. We
already run Postgres for the application database.

## Decision

Use a Postgres table with `SELECT ... FOR UPDATE SKIP LOCKED` as
the queue. Workers poll the table at 1s intervals. Failed jobs
move to a dead-letter table after 5 retries.

## Alternatives considered

- **AWS SQS.** Managed, cheap, no extra operational surface. We
  didn't pick it because we don't currently use AWS for queueing
  and would prefer to avoid adding a vendor surface for a workload
  this small. Reconsider at >10k jobs/hour or if cross-region
  delivery becomes a requirement.
- **Kafka.** Wildly overpowered for ~2k jobs/hour. Operational
  cost (cluster, ZooKeeper or KRaft, partition management) is not
  justified by the workload.
- **RabbitMQ.** A reasonable fit, but adds an operational service
  we don't currently run and would have to learn under load.

## Consequences

- **Positive.** Zero new operational surface. Job state is
  transactionally consistent with application state. Familiar
  tooling and debugging.
- **Negative / new failure modes.** Postgres write load increases
  by job-write QPS; we must monitor primary write load. Long-running
  transactions in workers can block VACUUM and cause table bloat —
  jobs must commit promptly. `SKIP LOCKED` requires Postgres 9.5+
  (we're on 15, fine).
- **What to monitor.** Queue depth (rows where status='pending').
  Worker lag (oldest pending job age). DLQ depth. Postgres write
  IOPS attributable to the queue table.
- **Reversal cost.** Two-way door. If we outgrow Postgres-as-queue,
  we migrate to SQS/Kafka with a parallel-write window. Cost is
  one engineer-week of migration work. Not expensive enough to
  warrant pre-emptive avoidance.

## Open questions

- At ~5k sustained jobs/hour, revisit whether the queue should
  move off the application Postgres to its own instance (still
  Postgres, just isolated).
- What's the retention policy for completed-job rows? Defer for
  3 months; revisit when the table exceeds 10M rows.
```

That's the shape. The constraint is named (team's operational expertise + workload size), the alternatives are real, the sacrifice is explicit (Postgres write load, table bloat risk), the reversal cost is honest (two-way door, one engineer-week).

## When NOT to write an ADR

ADRs are not free — they're durable records people will read later. Don't write one for:

- **Two-way-door decisions with low impact.** Picking a logging library, a date-formatting helper, a CSS framework. Just pick and move on.
- **Decisions already made by team standards.** "We use TypeScript" doesn't need an ADR; the team standard is the record.
- **Implementation details below the architecture line.** Function signatures, internal class structure, naming conventions. ADRs are for cross-cutting decisions that future engineers need to understand.
- **Decisions the team would never reverse.** "We use HTTPS." That's not a decision; that's a baseline.

A useful test: would someone joining the team six months from now ask "why did we do it this way?" and be confused without the context? If yes, ADR. If no, skip.

## ADR maintenance

- ADRs are **append-only and immutable.** Don't edit a past ADR; supersede it with a new one (status: Superseded by ADR-NNN). The history is the value.
- **Number them sequentially.** ADR-001, ADR-002, etc. Per repository or per system, not per author.
- **Store them in the repo**, next to the code they describe (`docs/adrs/` or similar). Not in a wiki that no one reads.
- **Review them in PRs.** An architectural change with no corresponding ADR is a change with no record. Reviewers should ask "where's the ADR?" before approving.

If a decision is significant enough to debate, it's significant enough to write down.
