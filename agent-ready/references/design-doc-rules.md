# Design doc rules: citations and quality bar

Read this before filling in `templates/agent-design-doc.md`.

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

## Quality bar before declaring Phase 2 complete

- [ ] Section 1 doesn't reference unverified features. If you say "this app does X," X must be cited from README or feature-tagged code.
- [ ] Section 2 names actual entry points (e.g., `main.ts`, `cmd/server/main.go`, `Procfile` web process), not generic "the API layer."
- [ ] Section 3 lists each major struct/class with a citation. Not "we have models" but "`Payment` at `src/models/payment.ts:14`".
- [ ] Section 4 has at least one citation per algorithm. If the project has no non-trivial algorithms, say so explicitly and explain why (e.g., "this is a CRUD service; logic is form validation + DB writes").
- [ ] Section 5 has at least 3 numbered rules OR a `[NEEDS_CONTEXT]` placeholder explaining why none were found.
- [ ] Sections 6 and 7 are tables (or lists), not prose.
- [ ] Section 10 contains exactly the union of `[NEEDS_CONTEXT]` markers from §§3–9 — no more, no less.

If any check fails, the doc isn't done — go back and fix.
