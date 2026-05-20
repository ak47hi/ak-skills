---
name: system-design
description: Design real production systems end-to-end: elicit constraints → capacity estimate → data model & storage → architecture → scale the one bottleneck → failure modes → ADR-style decisions, each tied to a binding constraint and an explicit sacrifice. Numbers first; complexity must be earned; default to boring tech with a single-machine baseline check. Trigger on architecture work even when phrased in product terms: "the database is falling over", "we keep getting paged for X", "should we use Kafka", "how do we scale this", "what datastore for", "design a notification service", "capacity estimate for", "writing an ADR", "split into services", "resilience review", "SLO design", "thundering herd / hot shard / cascading failures", architectural tradeoff questions. Do NOT use for interview / whiteboard / LeetCode-style design prep, "design Twitter" drills, pure UI/frontend architecture, or implementation-level code review.
---

# system-design skill

Design production systems by routing the request through a fixed phase order. Opinionated about three things:

1. **Numbers first, structure second.** Estimate before drawing. An estimate that fits one machine reshapes the design before any box is on the page.
2. **Complexity must be earned.** Default is the simplest thing that meets the SLO. Microservices, sharding, Kafka, polyglot stores, CQRS — each is a cost the binding constraint has to pay for. "Boring tech until a constraint forces otherwise."
3. **Every decision ties to a constraint and a sacrifice.** If a choice can't be explained as "binding constraint X forces this, accepted sacrifice Y" — the design isn't done yet.

This is for building **real** systems. Not interview prep. Not whiteboard drills. If the user is practicing for an interview, point them at canonical interview resources instead.

---

## Seven phases

```
1. ELICIT       The gate. Constraints in or block.                    (inline)
2. ESTIMATE     Peak QPS, storage/yr, bandwidth, working set.         references/estimation.md
3. DATA         Access patterns → model → store(s).                   references/datastores.md
4. ARCHITECT    Components, data flow, sync vs async per boundary.    (inline — synthesis)
5. SCALE        Find the one binding bottleneck. Deep-dive only that. references/patterns.md
6. FAILURE      Per dependency: slow / down / wrong + blast radius.   references/failure-modes.md
7. JUSTIFY      ADR-style decision record per significant choice.     references/tradeoffs.md
```

Run in order. Skip a phase only if its output is already supplied (e.g. user pastes a capacity estimate — skip 2; user asks one targeted question — skip everything irrelevant to it).

---

## Phase 1: ELICIT (the gate)

**Do not produce architecture before constraints exist.** Inferred constraints are fine — flag them as assumptions — but design that starts with zero numbers is hallucination.

### Seven dimensions to pin down

1. **Functional core** — the 2–3 dominant operations the system has to do. Not the feature list. The hot path.
2. **Scale** — current and 12-month projection. Peak QPS, not average. ("Twitter daily peak ≠ average × 1.0; assume peak ≈ 2–3× average for human-traffic systems unless you have data.")
3. **Latency budget** — p50 and p99 per dominant operation. "Fast" is not a number.
4. **Consistency per operation** — different operations on the same system often want different consistency. Payment write ≠ trending-now read.
5. **Availability SLO** — three nines / four nines. Translates to error budget per quarter, which translates to how much resilience work the design has to pay for.
6. **Read : write ratio** — 95:5 vs 50:50 vs 5:95 reshapes the storage choice and the caching strategy.
7. **Operational reality** — team size, on-call rotation, existing stack, cloud vs self-managed, in-house ops maturity. "Run Cassandra" means "have a team that runs Cassandra at 3am." Boring is often correct.

### When to skip, when to ask, when to propose-and-go

| Signal in the prompt | Action |
|---|---|
| All seven dimensions stated (or derivable from a clear scenario) | Skip ELICIT. Proceed to ESTIMATE. |
| User asks one targeted decision ("Kafka vs Postgres-as-queue for ~300 jobs/hr") | Skip ELICIT. Confirm the binding constraint inline (≤1 sentence) and answer narrowly. |
| Three or fewer dimensions are missing AND defaults are uncontroversial | Propose-and-go: state inferred defaults in a single short block, proceed. The user corrects if wrong. |
| Four or more missing OR the prompt is broadly vague ("design our system") | Ask ONE batched round. Number the questions. Do not iterate elicitation rounds. |

**One round, not three.** If the user's answer is still vague, infer the rest and flag every inferred number as an assumption. The user can correct on the next turn.

**What NOT to ask:** the technology to use, the deployment target, the language, the framework. Those are downstream decisions the skill makes; the user supplies constraints, not solutions.

### Propose-and-go template (mild ambiguity)

> Treating this as: ~50k DAU, 10:1 read:write, p99 < 200ms on the read path, single-region for v1, two-engineer team on AWS, Postgres + Redis already in stack. Proceeding — correct any of these.

Short, numbered, replaceable. Don't dress it up.

---

## Phase 2: ESTIMATE

Load `references/estimation.md`. Produce: peak QPS, storage at 12 months (with replication + index overhead), bandwidth, working-set size. Run the **single-machine baseline check** — one modern box handles surprisingly much. If the estimate fits one box with headroom, the design starts there and distribution must be justified by something other than throughput (HA, geographic latency, blast-radius isolation).

---

## Phase 3: DATA

