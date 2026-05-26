---
name: plantuml
description: Generate valid, reviewable PlantUML for sequence, component, class, state, activity, deployment, ER / ERD, use case, C4 (Context/Container/Component/Dynamic via the C4-PlantUML stdlib), and pipeline (streaming / system design / left-to-right data flow). Elicits diagram type, participants, and scope when intent is unclear; skips elicitation when the spec is complete. Defaults to monochrome (`!theme plain`); opt-in colored preset when user explicitly asks for "colored", "styled", "rich", or "Confluence-ready" diagrams. Trigger on the intent to diagram software — "sequence diagram for X", "ERD of our schema", "state machine for orders", "C4 container", "kafka pipeline", "system design" — not just the word "PlantUML". Also triggers on `.puml` files or any UML request. Do NOT use for Mermaid, D2, Graphviz, drawio, Excalidraw, or diagram families PlantUML handles poorly (gantt, sankey, journey, mindmap, gitGraph, timeline) — see `references/92-not-plantuml.md`.
---

# PlantUML skill

Generate valid PlantUML for a fixed set of diagram types. Opinionated about three things:

1. **Right diagram type beats prettier diagram.** A sequence diagram of a static structure is wrong even if it renders. The ROUTE phase exists to catch this before generating.
2. **Elicit when intent is ambiguous; skip when it isn't.** Don't ask questions the prompt already answered. Don't guess when it didn't.
3. **Minimal styling, named diagrams, explicit boundaries.** `!theme plain` is the default; `@startuml <name>` always; no bespoke skinparams (use the canonical colored preset in `references/22-styling-colored.md` if the user explicitly asks for color); no color-only semantics regardless of mode. Diagrams should read in monochrome by default.

---

## Four phases

```
ELICIT   →  Ask only when type / participants / scope are unclear.    references/00-elicitation.md
ROUTE    →  Intent → diagram type → reference + template.             references/01-routing.md
GENERATE →  Copy the template, fill it, apply the type's rules.       references/10..18-*.md + templates/
VERIFY   →  Run the anti-pattern checklist, emit the output contract. references/90-anti-patterns.md + 91-output-contract.md
```

These are phases, not modes — run them in order, once per request. If the user iterates on a diagram, re-enter from ROUTE (the elicited context carries forward).

---

## ELICIT

Read `references/00-elicitation.md`. It defines:
- When the prompt is **complete enough to skip** (type + participants + scope all pinned down).
- The **three questions** worth asking when it isn't: which diagram type, who the participants are, what the scope is.
- How to **propose 2–3 candidate types** when the user doesn't know which to ask for, tied to intent ("flow over time → sequence; static structure → component or C4 container").

Skip elicitation aggressively. Asking when the spec is already complete wastes a turn and signals the skill doesn't read.

---

## ROUTE

Read `references/01-routing.md`. The decision tree maps user intent to one diagram type and points at the reference + template pair to load. The mapping summarized:

| Intent | Type | Reference | Template |
|---|---|---|---|
| Message exchange over time between participants | sequence | `references/10-sequence.md` | `templates/sequence.puml` |
| Static structure of software pieces and their interfaces | component | `references/11-component.md` | `templates/component.puml` |
| Object-oriented type structure (classes, generics, relations) | class | `references/12-class.md` | `templates/class.puml` |
| State machine, lifecycle of an entity | state | `references/13-state.md` | `templates/state.puml` |
| Procedural / business flow with branches and loops | activity | `references/14-activity.md` | `templates/activity.puml` |
| Where things run — nodes, artifacts, infra | deployment | `references/15-deployment.md` | `templates/deployment.puml` |
| Data model entities and their cardinality | ER | `references/16-er.md` | `templates/er.puml` |
| Actor goals against a system boundary | use case | `references/17-usecase.md` | `templates/usecase.puml` |
| C4 abstraction levels (Context/Container/Component/Dynamic) | C4 | `references/18-c4.md` | `templates/c4-*.puml` |
| Streaming / "system design" / left-to-right data pipeline (producers → broker → processors → sinks) | pipeline | `references/19-pipeline.md` | `templates/pipeline.puml` |

If a request honestly needs two diagrams (e.g. "C4 container diagram + a sequence diagram of one critical path"), generate both — but produce them as separate named `.puml` files, not a single mixed diagram.

---

## GENERATE

For the routed type:

1. Copy the matching template verbatim from `templates/`.
2. Rename the diagram (`@startuml <name>`).
3. Read the matching `references/1X-*.md` for **structural rules** (which constructs to prefer, which arrows mean what, what to declare explicitly).
4. Fill in the skeleton. Don't invent constructs the reference doesn't list — PlantUML's surface is wide; sticking to the canonical set keeps diagrams renderable across PlantUML versions.

**Universal defaults** applied in every template:
- `@startuml <descriptive-name>` and `@enduml` always.
- `!theme plain` as the first non-comment line **for non-C4 diagrams**. C4 templates skip this — the C4-PlantUML stdlib applies its own visual style, and stacking `!theme plain` on top fights it. (Fallback if a user's PlantUML build doesn't ship `plain`: drop the line and use the inline `skinparam` block documented in `references/91-output-contract.md`.)
- `left to right direction` only for diagrams that read horizontally (use case, ER, short flows); top-to-bottom otherwise.
- No color-only semantics — even in colored mode (see below). If something needs to stand out, use a stereotype or note, not a color.

