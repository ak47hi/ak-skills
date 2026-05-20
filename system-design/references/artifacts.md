# Artifacts

Load when the work done in a session is worth surviving the conversation: ADRs for significant decisions, RFCs for full designs, capacity worksheets, postmortems, critiques, migration plans. This file defines **when to offer artifacts**, **how to name them**, **where they live**, and **the opt-in confirmation flow** that prevents surprising file creation.

## Default behavior: opt-in per artifact

The skill **never silently writes files**. After a full design or significant decision, the skill **offers** the artifacts that would be valuable, names the proposed paths, and waits for confirmation before writing.

The confirmation script is short, numbered, replaceable:

> I can write the following artifacts:
>
> 1. `docs/adrs/007-postgres-as-queue.md` (ADR for the queue choice)
> 2. `docs/adrs/008-redis-cache-strategy.md` (ADR for the cache layer)
> 3. `docs/rfcs/2026-05-notification-service.md` (the full RFC)
> 4. `docs/capacity/notification-service.md` (capacity worksheet)
>
> Confirm to write all, list specific numbers to write only those,
> or say "no thanks" to keep this conversational.

The user picks. The skill writes only what was confirmed.

## When to offer artifacts

Offer when the work produced is durable. Don't offer for ephemeral or narrow work.

| Mode and scope | Offer? |
|---|---|
| Greenfield, full design (all 8 sections of output template) | Yes — RFC + ADRs for significant decisions + capacity worksheet |
| Greenfield, narrow question ("Kafka vs PG-as-queue at 300 jobs/hr") | No — chat-mode answer is the deliverable |
| Greenfield, with explicit user request ("write this up as an RFC") | Yes, as requested |
| Review, prioritized findings | Offer critique document only if findings are substantial (typically 3+ P0/P1 findings) |
| Diagnose, smallest-fix proposal | No — output is conversational. Offer postmortem only if the user is writing one for an actual incident |
| Diagnose, full incident write-up requested | Yes — postmortem template |
| Evolve, migration plan with phases | Yes — migration plan + ADR for the chosen step |
| Evolve, "what's the next step" with single-sentence answer | No — chat-mode answer |
| User explicitly says "write this up" / "give me the ADR" / "save this" | Yes, regardless of scope |

**Default to no** when in doubt. The cost of an unnecessary artifact (clutter, stale doc) is higher than the cost of an extra conversational round to confirm.

## Significant choice criteria (what warrants an ADR)

From `references/tradeoffs.md`'s "When NOT to write an ADR" rules, repeated here for the artifact-offering decision. Offer an ADR when:

- The choice is a **one-way door** or expensive to reverse (shard key, identifier scheme, wire format, multi-region commitment).
- The choice adds **new operational surface** (a new datastore, a new service, a new dependency the team has to learn).
- The choice **deviates from team standards** (using something other than the default Postgres + Redis stack, for example).
- The choice involves a **non-obvious tradeoff** (consistency vs availability, batch vs streaming, polyglot vs single store).

Don't offer ADRs for:

