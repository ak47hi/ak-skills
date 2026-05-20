# ADR-NNN: <decision title>

Status: Proposed | Accepted | Superseded by ADR-MMM
Date: YYYY-MM-DD
Owner: <name or team>

## Context

<What's the situation that demands a decision? 2–4 short paragraphs.
Name the binding constraint. Include the relevant numbers
(scale, latency, SLO, team size, existing stack). Avoid narrative
filler — every sentence should change what the reader builds.>

## Decision

<What we're doing. One paragraph. Imperative voice. No hedging.>

## Alternatives considered

- **<Alternative name>.** <What it is, in one sentence.> Why we didn't
  pick it: <name the specific constraint it failed to satisfy, not a
  vague preference>.
- **<Alternative name>.** <One sentence.> Why we didn't pick it: <...>.
- **<Alternative name>.** <One sentence.> Why we didn't pick it: <...>.

## Consequences

### Positive
- <What gets easier or better.>
- <...>

### Negative / new failure modes
- <What's harder, riskier, or newly possible to break. Be specific —
  "may have replication lag bugs" beats "may have issues".>
- <...>

### What to monitor
- <Metric or signal that tells us this decision is working.>
- <Metric or signal that would tell us it's not.>

### Reversal cost
<One-way door or two-way door? If one-way, what would force a reversal
and what would the reversal involve (estimate engineer-weeks, data
migration, downtime)?>

## Open questions

- <Deferred question with a deadline or trigger ("revisit when write
  QPS exceeds 10k").>
- <...>
