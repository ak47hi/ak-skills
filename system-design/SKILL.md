---
name: system-design
description: Design real production systems and evolve existing ones — greenfield, critique, diagnose, or migrate. Phases: elicit constraints → capacity estimate → data model & storage → architecture → scale the one bottleneck → failure modes → ADR-style decisions, each tied to a binding constraint and an explicit sacrifice. Numbers first; complexity must be earned; default to boring tech with a single-machine baseline check. Trigger in any framing: "the database is falling over", "should we use Kafka", "how do we scale this", "what datastore for", "design a notification service", "capacity estimate for", "writing an ADR", "split into services", "resilience review", "SLO design", "critique this design", "review our architecture", "diagnose why X is slow", "next step to scale", architectural tradeoff questions. Do NOT use for interview / whiteboard / LeetCode-style design prep, "design Twitter" drills, pure UI/frontend architecture, or implementation-level code review.
---

# system-design skill

Design production systems by routing the request through a fixed phase order. Opinionated about three things:

1. **Numbers first, structure second.** Estimate before drawing. An estimate that fits one machine reshapes the design before any box is on the page.
2. **Complexity must be earned.** Default is the simplest thing that meets the SLO. Microservices, sharding, Kafka, polyglot stores, CQRS — each is a cost the binding constraint has to pay for. "Boring tech until a constraint forces otherwise."
3. **Every decision ties to a constraint and a sacrifice.** If a choice can't be explained as "binding constraint X forces this, accepted sacrifice Y" — the design isn't done yet.

This is for building **real** systems. Not interview prep. Not whiteboard drills. If the user is practicing for an interview, point them at canonical interview resources instead.

---

## Mode routing

Before phases, name the mode. Most prompts are greenfield; the others have different phase sequences.

| Signal | Mode | Workflow |
|---|---|---|
| "design X" / "build a system for Y" / "what's the architecture for Z" | **greenfield** | ELICIT → ESTIMATE → DATA → ARCHITECT → SCALE → FAILURE → JUSTIFY |
| "critique this design" / "review our architecture for X" / pastes a design + asks for feedback | **review** | ELICIT(design) → CRITIQUE → PRIORITIZED FINDINGS |
| "the DB is falling over" / "we keep getting paged for X" / "why is this slow" | **diagnose** | ELICIT(symptoms + state) → DIAGNOSE → SMALLEST-FIX → NEXT-SIGNAL |
| "we need to scale this" / "how do we add geo" / "extract X service" / "next step from here" | **evolve** | ELICIT(state + wall) → NEXT-STEP → MIGRATION-PLAN → NEXT-SIGNAL |

When the mode signal is ambiguous, **default to greenfield with propose-and-go** ("Treating this as greenfield design — say so if you actually want a critique of an existing X"). The cost of a wrong mode is one turn; the user corrects.

Cross-cutting rules in every mode:

- Constraints gate the work — no architecture, critique, diagnosis, or migration plan without them (inferred + flagged is fine).
- The anti-pattern catalog in `references/anti-patterns.md` is walked in JUSTIFY (greenfield) and CRITIQUE (review). For diagnose and evolve, it's walked against the proposed fix or next step.
- Output matches the user's depth. Narrow question → narrow answer.

Full rules for non-greenfield modes live in `references/modes.md`. Load it when the mode is not greenfield.

---

## Greenfield workflow (default)

### Seven phases

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

### Archetype recognition (during ELICIT, every mode)

After pinning the universal seven dimensions, check `references/archetypes/README.md` for archetype signals. The catalog covers nine recurring shapes: multi-tenant SaaS, real-time streaming, batch ETL, ML inference, geo-distributed, read-heavy/mobile, write-heavy, observability, hot-cold-tiered.

If **one or more archetypes fire**, load their files. Each archetype contributes:
- Additional elicitation questions (beyond the universal seven).
- Recurring failure modes specific to that shape.
- The questions a god-tier designer always asks before recommending.
- Common pitfalls and anchor numbers for calibration.

If **no archetype fires**, the universal foundation handles it. Most systems are not exotic; don't force a label.

If **multiple archetypes fire** (common — a system can be multi-tenant + geo-distributed + read-heavy), load each. Conflicts between archetype recommendations are **surfaced to the user**, not hidden — e.g., "multi-tenant says isolate per tenant; geo-distributed says minimize cross-region writes — reconciling these constrains your tenant→region mapping."

Loading an archetype does **not** mean producing a canned design. The archetype brings questions and failure modes; the design still derives from the elicited constraints. Two multi-tenant SaaS systems with different scales and operational realities have different designs.

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

## Artifacts (opt-in, never silent)

When the session produces durable work — a full design, a significant decision, a substantial critique, a migration plan, a postmortem — **offer to write it to disk**. The skill never silently creates files. Load `references/artifacts.md` for the full rules.

The flow:

