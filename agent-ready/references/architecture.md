# Architecture generation (Phase 2.5)

This phase runs only when `--architecture` is passed.

## The transform rule

`ARCHITECTURE.md` is a **pure transform** of `AGENT_DESIGN_DOC.md` (slim or full) + `.agent-docs/*.md` (if split) + `.understand-anything/knowledge-graph.json`. **Do not re-read source files in this phase.** The design doc has already done that work and added citations; this phase exists to visualize what's documented, not to re-derive it.

If you find yourself wanting to open a `.ts`/`.go`/`.py` file in this phase, stop — the right move is to add a `[NEEDS_CONTEXT]` to the design doc and re-run Phase 2, not to bypass it here.

## Required sections (exact order)

```markdown
# ARCHITECTURE.md

## 1. Summary

<One paragraph. What the architecture is and the dominant style
(monolith, microservices, event-driven, layered, hexagonal, etc.). Derived
from AGENT_DESIGN_DOC.md §1 + §2.>

## 2. Component flowchart

```mermaid
flowchart TB
    <nodes and edges>
```

## 3. Sequence diagrams (2–3 top flows)

<For each of the top 2–3 user-facing or operationally-critical flows
identified in the design doc, one sequenceDiagram block.>

```mermaid
sequenceDiagram
    <participants and messages>
```

## 4. Data model

<ER or class diagram, derived from §3 of the design doc.>

```mermaid
erDiagram
    <entities and relationships>
```

OR

```mermaid
classDiagram
    <classes and relationships>
```

## 5. Dependency graph

<External dependencies, libraries, and infrastructure derived from §6.>

```mermaid
flowchart LR
    <project node> --> <each dep>
```

## 6. Config table

<Reproduce §7 as a markdown table — no Mermaid here.>

## 7. Open Questions

<Verbatim copy of AGENT_DESIGN_DOC.md §10.>
```

## Mermaid rules — the reserved-keyword blocklist

The Mermaid parser will choke on the following words used as **participant IDs** or **node IDs**. Rename them (suffix with `_node`, `_actor`, `_svc` as appropriate):

```
loop, alt, else, opt, par, end, note, link, callback, click, class
```

For example: `loop` (bad) → `loop_actor` (good), `end` (bad) → `end_node` (good).

## Mermaid rules — label characters to avoid

The following characters break Mermaid label parsing when used inside `[label]`, `(label)`, `{label}`, or as a sequence-diagram message:

- `(` and `)` — use word "of" or hyphen
- `:` — use hyphen or word "for"
- `;` — use comma
- `#` — use word "num" or "id"
- `&` — use word "and"

Example: `Process(POST /api/v1)` → `Process POST v1 API`

## Mermaid rules — directive

Use `flowchart TB` (top-to-bottom) for component graphs and `flowchart LR` (left-to-right) for dependency graphs. Don't use `graph TD`/`graph LR` (the older syntax; `flowchart` is the modern equivalent).

## Mermaid rules — edge tracing

**Every edge in your component flowchart must trace to either:**
- An edge in `.understand-anything/knowledge-graph.json`, OR
- A data flow explicitly documented in `AGENT_DESIGN_DOC.md` (or `.agent-docs/*.md`)

Do NOT infer edges from naming similarity (`UserService` calls `User`) or filesystem proximity (`src/auth/login.ts` calls `src/auth/session.ts`). If you can't trace it, omit it. **A small correct diagram beats a large wrong one.**

## Validation loop (per Mermaid block)

For each fenced ```mermaid block in `ARCHITECTURE.md`:

```bash
TMP=$(mktemp --suffix=.mmd)
echo "<block contents>" > "$TMP"
bash scripts/validate-mermaid.sh "$TMP"
RC=$?
rm -f "$TMP"
```

If `RC != 0`:

**Fix attempt #1: reserved-keyword scan.** Search the block for any of the reserved keywords used as a participant or node ID; rename. Re-validate.

**Fix attempt #2: label-character scan.** Search the block for any of the blocked characters inside `[]`, `()`, `{}`, or after `->>:`/`->>` in sequence diagrams; replace per the table above. Re-validate.

If still failing after both attempts:
- Prepend the block with `%% VALIDATION WARNING: <one-line summary of stderr>`
- Do NOT delete the block — a broken-but-visible diagram is more useful than no diagram
- Continue to the next block

**Hard ceiling: 2 fix attempts per block.** Don't loop forever.

## When `mmdc` is not installed

`scripts/validate-mermaid.sh` returns 0 with a stderr warning if `mmdc` is missing. In that case:

- Emit all Mermaid blocks as-written
- Print a single warning at the top of `ARCHITECTURE.md`:

```markdown
> ⚠ Mermaid CLI (`mmdc`) not installed — diagrams below were not validated.
> Install with `npm install -g @mermaid-js/mermaid-cli` and re-run `/agent-ready --skip-understand --architecture` to validate.
```

Do **not** skip Phase 2.5 because of missing `mmdc`; an unvalidated diagram is still useful documentation.

## After the doc is written and validated

Update `.understand-anything/config.json`:

```json
{
  "autoUpdate": true,
  "architecture": true
}
```

Preserve other keys; only set `architecture: true`. This flag is read by the auto-refresh path (see `auto-refresh.md`) to decide whether to re-run Phase 2.5 on subsequent KG updates.
