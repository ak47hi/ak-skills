---
name: agent-ready
description: Prepares a repository for AI agents by generating a knowledge graph (via understand-anything), a cited AGENT_DESIGN_DOC.md, and optionally an ARCHITECTURE.md with Mermaid diagrams, then wires CLAUDE.md and commits only the generated artifacts. Accepts flags --skip-understand, --skip-commit, --architecture, --no-split. Use when the user says "make this repo agent-ready", "prepare this codebase for AI agents", "generate an agent design doc", "create a knowledge graph for this project", "onboard Claude to this repo", "bootstrap agent docs", "add CLAUDE.md and design doc", "make this codebase Claude-ready", "set up auto-updating project documentation", or runs `/agent-ready`. Phases run sequentially; only the CLAUDE.md merge prompts the user. Do NOT use for one-off code reviews, README generation, existing-doc edits, or non-repo single-file tasks.
---

# agent-ready

Prepares any git repository for AI agents (Claude, Codex, Cursor, Copilot, Gemini CLI, etc.) by orchestrating:

1. A **knowledge graph** via the [understand-anything](https://github.com/Lum1104/Understand-Anything) plugin
2. A **cited Agent Design Document** (`AGENT_DESIGN_DOC.md`) with every claim traceable to `file:line`
3. Optionally an **architecture overview** (`ARCHITECTURE.md`) with validated Mermaid diagrams
4. A wired **`CLAUDE.md`** that imports the design doc and the Karpathy Guidelines
5. A single **local commit** containing only the generated artifacts (no push, no `Co-Authored-By`, no `git add .`)

This skill orchestrates existing tools — it does **not** reimplement knowledge-graph construction, graph review, or Mermaid rendering. Those are delegated to `understand-anything` and `mmdc`.

---

## Flags

| Flag | Effect |
|---|---|
| `--skip-understand` | Skip Phase 1 (don't run `/understand`). Use when the KG is already current. |
| `--skip-commit` | Skip Phase 5 (don't stage/commit). Useful when the user wants to review first. |
| `--architecture` | Run Phase 2.5 to generate `ARCHITECTURE.md`. Persist `"architecture": true` in `.understand-anything/config.json`. |
| `--no-split` | Skip Phase 2.4 progressive disclosure (keep `AGENT_DESIGN_DOC.md` as a single file regardless of length). |

Parse flags from the user's invocation. Unrecognized flags → abort with a clear error listing the valid set.

---

## Hard dependencies

These MUST be invoked rather than reimplemented:

- **`understand-anything` plugin** — provides `/understand`. Install: `/plugin marketplace add Lum1104/Understand-Anything && /plugin install understand-anything`. Writes `.understand-anything/{knowledge-graph,config,meta,fingerprints}.json`.
- **`mmdc` (Mermaid CLI)** — used for diagram validation in Phase 2.5. Install: `npm install -g @mermaid-js/mermaid-cli`. If missing, Phase 2.5 logs a warning and emits diagrams without validation; never silently skips them.
- **`git`** — Phase 5 only. Used for `git add <allowlisted-paths>` and `git commit`. Never `git push`, never `--no-verify`, never `--amend`, never `git add .` / `-A` / `*`.

If `/understand` is not available when Phase 1 runs, abort with: *"The `understand-anything` plugin is not installed. Install it via `/plugin marketplace add Lum1104/Understand-Anything` then `/plugin install understand-anything`, then re-run `/agent-ready`."*

---

## Strict rules (apply throughout)

These rules exist because agent docs that hallucinate are worse than no docs — they erode the trust the rest of this skill is trying to build. Read carefully.

1. **Every algorithm / business-rule claim cites `file:line`.** If you can't cite, you can't claim — write `[NEEDS_CONTEXT]: <specific question>` instead. Paraphrasing logic without source backing is forbidden.
2. **Mermaid edges must trace to a knowledge-graph edge or a documented data flow.** Don't infer relationships from naming or proximity. If a flow isn't in the KG and you can't find it in source, omit the edge.
3. **Prefer fewer accurate diagram edges over more speculative ones.** A small correct diagram beats a large wrong one.
4. **Phase 5 banned patterns:** `git add .`, `git add -A`, `git add *`, `git push`, `git push --force`, `--no-verify`, `--amend`, any `Co-Authored-By:` trailer (the user's global CLAUDE.md hard-bans this).
5. **Only Phase 3 prompts the user.** All other phases run autonomously; if you find yourself wanting to ask the user a question, you're probably about to violate rule 1 — write `[NEEDS_CONTEXT]` instead.

---

## Phase sequence

Execute strictly in order. Stop and report on first hard failure.

### Phase 1 — Knowledge graph

Skip if `--skip-understand` was passed.

Invoke `/understand --auto-update --review`. If `--review` is not supported by the installed version, fall back to `/understand --auto-update` and log the deviation. The plugin handles all KG construction, file fingerprinting, and config writing.

**Verify before continuing:**
- `.understand-anything/knowledge-graph.json` exists and is non-empty
- `.understand-anything/config.json` contains `"autoUpdate": true` (add if missing)

If `/understand` fails, halt — do not proceed to Phase 2 with a stale or missing KG.

### Phase 2 — Agent Design Document

Read `.understand-anything/knowledge-graph.json` to identify: entry points, core data structures, key algorithms, public API surface, error-handling boundaries. Then read the actual source files those references point to — the KG is a starting map, not the source of truth for claims.

Write `AGENT_DESIGN_DOC.md` at the project root with **exactly 10 sections** in this order:

1. What This Project Does
2. Architecture (high-level diagram or prose)
3. Core Data Structures
4. Key Algorithms
5. Business Logic Rules
6. External Dependencies
7. Configuration & Tunables
8. Error Handling
9. Testing Strategy
10. Open Questions tracker

**Read `references/design-doc-template.md` for the full template, the `[NEEDS_CONTEXT]` syntax, and concrete examples of good vs. bad citations.**

### Phase 2.4 — Progressive disclosure split

Skip if `--no-split` was passed OR if `AGENT_DESIGN_DOC.md` is ≤ 200 lines.

Move sections 3–9 into individual files under `.agent-docs/`:
- `data-structures.md`, `algorithms.md`, `business-rules.md`, `integrations.md`, `configuration.md`, `error-handling.md`, `testing.md`

Rewrite `AGENT_DESIGN_DOC.md` slim: sections 1, 2, 10 in full; 3–9 as 1–2-sentence summaries with `→ See .agent-docs/<file>.md` pointers; section 5 retains the top-10 most-critical rules inline.

**Invariants (must hold after split):**
- Slim `AGENT_DESIGN_DOC.md` < 200 lines
- Total `[NEEDS_CONTEXT]` count across slim + `.agent-docs/*.md` equals the count before the split (zero loss)
- Every section pointer resolves to an existing file

**Read `references/progressive-split.md` for the rewrite rules and the top-10-rule selection criteria.**

### Phase 2.5 — Architecture (only if `--architecture`)

Generate `ARCHITECTURE.md` as a **pure transform** of `AGENT_DESIGN_DOC.md` + `.understand-anything/knowledge-graph.json`. **Do NOT re-read source files in this phase** — that's the design doc's job; this phase exists to visualize what's already documented.

Required sections:

1. Summary (one paragraph)
2. Component flowchart (`flowchart TB`)
3. 2–3 sequence diagrams for the top user-facing flows
4. Data model (ER or class diagram)
5. Dependency graph
6. Config table
7. Open Questions (copied from design doc §10)

**Mermaid validation loop:** For each Mermaid block, write to a temp file and run `scripts/validate-mermaid.sh <tmpfile>`. On failure, apply up to **2 fix attempts** using the rules in `references/architecture.md`. If still failing, prepend `%% VALIDATION WARNING: <stderr-summary>` to the block — do NOT delete unvalidated blocks.

After ARCHITECTURE.md is written and validated, merge `"architecture": true` into `.understand-anything/config.json`.

**Read `references/architecture.md` for the Mermaid reserved-keyword blocklist, label character rules, and the fix-attempt heuristics.**

### Phase 3 — CLAUDE.md merge (THE ONLY USER-PROMPTING PHASE)

Ensure `CLAUDE.md` at the project root contains:
1. The line `@AGENT_DESIGN_DOC.md` (create the file if it doesn't exist)
2. A `## Karpathy Guidelines` section (verbatim block — see `references/karpathy-guidelines.md`) IF that heading isn't already present

Construct the proposed file content. If `CLAUDE.md` exists, compute a unified diff (`diff -u <current> <proposed>`); otherwise show the proposed content with a `+` prefix on each line. Print the diff inside a fenced ```diff block.

Then call `AskUserQuestion` with:
- `question`: "Apply this CLAUDE.md change?"
- `options`: `["Yes, apply"], ["No, only add @AGENT_DESIGN_DOC.md line"], ["Abort"]`

On **"Yes"**: write the proposed content.
On **"No"**: ensure CLAUDE.md contains only the `@AGENT_DESIGN_DOC.md` line (append if needed); do NOT add Karpathy.
On **"Abort"**: stop the skill before Phase 4. Report what was generated and what was rolled back.

**Read `references/claude-md-merge.md` for diff formatting details and the rejection-fallback algorithm.**

### Phase 4 — Verify & report

Confirm all of the following and print a summary:

- `.understand-anything/config.json` contains `"autoUpdate": true`
- `AGENT_DESIGN_DOC.md` exists and is non-empty
- `CLAUDE.md` contains `@AGENT_DESIGN_DOC.md` (line, not just substring in another context)
- Total `[NEEDS_CONTEXT]` count across `AGENT_DESIGN_DOC.md` and `.agent-docs/*.md` (if split)
- If split: slim doc < 200 lines AND `.agent-docs/` has the expected 7 files AND every pointer resolves
- If `--architecture`: `ARCHITECTURE.md` exists, has 4–6 Mermaid blocks, and each either validated or carries `%% VALIDATION WARNING`
- If `--architecture`: `.understand-anything/config.json` has `"architecture": true`

If any check fails, report it but do not auto-fix in this phase — the failure indicates an earlier-phase bug worth surfacing.

### Phase 5 — Commit

Skip if `--skip-commit` was passed.

**Read `references/commit-safety.md` for the exact bash template, the allowlist, and the post-stage guard.** Use that template verbatim — do not rewrite it.

Commit message (exact): `feat: make repo agent-ready with knowledge graph auto-update and design doc`

**Banned in this phase** (reinforcing the strict rules above):
- `git add .`, `git add -A`, `git add *`
- `git push`, `git push --force`
- `--no-verify`, `--amend`
- Any `Co-Authored-By:` trailer (user's global CLAUDE.md hard-bans this; no exceptions)

If the post-stage grep guard reports unexpected files staged, **abort the commit** and report which files were unexpected — do not unstage and retry.

---

## Auto-refresh behaviour

When the `understand-anything` post-commit hook re-fires `/understand --auto-update`:

- If `.understand-anything/config.json` has `"architecture": true` AND `ARCHITECTURE.md` exists, re-run **only Phase 2.5** (re-read design doc + `.agent-docs/`; do NOT regenerate the design doc, since that would lose `[NEEDS_CONTEXT]` markers the human has been resolving).
- If `AGENT_DESIGN_DOC.md` is older than `.understand-anything/knowledge-graph.json`, print: *"⚠ Design doc is older than the KG. Consider running `/agent-ready --skip-understand --architecture` to refresh."*

**Read `references/auto-refresh.md` for the full re-entry decision tree.**

---

## When things go wrong

| Symptom | Action |
|---|---|
| `/understand` not found | Surface install commands. Halt Phase 1. |
| `mmdc` not installed and `--architecture` passed | Emit ARCHITECTURE.md without validation; warn user; do NOT skip the phase. |
| Working tree dirty when Phase 5 starts | Abort. The user has uncommitted changes; mixing them into the agent-ready commit violates the "only generated files" rule. |
| Phase 5 grep guard fires | Abort commit; report which files were unexpected; do NOT unstage. |
| User aborts Phase 3 | Stop before Phase 4. Report what was generated and that no CLAUDE.md change was made. |
