# AGENT_DESIGN_DOC.md — skeleton

This is the literal structure the model produces in Phase 2. Citation rules and the quality bar live in `references/design-doc-rules.md` — read that before filling this skeleton in.

Fill each `<...>` block with content; preserve section numbering and headings exactly.

```markdown
# AGENT_DESIGN_DOC.md

## 1. What This Project Does

<2–4 paragraphs. Plain English. What problem this solves, who uses it, the
primary value prop. No file citations needed for the elevator pitch, but
specific feature claims should still cite README or docs.>

## 2. Architecture

<High-level diagram (Mermaid `flowchart TB` if appropriate, else prose).
Identify entry points (CLI, HTTP handler, message consumer, library API)
and the major subsystems they delegate to. Cite each subsystem's primary
file. Aim for 5–10 nodes/concepts max — this is the bird's-eye view.>

## 3. Core Data Structures

<For each major domain object: name, fields, invariants. Cite the type
definition. Example:

### `Payment`
- Fields: `id`, `amount`, `currency`, `status`, `idempotency_key`
- Invariants: `amount > 0`, `status` ∈ {pending, captured, refunded, failed}
- Definition: `src/models/payment.ts:14-32`
- State transitions: `src/models/payment.ts:45-78` (see also business-rules)>

## 4. Key Algorithms

<For each non-trivial algorithm: what it does, when it's invoked, complexity
notes, edge cases. Cite the implementation. Example:

### Idempotency-key dedup
- Hashes request body + key, stores in Redis with 24h TTL
  (`src/payments/idempotency.ts:42-91`)
- Collision behaviour: returns cached response without re-executing
  (`src/payments/idempotency.ts:103-117`)
- [NEEDS_CONTEXT]: What happens on Redis unavailability — fail open or fail closed?>

## 5. Business Logic Rules

<Numbered list of business rules. Each rule cites the file:line where it's
enforced. Example:

1. Refunds may only be issued within 90 days of capture
   (`src/refunds/eligibility.ts:23`)
2. A merchant's daily payout cap is 10,000 USD unless the `unlimited_payouts`
   flag is set (`src/payouts/limits.ts:55-67`)
3. Subscription renewals retry up to 3 times over 7 days before cancellation
   (`src/billing/dunning.ts:88-102`)

If you can't find a rule's enforcement point, write it as:
N. [NEEDS_CONTEXT]: Is there a maximum number of failed login attempts before account lockout?>

## 6. External Dependencies

<Table of external services, libraries, and infrastructure. Cite where each
is configured/used.

| Dependency | Purpose | Where used |
|---|---|---|
| Stripe API | Payment processing | `src/stripe/client.ts:1-45` |
| Redis | Idempotency cache + rate limits | `src/cache/redis.ts:8-22` |
| Postgres | Primary data store | `migrations/`, `src/db/pool.ts:5-18` |
>

## 7. Configuration & Tunables

<Table of env vars, config files, feature flags. Cite where each is read/defined.

| Name | Default | Where read | Effect |
|---|---|---|---|
| `MAX_BATCH_SIZE` | 100 | `config/batch.py:8` | Batch processor flush size |
| `RETRY_CAP` | 5 | `internal/retry/policy.go:18` | Max retry attempts |
>

## 8. Error Handling

<How the system handles errors at major boundaries. Cite the error types
and the catch/recover sites. Example:

- HTTP boundary: 4xx vs 5xx classification at `src/http/errors.ts:14-58`
- Payment failures: distinguished as retriable (network) vs terminal
  (declined card) at `src/payments/errors.ts:22-44`
- Background jobs: dead-letter queue after N retries, see `src/queue/dlq.ts:9-31`
- [NEEDS_CONTEXT]: Is there structured logging or just stderr?>

## 9. Testing Strategy

<What's tested, what isn't, how to run tests. Cite the test config and CI.

- Test runner: <tool> (`<config-file>:<line>`)
- Unit test coverage: <file/dir patterns>
- Integration tests: <where>
- E2E / acceptance: <where, or "none">
- CI runs: <link to .github/workflows or .gitlab-ci.yml>
- [NEEDS_CONTEXT]: Is there a fixture or seed-data convention?>

## 10. Open Questions

<List every [NEEDS_CONTEXT] marker collected across the doc — copied verbatim,
numbered. Anyone reading this section gets the full backlog of unresolved
questions. Example:

1. [NEEDS_CONTEXT]: What happens on Redis unavailability — fail open or fail closed?
2. [NEEDS_CONTEXT]: Is the `MAX_BATCH_SIZE` constant applied per-request or per-tenant?
3. [NEEDS_CONTEXT]: Is there structured logging or just stderr?>
```