**Colored mode (opt-in).** When the user **explicitly** asks for colored / styled / "rich" / "Confluence-ready" diagrams, swap `!theme plain` for the canonical preset documented in `references/22-styling-colored.md` (a Confluence-friendly soft palette). The preset is the only sanctioned alternative to monochrome — bespoke / ad-hoc `skinparam` blocks remain an anti-pattern. Do **not** apply to C4 diagrams. If the request is ambiguous (e.g. "rich PlantUML" — "rich" could mean information-rich), ask one question per `references/00-elicitation.md`.

For C4 specifically, the `!include <C4/C4_Container>` short form requires the PlantUML standard library (bundled with official PlantUML jars since ~2020). If unsupported on the user's build, the templates document the GitHub URL fallback — see `references/18-c4.md`.

---

## VERIFY

Before emitting the artifact:

1. **Mechanical pass:** run `scripts/lint.py <generated>.puml`. The script checks the deterministic rules (named `@startuml`, balanced theme/include ordering, no `!theme plain` on C4, crow's-foot on ER relations, tech labels on C4 containers, `[*]` on state diagrams, etc.). It exits non-zero on errors. Fix any reported issue before emitting. The list of codes is in `references/90-anti-patterns.md` § "Mechanical lint pass".
2. **Prose pass:** walk `references/90-anti-patterns.md` for the things lint can't catch — abstraction-level mistakes, intent mismatches, layout choice, scope decisions. Common catches: god-diagrams (>15 nodes in a context/component diagram), color-only semantics, mixed C4 abstraction levels, inconsistent arrow styles within one diagram.
3. **Format the response** per `references/91-output-contract.md`:
   - One fenced `puml` code block with the full source.
   - The render command (`plantuml -tsvg <name>.puml` for vector, `-tpng` for raster).
   - A single-sentence summary of what the diagram shows.

That's it. No surrounding prose explaining the syntax — the user can read it.

---

## When to push back

- User asks for a diagram type that doesn't fit the intent (e.g. a sequence diagram of a database schema). Explain the mismatch in one sentence and propose the right type.
- User asks to color-code by **status** (deprecated/new/deferred). Suggest stereotypes / notes instead; explain that color-only semantics break in monochrome rendering and for color-blind readers. (This is different from "I want colored diagrams" — that's a styling request, not a semantic one; apply the colored preset from `references/22-styling-colored.md`.)
- User asks for a single diagram that mixes C4 levels. Split into two.
- User asks for >20 participants in one sequence diagram or >15 nodes in one component diagram. Suggest decomposition (per-use-case sequences, sub-component diagrams).

These are judgment calls, not refusals — if the user insists with a reason, comply.

---

## Iteration

When the user asks for changes to a generated diagram, re-enter from ROUTE (the diagram type rarely changes, so this is usually a no-op) and re-run GENERATE + VERIFY. Keep the diagram named the same so the render command is stable.

---

## References at a glance

| File | What it carries |
|---|---|
| `references/00-elicitation.md` | When to ask, what to ask, when to skip |
| `references/01-routing.md` | Intent → diagram type decision tree |
| `references/10-sequence.md` | Sequence: participants, arrows, notes, grouping, autonumber |
| `references/11-component.md` | Component: components, interfaces, ports, grouping containers |
| `references/12-class.md` | Class: visibility, relations, generics, packages |
| `references/13-state.md` | State: `[*]`, composites, concurrent regions, choice/fork/join |
| `references/14-activity.md` | Activity (beta): `:action;`, swimlanes, partitions, fork |
| `references/15-deployment.md` | Deployment: nodes, artifacts, cloud, db, queue, nesting |
| `references/16-er.md` | ER: `entity`, `*`, `<<FK>>`, crow's-foot cardinality |
| `references/17-usecase.md` | Use case: actors, system boundary, include/extend |
| `references/18-c4.md` | C4: stdlib includes, macros, abstraction levels |
| `references/19-pipeline.md` | Pipeline: left-to-right data flow, stage discipline, sprite use |
| `references/20-sprites.md` | Sprite catalogue (gilbarbara, tupadr3, awslib, kubernetes-PlantUML) — opt-in vendor icons |
| `references/22-styling-colored.md` | Canonical colored preset (Confluence-friendly soft palette) — opt-in alternative to `!theme plain` |
| `references/90-anti-patterns.md` | What to refuse to emit and why; lint codes |
| `references/91-output-contract.md` | Final response format |
| `references/92-not-plantuml.md` | Exit cases: when to point at Mermaid / D2 instead |
| `scripts/lint.py` | Mechanical first pass over the generated `.puml`; called by VERIFY |
| `evals/evals.json` | Test cases (skill-creator schema) — what "good" means |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full history. The most recent entry is summarized in the README and in the `2026-05-26 — colored styling preset (opt-in)` block there.
