# Architecture critique: <system name>

Reviewer: <name>
Date: YYYY-MM-DD
Status: Draft | Final
Scope: <full review | resilience-only | cost-only | consistency-only>

> Findings only. Not a redesign. If the user wants a redesign,
> switch to greenfield mode.

## Design under review

<3–5 line summary of the design being reviewed. Restate it back to
confirm shared understanding. Include the key components, scale,
and what the team believes the binding constraints are.>

## Constraints assumed

<The constraints the design was built against, as the team understands
them. Flag any that look mismatched in the findings below.>

- **Scale**: <current / projected>
- **Latency budget**: <p50, p99>
- **Availability SLO**: <X nines>
- **Read : write**: <ratio>
- **Operational reality**: <team size, on-call, existing stack>

## P0 findings — must fix before this design is safe in production

> P0 means: there's a credible failure path that hits users in
> normal operation, or a one-way door that will be expensive to
> reverse. Do not accept the design without addressing these.

### <Finding title>
**Binding constraint**: <what constraint this concerns>
**Symptom**: <what triggers this in the design>
**Smallest fix**: <the minimum change that resolves it>

### <Finding title>
**Binding constraint**: <...>
**Symptom**: <...>
**Smallest fix**: <...>

## P1 findings — should fix in the next quarter

> P1 means: the design works but carries known risk or unnecessary
> cost. Worth fixing within a reasonable time horizon.

### <Finding title>
**Binding constraint**: <...>
**Symptom**: <...>
**Smallest fix**: <...>

### <Finding title>
...

## P2 findings — worth knowing, can defer

> P2 means: a smell to be aware of. Decision can wait until a forcing
> signal appears.

### <Finding title>
...

## Open questions for the team

- <Question that surfaces a constraint the design didn't name.>
- <Question whose answer would change the priority of a finding above.>
- <...>

## Anti-pattern checklist walked

<Mark which patterns from `references/anti-patterns.md` fired during
the review. Helps the team see the full breadth of what was checked.>

- [ ] Premature microservices
- [ ] Premature sharding
- [ ] Distributed monolith
- [ ] Microservices for a small team
- [ ] Kafka for low-volume async
- [ ] Async-as-default
- [ ] Dual-write without outbox/CDC
- [ ] Exactly-once-delivery claim
- [ ] Polyglot persistence without justification
- [ ] MongoDB because schemas are restrictive
- [ ] Elasticsearch as system of record
- [ ] Time-series DB at small scale
- [ ] Custom consensus / leader election
- [ ] Multi-region active-active without RTO/RPO forcing it
- [ ] Retry without backoff / jitter / idempotency
- [ ] No bounded queues
- [ ] Liveness / readiness conflated
- [ ] Untested failover assumed working
- [ ] Synchronous dependency without timeout
- [ ] No degradation strategy / MVF
- [ ] Caching everything
- [ ] Future-proofing for hypothetical scale
- [ ] Resume-driven architecture
- [ ] Decisions without ADRs
- [ ] ADRs without sacrifices
- [ ] "We'll handle invalidation later"
- [ ] Happy-path-only design

## Next steps

<If user wants to act: which finding to tackle first, how. If user
wants to redesign: switch to greenfield mode and start fresh.>
