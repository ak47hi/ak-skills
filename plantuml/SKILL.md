---
name: plantuml
description: Generate valid, reviewable PlantUML for sequence, component, class, state, activity, deployment, ER / ERD, use case, C4 (Context/Container/Component/Dynamic via the C4-PlantUML stdlib), and pipeline (streaming / system design / left-to-right data flow). Elicits diagram type, participants, and scope when intent is unclear; skips elicitation when the spec is complete. Defaults to minimal monochrome-friendly styling (`!theme plain`), explicit `@startuml/@enduml`, named diagrams. Trigger on the intent to diagram software — "sequence diagram for X", "ERD of our schema", "state machine for orders", "C4 container", "draw the architecture", "kafka pipeline", "system design", "sketch the system" — not just the word "PlantUML". Also triggers on `.puml` files or any UML request. Do NOT use for Mermaid, D2, Graphviz, drawio, Excalidraw, ASCII box art, or diagram families PlantUML handles poorly (gantt, sankey, journey, mindmap, gitGraph, timeline) — see `references/92-not-plantuml.md`.
---

# PlantUML skill

Generate valid PlantUML for a fixed set of diagram types. Opinionated about three things:

1. **Right diagram type beats prettier diagram.** A sequence diagram of a static structure is wrong even if it renders. The ROUTE phase exists to catch this before generating.
2. **Elicit when intent is ambiguous; skip when it isn't.** Don't ask questions the prompt already answered. Don't guess when it didn't.
3. **Minimal styling, named diagrams, explicit boundaries.** `!theme plain`, `@startuml <name>`, no decorative skinparams, no color-only semantics. Diagrams should read in monochrome.

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
- No color-only semantics. If something needs to stand out, use a stereotype or note, not a color.

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
- User asks to color-code by status. Suggest stereotypes / notes instead; explain that color-only semantics break in monochrome rendering and for color-blind readers.
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
| `references/90-anti-patterns.md` | What to refuse to emit and why; lint codes |
| `references/91-output-contract.md` | Final response format |
| `references/92-not-plantuml.md` | Exit cases: when to point at Mermaid / D2 instead |
| `scripts/lint.py` | Mechanical first pass over the generated `.puml`; called by VERIFY |
| `evals/evals.json` | Test cases (skill-creator schema) — what "good" means |

---

## Changelog

### 2026-05-19 — refinement v1

Evaluation + refinement pass against current PlantUML (v1.2026.x) and C4-PlantUML (v2.13.0). Architecture unchanged; edges sharpened.

- **Added** `evals/evals.json` (10 cases, skill-creator schema) and `evals/baseline.json` recording pre-change behavior.
- **Added** `scripts/lint.py` (Python 3 stdlib, no deps). Deterministic anti-pattern checks; VERIFY's mechanical first pass.
- **Added** `references/92-not-plantuml.md` — exit cases when Mermaid / D2 / Excalidraw is the right tool. Skill now redirects rather than silently producing PlantUML for GitHub-README / gantt / journey / mindmap / etc.
- **Updated** `references/18-c4.md` — `SHOW_LEGEND()` preferred over `LAYOUT_WITH_LEGEND()`; tag system (`AddElementTag` / `AddRelTag`) documented as the canonical replacement for color-only semantics inside C4; `!ROUNDED_STYLE=1` and `!NEW_C4_STYLE=1` opt-ins; `LAYOUT_LANDSCAPE()` / `!NO_LAY_ROTATE=1` layout interactions.
- **Updated** all four C4 templates — `LAYOUT_WITH_LEGEND()` → `SHOW_LEGEND()`; commented `!ROUNDED_STYLE=1` opt-in.
- **Updated** `references/10-sequence.md` — `return` shorthand, `autonumber` format strings (`autonumber 10 "<b>[000]"`), `autonumber stop` / `resume`, `!pragma teoz true` (advanced).
- **Updated** `templates/sequence.puml` — commented examples of `return` and `autonumber` format string.
- **Updated** `references/90-anti-patterns.md` — `!theme` must precede `!include` (`E010`); `!theme plain` on C4 (`E011`); cross-reference to `scripts/lint.py` and its code vocabulary.
- **Updated** `SKILL.md` VERIFY — mechanical lint pass added as step 1, prose walk as step 2.

### 2026-05-19 — Phase 5 description tuning

Ran skill-creator's `run_loop.py` (20-query trigger eval; 5 iterations; 300 `claude -p` calls). **Best_description came back identical to original** because the harness was structurally unable to measure: `run_eval.py` writes a synthetic slash command at `~/.claude/commands/<skill_name>-skill-<uuid>.md` and checks for the uuid-suffixed name in the `Skill` tool's input, but `claude -p` invoked the **real installed skill** at `~/.claude/skills/plantuml/` by its bare name `plantuml`. String-match never fired. The four LLM-generated description drafts were written to a file nobody read.

