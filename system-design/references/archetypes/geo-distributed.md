# Geo-distributed

Load when the prompt describes multi-region deployment: RTO/RPO requirements, regional failover, active-active or active-passive across regions, data residency, GDPR locality, cross-region latency.

The defining concern: **trading latency, cost, and operational complexity against availability and data-residency requirements that single-region deployment can't meet.**

## When this archetype fires

Signal cues:
- "Multi-region" / "multi-DC" / "geo-distributed"
- "Active-active" / "active-passive" / "regional failover"
- "RTO" (recovery time objective) / "RPO" (recovery point objective)
- "Data residency" / "GDPR locality" / "regulatory data localization"
- "Cross-region latency" / "users in APAC are slow"
- "Disaster recovery" / "DR plan" / "regional outage"

Non-signals:
- Multi-AZ within one region — that's standard HA, not geo-distributed (cross-AZ latency is < 1ms; cross-region is 70–150ms; the problems are different).
- A CDN for static assets — that's edge caching, not geo-distribution of data.
- Multi-region read replicas without write capability or strict residency rules — closer to read-heavy-mobile patterns than full geo-distribution.

## Additional elicitation (beyond the universal seven)

1. **RTO (recovery time objective).** When a region goes down, how fast must the system come back up in another region? Minutes? Seconds? Zero-downtime?
2. **RPO (recovery point objective).** How much data can be lost in a regional failure? Zero (synchronous replication)? Seconds (async with low lag)? Minutes? Hours?
3. **User distribution.** Where are users geographically? What's the latency budget per region? A 200ms response is fine for low-latency regions; same response is unusable for users on the other side of the planet adding their own 150ms RTT.
4. **Data residency rules.** Does some data have to stay in specific regions (EU GDPR, China, Russia, India)? Per-customer, per-data-type, per-tenant? These rules ARE the architecture for the residency-bound data.
5. **Conflict resolution policy** (only if active-active). When two regions accept conflicting writes to the same record, what wins? Last-write-wins? CRDTs? Per-record region ownership? "We'll merge manually" is not a real answer.
6. **Failover trigger.** Manual (operator decides), automatic (health checks), or hybrid? Automatic failover has split-brain risk; manual has slower RTO.
7. **What's actually replicated.** All data? Hot data only? Per-region partitioning of cold data with cross-region for hot? The replication scope drives cost dramatically.
8. **Cost ceiling.** Active-passive doubles infrastructure (and underutilizes the secondary). Active-active doubles infrastructure AND increases write coordination cost. Is the budget compatible?
9. **Failover test cadence.** When was the last live failover test? "We haven't" is the common answer; it's the answer that produces incidents.

## Recurring failure modes

### Split brain

**Symptom.** A network partition isolates two regions. Both detect the other as down. Both promote themselves to primary. Both accept writes. The partition heals; reconciliation is impossible without data loss.

**Why it happens.** Failover logic without fencing. Two leaders are not allowed; the design failed to enforce it.

**Mitigation.** External consensus (etcd, ZooKeeper, Consul) holds the leader election. Fencing: a deposed leader is denied write access (storage-level lease, network-level rule). For multi-leader/active-active, use a database designed for it (CockroachDB, Spanner, Cassandra with proper consistency settings).

### Untested failover

**Symptom.** "We have multi-region for DR." When the real incident hits, the failover procedure has subtle wrong assumptions: DNS TTL is longer than expected, the secondary's connection pool isn't sized, monitoring doesn't follow, the runbook references an old environment.

**Why it happens.** Practice is expensive (real failover affects users), so it doesn't happen.

**Mitigation.** Practice quarterly. Tabletop exercises at minimum. Production failover in a low-traffic window, with rollback ready. Chaos engineering tools (Chaos Monkey for regions). Untested failover is not failover.

### Replication lag exceeds RPO

**Symptom.** The system claims RPO of 30 seconds. The actual replication lag (under load) is 5 minutes. A regional failure loses 5 minutes of data, breaching the SLA.

**Why it happens.** Replication lag wasn't measured under realistic write load. Async replication has no upper bound by default.

**Mitigation.** Monitor replication lag as a top-level metric. Alert when lag exceeds RPO budget. Throttle writes if lag is unacceptable. Synchronous replication for hard-RPO data (but accept the latency cost).

### Cross-region call latency cascading into user latency

**Symptom.** User in Europe makes a request. Service routes the request to a US region for a specific dependency. The 150ms RTT round trip dominates the response time. The system "works" but is unusably slow for some users.

**Why it happens.** Some service in the request chain is single-region. A single cross-region hop kills the latency budget.

**Mitigation.** Audit the full request chain for region locality. Replicate or relocate services so a request stays in one region. Where a cross-region call is unavoidable, make it async with a cached fallback.

### Failover that leaves stale state

**Symptom.** Region A is the primary. It fails over to Region B. Region A comes back later and starts serving traffic from its own (now stale) view of the world.

**Why it happens.** Failover changed the primary, but Region A's local resumption logic doesn't know it's not primary anymore. Without fencing, it accepts writes that diverge.

**Mitigation.** Resumed Region A must check current primary before accepting writes — and accept that it's now the standby. Fencing tokens, consensus-tracked epoch numbers, or operator-enforced standby.

### Data residency violations

**Symptom.** EU user data ends up in US-region replica due to a misconfigured replication topology. Discovered during audit; fines follow.

