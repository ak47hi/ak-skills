# Migration plan: <system or component>

Author: <name>
Date: YYYY-MM-DD
Status: Draft | Approved | In progress | Complete | Rolled back

> Evolution, not rewrite. The next step from the current system,
> with parallel-write windows and two-way doors at every choice point.

## Current state

<3–5 lines on what's running today: architecture, scale, datastore
choices, operational baseline. The thing the team is comfortable
with — the cost of changing it is real.>

## The wall

<The specific binding constraint that forces a step. With numbers.>

- **Constraint**: <what's saturating / breaking / about to break>
- **Current measurement**: <numbers>
- **Projected**: <12-month projection that exceeds capacity>
- **What's been tried**: <vertical scaling? replicas? caching? indexes?>

## Next step (proposed)

<The smallest move from the scaling order of reach in
`references/patterns.md` (or storage ladder in `references/datastores.md`)
that addresses the wall.>

- **Move**: <vertical → horizontal stateless | + read replicas |
  + caching | + sharding | extract one service | single-region →
  active-passive multi-region | etc.>
- **Why this step (not a bigger or smaller one)**: <one paragraph>
- **What this step does NOT address**: <honest about which other
  constraints remain>

## Migration phases

> Each phase is independently reversible where possible. Two-way doors
> at every choice point.

### Phase 1: <name> (estimated <duration>)

- **Actions**: <bullet list of concrete changes>
- **Rollback procedure**: <how to revert this phase if needed>
- **Success signal**: <metric or behavior that confirms this phase
  is working before moving to phase 2>
- **One-way doors in this phase**: <any irreversible choices, with
  named alternatives considered>

### Phase 2: <name> (estimated <duration>)

...

### Phase N: decommission old (after <safety window>)

- **Actions**: <stop writes to old, retain data for N days, then
  remove>
- **Why a safety window**: <rollback is still possible during the
  window if a hidden bug surfaces>

## Parallel-write window (if storage touched)

> Skip this section if migration doesn't touch persistent storage.

| Period | Reads from | Writes to |
|---|---|---|
| Before | old | old |
| During (parallel-write) | old | both old and new (or new with reverse-replication to old) |
| Cutover (reads flipped) | new | both |
| After | new | new |
| Decommission | new | new (old removed after safety window) |

**Verification during parallel-write**: <how to confirm the new store
has correct data — row counts, checksums, sample comparisons,
shadow reads, etc.>

## Rollback plan

<For each phase, what triggers a rollback and how it's executed.
Tested in dev before phase 1 ships in prod.>

| Trigger | Action |
|---|---|
| <Specific symptom — e.g. p99 latency exceeds budget> | <Revert phase X> |
| <Data inconsistency between old and new> | <Pause writes, investigate> |
| <Rollback in phase N+1 reveals dependency on phase N> | <Roll back phase N+1, leave phase N> |

## Success signals

<What confirms the migration worked. Specific metrics, specific
thresholds, observed over a defined period.>

- <Signal 1: e.g., 'p99 latency < target for 7 consecutive days
  under peak load'>
- <Signal 2>
- <Signal 3>

## Next wall (after this step)

<Honestly name the next constraint this design will hit. Each step
buys time, not infinity. Knowing the next wall helps the team plan.>

- **Expected next wall**: <description>
- **Likely signal**: <metric crossing threshold>
- **Likely next step**: <the move after this one>

## Operational changes

<What the team has to do differently after this migration.>

- New runbooks: <list>
- Updated monitoring / alerting: <list>
- New on-call dependencies: <list>
- Cost change: <delta in $/month>

## Open questions

<Things deferred to during-migration learning.>

- <Question that gets answered by phase N's success signals>
- <...>
