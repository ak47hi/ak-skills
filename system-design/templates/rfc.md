# RFC: <title>

Author: <name>
Date: YYYY-MM-DD
Status: Draft | Under review | Approved | Implemented | Withdrawn
Reviewers: <names>

## Summary

<1–3 sentences. What this RFC proposes and the binding constraint
that forced the proposal.>

## Motivation

<Why now? What's the situation that demands this design? Include
the numbers (current scale, projected scale, current pain, SLO).
This section is the "context" of the whole RFC; everything else
derives from it.>

## Constraints

<The elicited dimensions. Flag inferred / assumed values explicitly.>

- **Functional core**: <2–3 dominant operations>
- **Scale**: current <N>, 12-month projection <N>, peak factor <N>
- **Latency budget**: p50 < <X>ms, p99 < <Y>ms for the dominant operation
- **Consistency**: <per-operation requirements>
- **Availability SLO**: <X nines>
- **Read : write ratio**: <X : Y>
- **Operational reality**: <team size, on-call, existing stack>
- **Archetype(s)**: <multi-tenant SaaS / streaming / etc., if any apply>

## Capacity estimate

<Peak QPS, storage/yr, bandwidth, working set. Include the
single-machine baseline check: does this fit one box with headroom?
If yes, distribution must be justified by something other than
throughput.>

## Proposed design

<The architecture. Components, boundaries, sync vs async per boundary,
data flow. Keep as flat as the SLO allows. Name what crosses a process
boundary; everything else is internal.>

### Data model and storage

<Per-operation consistency. Per-store justification. Count consistency
boundaries.>

### Critical paths

<For each user-visible flow: which dependencies are on the critical
path, which can degrade gracefully, what's the minimum viable function?>

## Scaling the bottleneck

<The single binding bottleneck under projected load. The smallest
scaling step that addresses it. What forces the next step after that.>

## Failure modes and mitigations

<Per dependency: slow / down / wrong. Timeouts, retries, circuit
breakers, bulkheads, idempotency, degradation strategy.>

## Alternatives considered

- **<Alt 1>**: <one sentence>. Not chosen because <binding constraint
  it failed to satisfy>.
- **<Alt 2>**: <one sentence>. Not chosen because <...>.

## Decisions (ADRs)

<List of significant choices that warrant their own ADRs. One link
each. The ADRs carry the per-decision detail; this RFC carries the
overall design.>

- [ADR-NNN: <title>](../adrs/NNN-<slug>.md)
- [ADR-MMM: <title>](../adrs/MMM-<slug>.md)

## Rollout

<How does this ship? Phased? Behind a flag? Parallel-write window
for storage migrations? Rollback procedure?>

## Success metrics

<What measurable signals tell us this design is working in production?
SLO compliance, specific latency / error / cost metrics, business KPIs
if relevant.>

## Open questions

<Deferred questions with deadlines or triggers.>

## References

<Links to relevant background: prior incidents, related RFCs,
benchmark data, vendor docs.>
