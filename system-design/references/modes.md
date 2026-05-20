# Modes

Load when the mode is not greenfield. The four working modes, each with its own elicitation shape, phase sequence, and output. Greenfield is the default and lives inline in `SKILL.md`; this file covers **review**, **diagnose**, and **evolve** in depth.

## Why modes matter

The same skill, applied to different questions, produces different shapes of output. A request to **build** something is different from a request to **critique** something is different from a request to **diagnose** something is different from a request to **evolve** something. Same constraints discipline; different deliverable.

The most common skill failure is mode confusion: the user asks for a critique, the skill delivers a redesign. The user asks for a diagnosis, the skill delivers a rewrite plan. Naming the mode prevents this.

## Mode signal table (recap)

| Signal | Mode |
|---|---|
| "design X" / "build a system for Y" / "what's the architecture for Z" | greenfield |
| "critique this" / "review our architecture" / "what's wrong with this design" / pastes a design | review |
| "the DB is falling over" / "we keep getting paged" / "why is this slow" / "we have a production problem" | diagnose |
| "we need to scale this" / "how do we add geo" / "extract X into a service" / "what's the next step" | evolve |

**When ambiguous, default to greenfield with propose-and-go.** The cost of a wrong mode is one turn.

---

## Review mode

User describes or pastes an existing design (an architecture diagram, an RFC, a verbal description, a system in production) and asks for critique. **The skill's job is to find problems, not to redesign.**

### Elicitation

Pin these before critiquing:

1. **The design.** What's being reviewed? If the user describes verbally, restate it back in 3–5 lines to confirm understanding.
2. **The scope of the review.** Is this a full review (every dimension), or focused (resilience-only, cost-only, consistency-only)?
3. **The constraints the design was built against.** What did the team think the binding constraints were? (Many design problems are constraint-mismatches: the design solves a constraint that wasn't actually binding.)
4. **Current pain.** Is the design in production? Are there symptoms? (If yes, this may actually be a diagnose request — switch.)
5. **What changed?** New scale, new requirements, new team — context for why the review is happening now.

### Phase sequence

```
ELICIT(design) → CRITIQUE → PRIORITIZED FINDINGS
```

### CRITIQUE walk

Walk the design against five dimensions, in this order. Each item that fires becomes a finding.

1. **Binding-constraint mismatches.** What constraint is each significant choice solving? If the constraint wasn't actually binding, the choice is over-engineering.
   - Example: "We picked Cassandra for horizontal scale" — but the workload at 12 months projects to 30k write QPS, which a Postgres primary handles. Cassandra is solving an unbinding constraint at high operational cost.
2. **Over-engineering smells.** Walk `references/anti-patterns.md`. Each pattern that fires becomes a finding.
3. **Missing failure-mode coverage.** Walk the per-dependency checklist from `references/failure-modes.md`. The most common gap is "failover is untested." The second most common is "we don't have an MVF defined."
4. **Hidden one-way doors.** Find the choices the team will pay for later but didn't explicitly own:
   - Shard key (changing it = full data migration).
   - Identifier scheme exposed to clients (UUID vs auto-increment vs custom; changing it breaks integrations).
   - Wire format on persisted data (changing a serialization format means migration).
   - Multi-region commitment (going active-active is one-way; going back is harder).
   - Cross-service synchronous coupling (turns multiple services into one for failure purposes).
5. **Consistency boundaries.** Count the stores. Each pair is a potential divergence. For each boundary, is there a real sync mechanism (outbox / CDC) or is it dual-write hope?

### Output shape — PRIORITIZED FINDINGS

```
P0 — must fix before this design is safe in production
  - <finding>: <binding constraint it concerns> → <smallest fix>
  - ...

P1 — should fix in the next quarter
  - <finding>: ...

P2 — worth knowing, defer
  - <finding>: ...

Open questions for the team
  - <question>: ...
```

**Each finding names the constraint it's about and the smallest fix.** No P-level is mandatory — fine to have zero P0s if the design is sound.

### What NOT to do in review mode

- **Do not redesign.** If the user wants a redesign, they'll switch to greenfield and ask. Reviewing is finding problems, not proposing replacements.
- **Do not pad with positives.** "The use of TypeScript is solid" is not a finding. If everything's fine, the review is short.
- **Do not invent constraints to justify the existing design.** If the constraint behind a choice is missing, that IS the finding ("decision lacks named binding constraint").
- **Do not skip the smallest-fix step.** A finding without a path forward is a complaint.

### Propose-and-go for review

> Reviewing this as a P0/P1/P2-prioritized critique against your current constraints (~50k QPS, 99.95% SLO, 3-engineer team). I'll surface binding-constraint mismatches, over-engineering, missing failure coverage, and one-way doors. Not redesigning. Say so if you want a full redesign instead.

---

## Diagnose mode

User describes a production problem as symptoms. **The skill's job is to diagnose, then propose the smallest fix.**

### Elicitation

Pin these before diagnosing:

1. **The symptoms, with numbers.** Latency p50/p99, error rate, queue depth, saturation, working set, alert text. "It's slow" is not a symptom; "p99 went from 200ms to 1200ms" is.
2. **What changed.** Recent deploys, traffic shifts, data growth, configuration changes, dependency upgrades. Most production problems correlate with a change.
3. **The current state.** Architecture, scale, what's in front of the affected component, what's downstream.
4. **What's been tried.** Restarts? Tuning? Quick fixes? The history rules out hypotheses.
5. **Blast radius.** Is this affecting all users, one segment, one endpoint, one tenant? The scope of the problem narrows the cause.

### Phase sequence

```
ELICIT(symptoms + state) → DIAGNOSE → SMALLEST-FIX → NEXT-SIGNAL
```

### DIAGNOSE walk

Diagnose before prescribing. The order matters: rule out cheap causes before expensive ones.

**Cheap causes (check first):**

- **Connection pool exhaustion.** Symptoms: "database CPU fine but queries hang." Mitigation: PgBouncer / appropriate pool size.
- **Missing index.** Symptoms: query slowness on specific endpoints; sequential scans. Mitigation: EXPLAIN ANALYZE the slow queries, add the missing index.
- **Working set exceeds RAM.** Symptoms: cache hit ratio dropped; disk I/O up; latency degradation correlates with data growth. Mitigation: bigger instance, or trim the working set.
- **GC pause.** Symptoms: tail-latency spikes at regular intervals. Mitigation: tune the collector, reduce allocation, bigger heap.
- **Slow query.** Symptoms: one query is most of the time. Mitigation: EXPLAIN ANALYZE, query rewrite, index, or denormalization.
- **Hot key / hot partition.** Symptoms: one node/partition at 100%, peers idle. Mitigation: re-shard within the hot partition.
- **Resource exhaustion** (file descriptors, ephemeral ports, threads, memory). Symptoms: error messages name the exhausted resource. Mitigation: raise the limit, or fix the leak.
- **Retry storm.** Symptoms: error rate spikes synchronized across services. Mitigation: backoff + jitter on the retrying client.
- **Cache stampede.** Symptoms: latency spike correlates with cache expiration boundaries. Mitigation: TTL jitter, single-flight, soft-TTL background refresh.

**Expensive causes (only if cheap is ruled out):**

- **Vertical limit.** The instance can't go bigger. Move to read replicas + caching.
- **Single-primary write throughput.** Sharding is the last resort, not the first.
- **Wrong datastore.** The access pattern genuinely doesn't fit the store family. Migration is expensive — exhaust everything else first.

### Reasoning backward — the diagnose discipline

The temptation in diagnose mode is to skip to the most exciting hypothesis ("we need to shard!"). Resist this. The discipline:

1. **What's the symptom, in numbers?** Without a number, you can't measure whether a fix worked.
2. **What's the binding resource?** CPU, RAM, disk I/O, network, connections, locks, threads. One of these is the bottleneck.
3. **What recent change could have caused this?** Data growth, traffic shift, deploy, dependency change.
4. **What's the smallest hypothesis consistent with the evidence?** Picking the cheapest hypothesis that explains the data is correct most of the time.
5. **What would distinguish this hypothesis from others?** Before proposing a fix, identify the measurement that would confirm or refute.

### SMALLEST-FIX

The fix is the smallest change that addresses the binding constraint identified. Resist scope creep.

- A missing index does not justify a redesign.
- A connection pool problem does not justify microservices.
- A working-set-exceeding-RAM problem may justify a larger instance, not sharding.
- A cache stampede justifies TTL jitter + single-flight, not "rewrite without caching."

### NEXT-SIGNAL

After the fix, what does the team monitor to know it worked? And what would force the next step?

> Fix: add the missing index on `orders.customer_id`. Signal it worked: p99 on `/orders/recent` drops below 200ms. Signal it didn't (or there's a deeper problem): p99 stays elevated, or returns within a week. Next step if so: pg_stat_statements + EXPLAIN ANALYZE to find the remaining slow query.

### What NOT to do in diagnose mode

- **Do not redesign.** "Move off Postgres" is a diagnose-mode failure when the cheap-cause walk wasn't done.
- **Do not propose microservices.** Splitting a monolith does not fix a database problem.
- **Do not propose Kafka.** Adding a queue does not fix a slow query.
- **Do not propose sharding before exhausting vertical + replicas + caching.**
- **Do not skip the "what changed" question.** Most production problems correlate with a change.

### Propose-and-go for diagnose

> Treating this as a diagnose request. I'll walk cheap causes first (connection pool, missing index, working set vs RAM, slow query, retry storm, cache stampede) before expensive ones (replicas / caching / sharding). Will name the smallest fix and what signal confirms it worked.

---

## Evolve mode

User has a working system at one scale or shape and is hitting a wall. **The skill's job is to propose the next step, not a rewrite.**

### Elicitation

Pin these before proposing:

1. **The current system.** Architecture, scale (current numbers), datastore choices, where the team is operationally comfortable.
2. **The wall.** What specifically is breaking or about to break? Numbers, not narrative. "We're at 80% Postgres CPU at peak and capacity-planning says 12 months until 100%" is a wall; "we're worried about scale" is not.
3. **What's been tried.** Vertical scaling? Read replicas? Caching? What worked, what didn't.
4. **Constraints that didn't exist before.** New requirements (geo, compliance, new product), new scale signals, new team structure.
5. **Two-way vs one-way preference.** How reversible does the team want this step to be? A two-way door is almost always preferable.

### Phase sequence

```
ELICIT(state + wall) → NEXT-STEP → MIGRATION-PLAN → NEXT-SIGNAL
```

### NEXT-STEP

The next step comes from the scaling order of reach (`references/patterns.md`) or the storage migration ladder (`references/datastores.md`). **Pick the smallest step that addresses the wall.** Skipping steps requires naming the constraint that forces the skip.

Common evolutionary moves:

- Vertical → horizontal stateless (the easiest).
- Stateless → +read replicas (for read-heavy walls).
- +read replicas → +caching (when DB is still the limit).
- +caching → sharding (when writes are the limit and vertical is exhausted).
- Single-region → active-passive multi-region (for DR / regional outages).
- Active-passive → active-active (for cross-region latency, with conflict resolution cost).
- Monolith → extract one service (for a specific team-coupling or deploy-coupling pain).
- Postgres → +specialized store (for an access pattern genuinely outside relational, e.g. search index, time-series).

Each move has a cost. The justification names the constraint that forces it; the alternative is "stay where you are."

### MIGRATION-PLAN

For any storage or data-shape change, the migration is the work. The plan:

1. **Parallel-write window.** Write to both old and new stores. Read from old. Verify the new store gets correct data. This window may last days or weeks.
2. **Backfill historical data.** Migrate existing rows from old to new. Confirm row counts and checksums.
3. **Flip reads.** Start reading from new, keep writing to both. Monitor for read-path bugs.
4. **Stop writes to old.** Once read traffic confirms the new store is correct.
5. **Decommission old.** After a safety window (typically 30+ days) where rollback is still possible.

For non-storage migrations (extracting a service, changing a queue), adapt: dual-publish, shadow-traffic, gradual cutover, monitor at each step.

**Two-way-door preference at every choice point.** If a step can be reversed, prefer the reversible version. The cost of reversibility is usually small; the cost of irreversibility is occasionally enormous.

### NEXT-SIGNAL

After the step lands, what's the next wall?

> After the read replicas are in production and caching is in front: the next wall is write throughput on the primary. Signal: write QPS exceeds ~10k sustained, or vacuum can't keep up, or write latency climbs above the budget. Next step then: shard the highest-volume tables (likely `events` and `audit_log`) by `tenant_id`, with `tenant_id` as the new partition key. That's a one-way door — plan the shard key carefully.

### What NOT to do in evolve mode

- **Do not propose a rewrite.** Existing systems have operational knowledge, runbooks, customer-tested edge cases, performance characteristics. Throwing that away has a cost the rewrite plan usually undercounts.
- **Do not skip steps.** "We're going from single Postgres to global active-active" is several one-way doors at once.
- **Do not ignore the migration cost.** The new architecture might be "better" in isolation; the migration is the comparison.
- **Do not propose a step without naming the next wall.** Each step buys time, not infinity.

### Propose-and-go for evolve

> Treating this as an evolve request. I'll pick the smallest next step from the scaling order of reach, plan the migration with a parallel-write window and rollback path, and name the next wall after this step. Not a rewrite. Say so if you want a greenfield redesign instead.

---

## Mode-switching mid-conversation

The user may start in one mode and shift. Honor the shift:

- **Review → greenfield:** "OK now redesign it." Switch. Bring the constraints from the review with you.
- **Diagnose → evolve:** "Fix is in; what's the next architecture step?" Switch. The diagnosis is now context for the next-step proposal.
- **Greenfield → review:** "Actually critique this existing thing instead." Drop the greenfield draft; restart in review.
- **Evolve → diagnose:** "Wait, we're already paged; what's wrong now?" Switch. The wall just became a production problem.

When switching, state the switch explicitly so the user knows the conversation has changed shape:

> Switching to greenfield mode at your request. The constraints from the review carry forward; I'll redesign against them rather than critique what exists.

---

## Mode-agnostic discipline

Some rules apply in every mode:

- **Constraints gate the work.** No architecture, critique, diagnosis, or migration plan without them.
- **Numbers, not narratives.** A symptom is a number. A wall is a number. A scale is a number. "Slow" / "doesn't scale" / "falling over" are not enough — pin them.
- **The smallest thing that meets the binding constraint.** Across modes, this is the recurring stance.
- **Name the next signal.** Every recommendation ends with "what tells you this worked, and what would force the next step." The signal makes the recommendation falsifiable.
- **Output matches depth.** Narrow question, narrow answer. Full design request, full design. Critique with three small findings, three small findings — not eight.