1. Identify which artifacts the work justifies (RFC + ADRs for a full design; critique doc for a review with substantial findings; migration plan for an evolve step; postmortem for a diagnosed incident the user wants written up; capacity worksheet for a non-trivial estimate).
2. Offer them as a numbered list with proposed paths under `docs/` (or the repo's existing convention if different). Mention which templates from `templates/` will be used.
3. Wait for explicit confirmation. The user may accept all, accept some, redirect paths, or decline.
4. Write only what was confirmed.

**Defaults to no when in doubt.** Narrow questions, conversational iteration, quick fixes — chat is the deliverable; don't offer files.

**Per-mode defaults:**

| Mode | Artifacts to consider offering |
|---|---|
| Greenfield, full design | `rfc.md` (the whole design) + one `adr.md` per significant choice + `capacity-worksheet.md` |
| Greenfield, narrow | None — chat-mode answer is the deliverable |
| Review with 3+ P0/P1 findings | `critique.md` |
| Diagnose, smallest-fix proposal | None — chat answer. Offer `postmortem.md` only if the user is writing up an actual incident |
| Evolve, multi-phase migration | `migration-plan.md` + ADR for the chosen step |
| User explicit request ("write this up") | Whatever was requested, regardless of scope |

**Significant-choice criteria for ADRs** (from `references/tradeoffs.md`): one-way door, new operational surface, deviation from the team's existing stack, or a non-obvious tradeoff. Two-way-door / already-team-standard / implementation-level choices don't get ADRs — say so out loud and move on.

**Diagrams.** If a C4 / sequence / deployment diagram would strengthen the design, **point the user at the sibling `plantuml` skill** rather than embedding PlantUML output. Cross-skill separation is preserved.

---

## Review, diagnose, evolve workflows

Brief shape; full phase rules in `references/modes.md`. Load it when the mode is not greenfield.

### Review

User describes or pastes an existing design and asks for critique. **Do not redesign.** Walk the design against:

1. **Binding-constraint mismatches.** Is the design solving a constraint that was actually binding? "We picked Cassandra for horizontal scale" — but the workload is 50k QPS that Postgres absorbs.
2. **Over-engineering smells.** Walk `references/anti-patterns.md` against the design.
3. **Missing failure-mode coverage.** Per dependency, is slow/down/wrong actually handled? Untested failover assumed working is the most common gap.
4. **Hidden one-way doors.** Shard key, identifier scheme, wire format on persisted data, multi-region commitment.
5. **Consistency-boundary count.** Polyglot stores without a sync mechanism (outbox / CDC). Dual-write hazards.

Output is **prioritized findings** (P0 / P1 / P2), each naming the binding constraint it concerns and the smallest fix. If the user wants a redesign, switch to greenfield mode and say so.

### Diagnose

User describes a production problem as symptoms. **Diagnose before prescribing.**

1. Pin symptoms to numbers (latency p50/p99, error rate, queue depth, saturation, working set vs RAM). Ask if unstated.
2. Reason backward to the binding constraint. Rule out cheap causes (connection pool exhaustion, missing index, working set vs RAM, GC pause, slow query) before expensive ones (sharding, rewrite, new datastore).
3. Propose the **smallest fix** that addresses the binding constraint.
4. Name the signal that says "the fix worked" and the signal that would force the next step.

Hard rule: "the DB is falling over" does not necessarily mean "shard the DB." The diagnosis usually finds something cheaper.

### Evolve

User has a working system and is hitting a wall. **Propose the next step, not a rewrite.**

1. Confirm the wall — the specific binding constraint, with numbers.
2. Pick the next step from the scaling order of reach (`references/patterns.md`) or the storage migration ladder (`references/datastores.md`). Skipping steps requires naming the constraint that forces the skip.
3. Plan the migration: **parallel-write window** if storage is touched, **two-way-door preference** at every choice point, runbook for rollback.
4. Name the next wall after this step lands.

Existing systems have operational knowledge baked in; throwing it away has a cost. "We'd build it differently now" is a real consideration, but the migration cost is the honest comparison.

---

## When to push back

The full anti-pattern catalog lives in `references/anti-patterns.md` — walk it during JUSTIFY (greenfield) and CRITIQUE (review). Common smells worth challenging up front:

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
| `references/modes.md` | Full rules for the four working modes (greenfield / review / diagnose / evolve), per-mode elicitation questions, phase sequences, propose-and-go templates, output shapes. |
| `references/anti-patterns.md` | Catalogued over-engineering smells with named symptoms, why-bad, and the question to ask instead. Walked in JUSTIFY (greenfield) and CRITIQUE (review). |
| `references/archetypes/` | Catalog of nine recurring system shapes (multi-tenant SaaS, real-time streaming, batch ETL, ML inference, geo-distributed, read-heavy/mobile, write-heavy, observability, hot-cold-tiered). Per archetype: when it fires, additional elicitation questions, recurring failure modes, the questions a god-tier designer always asks, common pitfalls, anchor numbers. Loaded during ELICIT when signals match. Index in `archetypes/README.md`. |
| `references/benchmarks.md` | Calibrated throughput ceilings, latency profiles, and known scaling cliffs per component (network, storage, Postgres / MySQL, Redis / Memcached / DynamoDB, MongoDB / Cassandra, Kafka / SQS / Kinesis / RabbitMQ, ClickHouse / BigQuery / Snowflake, Elasticsearch, HTTP services by runtime, Lambda, ALB / CDN) plus per-architecture-layer latency budgets. Anchor numbers for ESTIMATE and ADR alternatives. Reviewed annually. |
| `references/artifacts.md` | When to offer durable artifacts (ADR / RFC / capacity worksheet / postmortem / critique / migration plan), the opt-in confirmation flow, file naming + path conventions, significant-choice criteria for ADRs, cross-skill plantuml-for-diagrams handoff. |
| `templates/` | Fillable artifact skeletons used when the user confirms artifact creation: `adr.md`, `rfc.md`, `capacity-worksheet.md`, `postmortem.md`, `critique.md`, `migration-plan.md`. The teaching/inline ADR template in `tradeoffs.md` complements these; this directory is the fillable companion. |