Empirical sanity check (manual `claude -p` runs against two opposing prompts):
- Should-trigger ("OAuth2 PKCE sequence diagram"): plantuml fired, read SKILL.md + references, wrote a `.puml`, ran `scripts/lint.py`. Full workflow.
- Should-not-trigger ("mermaid diagram for github readme"): plantuml did NOT fire; Claude produced a Mermaid `flowchart LR` directly.

Conclusion: the original description was already doing its job. Applied a small **surgical edit** to graft in genuine improvements surfaced by the LLM drafts: "ERD" added alongside "ER"; expanded exclusion list (D2, Excalidraw, gantt, sankey, user journey, mindmap, gitGraph, timeline); intent-based phrasing ("Trigger on the intent to diagram software... not just the word 'PlantUML'"); pointer to `references/92-not-plantuml.md`. Description is now 972 chars (cap 1024).

### 2026-05-19 — elicitation cap fix

Subagent eval run (see `evals/subagent-run-1.json`) flagged case 0 (ambiguous "draw a diagram of our system") as the lone PARTIAL because the model listed 6 candidate diagram types instead of the rule's 2–3. Root cause: the rule said "trim to 2–3 that fit" but didn't say what to do when nothing trims (maximally vague prompt). Tightened `references/00-elicitation.md` Q1 section: **cap at 3 candidates, always**. Added explicit fallback for the maximally-vague case (default to C4 Container / Sequence / ER as the three most common production-software intents; swap one out when the implied domain calls for it). Master nine-option list stays as the internal reference; the user sees at most three.

### 2026-05-19 — refinement v2: pipeline diagram + sprite catalogue

New diagram family + a generic sprite-inclusion reference any diagram type can pull in. Implements the plan in `docs/plans/refinement-v2.md`.

- **Added** `references/19-pipeline.md` — pipeline diagram type for horizontal data-flow / streaming / "system design" prompts. A focused variant of deployment (no new PlantUML primitives), with `left to right direction` as the non-negotiable, stage discipline, semantic-container rules per stage role, and a tight set of anti-patterns.
- **Added** `references/20-sprites.md` — catalogue of four sprite collections this skill knows: `gilbarbara-plantuml-sprites` (default for streaming/data tech, URL form pinned to v1.1), `tupadr3/plantuml-icon-font-sprites` (devicons / font-awesome fallback, different macro syntax), `aws-icons-for-plantuml` (AWS services, pinned to v23.0), `kubernetes-PlantUML` (k8s resources). Documents the Flink gap (no Flink sprite in plantuml-stdlib — use `<$apache>` + "Flink" label), the C4-PlantUML `$sprite="kafka"` integration, and the monochrome / labels-carry-meaning discipline.
- **Added** `templates/pipeline.puml` — horizontal Kafka-shaped pipeline skeleton: producer → Kafka topic → Flink (via `<$apache>` sprite) → Postgres / S3 / downstream Kafka topic, with the gilbarbara sprite preamble + labeled arrows. Drop the sprite preamble to get a plain-monochrome version.
- **Updated** `references/01-routing.md` — new pipeline row above deployment; "Pipeline vs deployment" and "Pipeline vs sequence" disambiguation paragraphs.
- **Updated** `references/00-elicitation.md` — pipeline added as option 10 in the master Q1 list; new "Streaming / pipeline / system-design prompt" entry in the trimmed-3-defaults rules with pipeline as the top pick.
- **Updated** `references/11-component.md`, `15-deployment.md`, `18-c4.md` — one cross-reference paragraph each pointing to `20-sprites.md`. C4 specifically documents the `$sprite="<name>"` arg on Container macros (preferred over raw `<$sprite>` syntax inside C4).
- **Updated** `SKILL.md` — pipeline added to the description's type list and trigger phrases ("kafka pipeline", "system design"); description now 988 chars (cap 1024). Pipeline row added to the GENERATE-phase routing table. References-at-a-glance gains rows for 19 and 20.

Notable correction to the plan during execution: the plan assumed `!include <gilbarbara/kafka>` worked via plantuml-stdlib short-form. WebFetch against the current plantuml-stdlib repo confirmed it doesn't — gilbarbara ships only as a separate `plantuml-stdlib/gilbarbara-plantuml-sprites` repo accessible via URL form (`!define SPRITESURL .../v1.1/sprites` + `!include SPRITESURL/<name>.puml`). The reference doc uses the URL form. Same for tupadr3 (uses prefix macros `DEV2_MYSQL(db1)`, not `<$>` — documented as the second-choice fallback).