Load `references/datastores.md`. Derive the data model **from the access patterns** (Phase 1's functional core), not from a tidy normalization. Pick stores per operation. Default to **relational until it hurts** — Postgres absorbs a lot of work before it's the binding constraint. Polyglot persistence is a cost (every additional store is a new place data can diverge); count consistency boundaries before adopting a second store.

---

## Phase 4: ARCHITECT (synthesis)

No reference — this phase is where Phase 2 (numbers) and Phase 3 (data) get drawn. Sketch components, boundaries, sync vs async per boundary. Keep the topology **as flat as the SLO allows**. Async off the synchronous critical path of a user-visible request; sync only where the user is literally waiting. Name what crosses a process boundary; everything else is internal.

---

## Phase 5: SCALE

Load `references/patterns.md`. Find the **single binding bottleneck** — the one resource that fails first as load rises. Scaling everything is over-engineering. Scaling order of reach: **vertical → horizontal stateless → read replicas → caching → sharding.** Each step has a binding constraint that forces the next; don't skip without naming it. Deep-dive only the bottleneck.

---

## Phase 6: FAILURE

Load `references/failure-modes.md`. For every dependency, ask three questions: **slow, down, wrong** — what does the system do in each case, and what's the blast radius? Define the **minimum viable function** for every user-visible flow (checkout works without recommendations; feed works without personalization). Walk the per-dependency resilience checklist. End with the line: untested failover is not failover.

---

## Phase 7: JUSTIFY

Load `references/tradeoffs.md`. Every significant choice gets an ADR-style record: Context / Decision / Alternatives / Consequences (including new failure modes + reversal cost + what to monitor) / Open questions. "Significant" means: one-way door, or new operational surface, or a deviation from the team's existing stack. Two-way-door decisions don't need ADRs — say so out loud and move on.

---

## Output structure

For a **full design**, emit these sections in order. Drop any section whose Phase had no output (rare).

```
1. Constraints                  (assumptions explicitly flagged)
2. Capacity estimate            (must include the single-machine baseline line)
3. Data model & storage         (per-operation consistency, per-store justification)
4. Architecture                 (components, boundaries, sync vs async)
5. Scaling the bottleneck       (the ONE bottleneck, the scaling step that addresses it)
6. Failure modes & mitigations  (per-dependency)
7. Decisions (ADR-style)        (one ADR per significant choice)
8. Open questions               (what would force a re-decision)
```

For a **narrow question** (one decision, scoped) — drop unused sections. A "Kafka vs Postgres-as-queue at ~300 jobs/hr" answer is **not** a full 8-section template; it's a short answer that names the binding signal, picks one with a sacrifice, and states the signal that would flip the answer. **Match the user's depth. Padding a one-decision answer into the full template is a failure mode.**

---

## When to push back

Common over-engineering smells. If you see one, challenge it before producing the design:

- **"Let's split this into microservices."** → What coupling problem is the monolith causing? Microservices add network, deployment, and observability cost; the binding constraint has to be team-coupling or deploy-coupling, not "modernity."
- **"We need to shard the database."** → Have you exhausted read replicas + caching? Sharding multiplies operational cost permanently; it's a one-way door for the shard key.
- **"Let's put Kafka in front of this."** → At what rate? A few hundred jobs/hr is a Postgres `SELECT ... FOR UPDATE SKIP LOCKED` or SQS. Kafka is a real cluster to operate.
- **"We'll add a search index / graph DB / time-series DB."** → How many consistency boundaries does that make? Each extra store doubles a class of bugs.
- **"We'll write our own consensus / leader election."** → No. Use a battle-tested implementation. Always.
- **"Let's go multi-region active-active."** → Active-passive almost always meets the SLO with a fraction of the consistency pain. What's the RTO/RPO that forces active-active?

These are conversations, not refusals. If the user has a reason, the reason is the binding constraint — record it in the ADR.

## When NOT this skill

- **Interview / whiteboard prep.** Different objective (signaling skill, not building). Point the user at canonical interview material instead.
- **Pure UI / frontend architecture.** State management, component layout, design systems are a different problem space.
- **Implementation-level code review.** This skill designs systems; it doesn't review function signatures.
- **Greenfield product strategy.** Whether to build the system at all is upstream of how to build it.

---

## Tone and depth

Terse, professional, no emoji, no decorative filler. Match the user's depth: give seniors the tradeoff, not the definition. If the user said "PACELC," don't explain CAP first. If the user said "the database is slow," don't lecture on B-trees — diagnose.

The output is decisions, not a textbook. Every paragraph should change what the reader builds.

---

## References at a glance

| File | What it carries |
|---|---|
| `references/estimation.md` | Latency ladder, data-size table, capacity formulas, Little's Law, single-machine baseline, worked example. |
| `references/datastores.md` | Selection matrix by family, "relational until it hurts" default, per-op consistency, CAP/PACELC practical, replication & partitioning hazards, polyglot cost, selection checklist. |
| `references/patterns.md` | Scaling order of reach, caching layers + hazards, async/messaging (queue vs log), CQRS / ES warnings, idempotency, coordination primitives. |
| `references/failure-modes.md` | Failure taxonomy, mitigation catalogue, degradation strategy, minimum-viable-function, per-dependency resilience checklist. |
| `references/tradeoffs.md` | Core axes, 5-step tradeoff method, ADR template, "when NOT to write an ADR." |
