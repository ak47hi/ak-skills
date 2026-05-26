# AGENT_DESIGN_DOC.md — template and citation rules

This is the structure the model must produce when writing the design doc in Phase 2.

## The cardinal rule: cite or mark

Every algorithm, business rule, data structure, configuration value, error code, or external dependency claim must be traceable to source. The format is:

```
<claim or statement> (`path/to/file.ext:LINE`)
```

When you can't find the source — or you find ambiguity — use:

```
[NEEDS_CONTEXT]: <a specific, answerable question>
```

**Examples:**

Good:
- "Idempotency keys expire after 24 hours (`src/payments/idempotency.ts:42`)."
- "Retry uses exponential backoff with jitter, capped at 5 attempts (`internal/retry/policy.go:18-27`)."
- "[NEEDS_CONTEXT]: Is the `MAX_BATCH_SIZE` constant in `config/batch.py:8` applied per-request or per-tenant?"

Bad (forbidden — no citation, paraphrased logic):
- "The retry policy uses exponential backoff."
- "Payments are processed asynchronously through a queue."
- "Users can authenticate via OAuth or API key."

If you find yourself wanting to write a Bad line, stop and either find the file:line OR write a `[NEEDS_CONTEXT]` question.

---

## The 10 sections (exact order, exact headings)

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

---

## Quality bar before declaring Phase 2 complete

- [ ] Section 1 doesn't reference unverified features. If you say "this app does X," X must be cited from README or feature-tagged code.
- [ ] Section 2 names actual entry points (e.g., `main.ts`, `cmd/server/main.go`, `Procfile` web process), not generic "the API layer."
- [ ] Section 3 lists each major struct/class with a citation. Not "we have models" but "`Payment` at `src/models/payment.ts:14`".
- [ ] Section 4 has at least one citation per algorithm. If the project has no non-trivial algorithms, say so explicitly and explain why (e.g., "this is a CRUD service; logic is form validation + DB writes").
- [ ] Section 5 has at least 3 numbered rules OR a `[NEEDS_CONTEXT]` placeholder explaining why none were found.
- [ ] Sections 6 and 7 are tables (or lists), not prose.
- [ ] Section 10 contains exactly the union of `[NEEDS_CONTEXT]` markers from §§3–9 — no more, no less.

If any check fails, the doc isn't done — go back and fix.