**Why it happens.** Replication topology configured loosely (replicate all data everywhere) doesn't respect residency rules.

**Mitigation.** Per-tenant or per-data-type region pinning. Replication topology enforced by region-aware routing (writes for EU users go only to EU; replicas of EU data only in EU). Audit logs of cross-region data movement.

### Conflict resolution as "last-write-wins" (LWW) for everything

**Symptom.** Active-active deployment using LWW for all conflicts. Two concurrent writes to the same record — one is silently discarded. User reports "my changes disappeared."

**Why it happens.** LWW is the easy default; designers don't consider per-record semantics.

**Mitigation.** Different records may need different resolution: LWW for non-critical metadata, CRDTs for counters/sets, per-record region ownership for financial state. Specify per record class, not globally.

## What god-tier designers always ask

1. **What's the actual RTO and RPO the business requires?** Often the business has never named them. Without numbers, design is by guess.
2. **What's the binding constraint forcing active-active vs active-passive?** Active-active is several times more expensive operationally. "Resilience" without an RTO < 1min is rarely worth it; active-passive with planned failover usually meets the SLO.
3. **What's the failover trigger?** Manual (human in the loop, slower RTO, no split-brain risk); automatic (faster RTO, requires consensus + fencing); document the choice.
4. **What's the conflict resolution policy per record type?** Universal LWW is data loss in disguise. CRDTs, per-record region ownership, or "fail and require explicit resolution" each fit different cases.
5. **Cross-region latency budget for user requests.** Identify which paths cross regions; budget the latency accordingly. Eliminate where possible.
6. **Data residency map: which data, which region(s)?** Document per-data-class. Enforce in the infrastructure.
7. **When was failover last tested live?** If "never," that's the highest-priority finding.
8. **What's the multi-region cost premium?** Active-passive ≈ 1.5–2× single-region (idle secondary). Active-active ≈ 2–3× (full secondary + coordination). The business needs to see and approve this.
9. **Can you operate in a single region during DR?** If a region is down permanently for hours, can the surviving region(s) carry full load? Capacity planning is often siloed per region.

## Common pitfalls

### Active-active for resilience without RTO/RPO forcing it

Already in `references/anti-patterns.md`; recurring here because geo-distributed designs are especially prone. The simpler active-passive design with a well-tested failover meets most resilience SLOs at a fraction of the cost.

### Synchronous cross-region replication

Every write blocks on cross-region round trip (150ms+). User-visible latency suffers; throughput drops. Synchronous cross-region is reserved for hard-RPO requirements (financial systems with regulatory mandate); everything else uses async.

### Forgetting DNS TTL in the failover plan

The plan says "in failover, change DNS to point at Region B." DNS TTL is 1 hour. For 1 hour, half the world still hits the dead Region A. Use TTL < 1 minute on records that participate in failover; better, use a load balancer (Route 53 health checks, Global Accelerator) that fails over in seconds.

### Failover runbook drift

The runbook was written 18 months ago. Service names changed. Connection strings changed. Environment variables changed. The runbook references things that no longer exist. Refresh annually at minimum.

### Replicating everything everywhere

"All data is in all regions for performance." But you only access 10% of the data from the secondary region; the rest is overhead. Per-region partitioning of cold data with cross-region for hot data significantly cheaper.

### Assuming database-level failover is the whole story

The database fails over; the application still has connections to the old database; the connection pool is configured for the old endpoint; the caches hold stale primary indicators. End-to-end failover is application-level.

### Ignoring stateful services in failover plans

The DB plan is clear. The Redis cache, the Kafka cluster, the search index, the object storage, the secrets store — each has its own failover semantics. Failover is N stateful systems, not one.

## Anchor numbers

- **Cross-region RTT**: typically **70–150ms** between regions on the same continent; **150–250ms** intercontinental; **> 250ms** for the longest hops (e.g., Sydney ↔ São Paulo).
- **Active-passive failover RTO**: realistically **minutes** (DNS propagation + connection draining + standby warm-up). Sub-minute requires significant engineering.
- **Active-active failover RTO**: realistically **seconds** (routing change at LB), but requires conflict-resolution machinery and pays cost continuously.
- **Replication lag (async)**: target **single-digit seconds**; alert at **tens of seconds**; lag of **minutes** is broken.
- **Multi-region cost premium**: active-passive ≈ **1.5–2×** single-region; active-active ≈ **2–3×** plus higher coordination overhead.
- **DNS TTL for failover-participating records**: **≤ 60 seconds** if failover relies on DNS; **0** (handled by L7 LB) is better.
- **Failover test cadence**: **quarterly** at minimum. Ideally tabletop monthly, live quarterly, full chaos exercise annually.

## Cross-archetype interactions

- **Geo-distributed + multi-tenant**: data residency rules constrain tenant→region mapping. EU tenants may be pinned to EU; cross-region tenants need conflict resolution per-record.
- **Geo-distributed + observability**: per-region metrics, alerting that doesn't depend on the failing region, log shipping that survives a regional outage.
- **Geo-distributed + write-heavy**: write-heavy + multi-region multiplies the bandwidth and coordination cost. Consider whether some writes can be region-local (no cross-region propagation needed).
- **Geo-distributed + read-heavy-mobile**: edge caching + CDN handles a lot of the "users are far away" problem without full multi-region for state. Only state that needs reads-and-writes locally requires real multi-region.