- Two-way-door decisions with low impact (library choices, helper-function placement, naming conventions).
- Already-team-standard choices ("we use TypeScript" doesn't need an ADR).
- Implementation details below the architecture line.
- Decisions the team would never realistically reverse ("we use HTTPS").

A useful test: would someone joining the team six months from now ask "why did we do it this way?" and be confused without the context? If yes, ADR-worthy.

## File naming conventions

| Artifact | Path convention | Example |
|---|---|---|
| ADR | `docs/adrs/NNN-kebab-case-title.md` | `docs/adrs/007-postgres-as-queue.md` |
| RFC | `docs/rfcs/YYYY-MM-system-name.md` | `docs/rfcs/2026-05-notification-service.md` |
| Capacity worksheet | `docs/capacity/system-name.md` | `docs/capacity/notification-service.md` |
| Postmortem | `docs/postmortems/YYYY-MM-DD-incident-name.md` | `docs/postmortems/2026-05-12-kafka-rebalance.md` |
| Critique | `docs/reviews/YYYY-MM-system-name.md` | `docs/reviews/2026-05-billing-architecture.md` |
| Migration plan | `docs/migrations/YYYY-MM-from-to.md` | `docs/migrations/2026-05-monolith-to-billing-service.md` |

**ADR numbering**: sequential per repository, never reused. If the user already has ADRs at `docs/adrs/001-...md` through `docs/adrs/006-...md`, the next one is `007-`.

**Verify the directory exists** before offering paths. If `docs/adrs/` doesn't exist in the repo, offer to create it as part of writing the first ADR — don't assume it's there.

**Respect existing conventions**. If the user's repo already has ADRs in `architecture/decisions/` or `documents/adr/`, use that path. The skill's default is `docs/adrs/`, but the user's repo wins.

## Multi-file vs single-file artifacts

Some sessions naturally produce multiple files (RFC + several ADRs + capacity worksheet). Offer them as a batch with numbered paths so the user can selectively accept or reject. Don't bundle into one giant document — ADRs and RFCs serve different purposes and accumulate at different rates.

Some sessions produce a single artifact (a postmortem, a critique, a migration plan). Offer the one file.

## Cross-skill: invoking the plantuml skill for diagrams

System designs often benefit from diagrams (C4 container, sequence for a critical path, deployment for the infrastructure layout). The sibling `plantuml` skill in this repo renders these. The system-design skill **does not embed PlantUML output itself** — separation of concerns is preserved.

When a diagram would help, offer:

> A C4 container diagram of this design would be useful for the RFC.
> The `plantuml` skill renders it — say the word and I'll hand the
> design over to it, or invoke it inline and link the result.

The user decides whether to involve plantuml. If yes, the system-design skill describes the intended diagram in prose (participants, scope, type) and the plantuml skill takes over.

## What NOT to do with artifacts

### Don't silently write files

Even after the user has confirmed once, every new artifact in the same session is a separate offer. The first ADR doesn't auto-authorize the second.

### Don't write artifacts the user didn't see in chat first

The artifact reflects what was discussed. If the skill writes content the user hasn't reviewed conversationally, the user has no way to catch errors or misinterpretations before they're persisted.

### Don't overwrite without explicit confirmation

If the proposed path exists (e.g., `docs/adrs/007-postgres-as-queue.md` is already there), the skill asks:

> `docs/adrs/007-postgres-as-queue.md` already exists. Options:
> 1. Overwrite (loses the current contents).
> 2. Save as `008-postgres-as-queue.md` (next number).
> 3. Save with a `-v2` suffix.
> 4. Skip this artifact.

### Don't write to paths outside `docs/`

The artifact templates target documentation directories. Writing ADRs to `src/` or `lib/` is wrong. If the user explicitly specifies a non-docs path, fine; default proposals stay in `docs/`.

### Don't write secrets, credentials, or internal-only details

Capacity worksheets, ADRs, and RFCs often discuss infrastructure. They should be safe to commit. Watch for: API keys quoted in the user's prompt (don't echo into the artifact), internal hostnames that shouldn't be public, customer names that breach confidentiality. When in doubt, ask before writing.

## Iteration on artifacts

After writing, the user may want changes. Edit the file directly using whatever editing tools are available; don't rewrite from scratch. Preserve the file's structure, timestamps, and prior content unless the change requires it.

If the user wants a draft for review first ("show me the ADR before writing"), the skill renders it inline in chat and waits for "looks good, write it" before saving.

## Updating prior artifacts

For long-running systems, artifacts get superseded. When a new decision overrides an old ADR:

- Add **Status: Superseded by ADR-NNN** to the old ADR (don't delete it; the history is the value).
- New ADR has **Status: Accepted** and the Context section references what changed.

For RFCs:

- Major redesigns get a **new** RFC, not edits to the old one.
- Mark the old one **Status: Superseded by RFC-YYYY-MM-...**.

ADRs and RFCs are **append-only and immutable** in spirit, even when stored in a mutable filesystem. The discipline preserves the reasoning trail.
