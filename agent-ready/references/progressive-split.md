# Progressive disclosure split (Phase 2.4)

## When to split

Split if and only if:
- `--no-split` was NOT passed, AND
- `AGENT_DESIGN_DOC.md` has > 200 lines after Phase 2

(The threshold exists because below it, single-file is faster to scan; above it, the doc becomes scrollware and important rules get buried.)

## What stays in `AGENT_DESIGN_DOC.md` (the slim version)

After split, the slim doc keeps:

- **Section 1 (What This Project Does)** — in full
- **Section 2 (Architecture)** — in full, including the diagram
- **Section 5 (Business Logic Rules)** — only the **top 10 most critical rules**, inline. Below them, a pointer: `→ Full list in .agent-docs/business-rules.md (N additional rules)`.
- **Sections 3, 4, 6, 7, 8, 9** — replaced with 1–2-sentence summaries, each ending in `→ See .agent-docs/<file>.md`.
- **Section 10 (Open Questions)** — in full

### Top-10-rule selection criteria for §5

Pick the rules that are most likely to cause an agent to make a wrong assumption if it doesn't know them. In rough priority order:

1. Money / billing / financial constraints (caps, limits, fees, refund windows)
2. Security / auth boundaries (who can do what, when)
3. Data integrity invariants (uniqueness, ordering, immutability)
4. Time-based rules (expirations, TTLs, retry windows)
5. State-machine transition constraints
6. Anything explicitly called out as a regulatory / compliance requirement
7. External-API contract rules (rate limits, idempotency, ordering guarantees)
8. Concurrency rules (locking, ordering, fan-out limits)
9. User-visible behaviour rules (what triggers notifications, what's user-facing vs internal)
10. Operational rules (rollout, feature-flag, kill-switch behaviour)

Skip purely-internal helper-function rules; those go in `.agent-docs/business-rules.md`.

## What moves into `.agent-docs/`

Create the directory `.agent-docs/` at the project root. Move sections 3–9 into individual files, **preserving all `[NEEDS_CONTEXT]` markers verbatim**:

| Source section | Target file |
|---|---|
| §3 Core Data Structures | `.agent-docs/data-structures.md` |
| §4 Key Algorithms | `.agent-docs/algorithms.md` |
| §5 Business Logic Rules (all rules; not just top 10) | `.agent-docs/business-rules.md` |
| §6 External Dependencies | `.agent-docs/integrations.md` |
| §7 Configuration & Tunables | `.agent-docs/configuration.md` |
| §8 Error Handling | `.agent-docs/error-handling.md` |
| §9 Testing Strategy | `.agent-docs/testing.md` |

Each `.agent-docs/*.md` file should have its own `# <Title>` at the top and the full section content underneath.

## Pointer format (in the slim doc)

For each replaced section, use this exact pattern:

```markdown
## 3. Core Data Structures

<1–2 sentence summary of what's in this section>

→ See `.agent-docs/data-structures.md`
```

## Invariants — verify all of these before Phase 2.4 is done

1. **Line count:** slim `AGENT_DESIGN_DOC.md` < 200 lines.
2. **`[NEEDS_CONTEXT]` conservation:** count markers in the slim doc + every `.agent-docs/*.md` file. The total must equal the count in the pre-split `AGENT_DESIGN_DOC.md`. If a marker was in §5 and that rule made the top 10, it can appear in both the slim doc and `.agent-docs/business-rules.md` — count both occurrences (they're not duplicates, they're a slim-doc copy + canonical home).
3. **All pointers resolve:** every `→ See .agent-docs/<file>.md` must point to a file that exists.
4. **Files exist:** all 7 `.agent-docs/*.md` files exist (even if a section was sparse; an almost-empty file with `[NEEDS_CONTEXT]: This section was sparse — needs more analysis` is acceptable).
5. **Section 10 unchanged:** the open-questions list still mirrors the union of all `[NEEDS_CONTEXT]` markers across all files.

If any invariant fails, fix before moving to Phase 2.5 / 3.

## Why split at all?

Two reasons:

1. **Reading cost:** loading an 800-line design doc into every future agent session burns context for parts the current task doesn't need. The slim doc is the "always load" tier; `.agent-docs/*.md` files are pulled in only when relevant.
2. **Editing cost:** when a human resolves a `[NEEDS_CONTEXT]` for one section, smaller files are less likely to merge-conflict and easier to review.
