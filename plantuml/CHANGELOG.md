# Changelog

History of changes to the plantuml skill. SKILL.md is the operational guide; this file is the archeology.

## 2026-05-26 — colored styling preset (opt-in)

User feedback: the skill silently stripped colors out of a request for "rich PlantUML diagrams" to match the doc's existing Mermaid style. The skill was working as designed (monochrome-default with `!theme plain` enforced), but the design had no documented escape hatch for presentation-quality / Confluence-ready output. Two real gaps surfaced — the description didn't advertise the monochrome stance loudly enough, and "comply if the user insists with a reason" had no canonical styling to comply *with*.

- **Added** `references/22-styling-colored.md` — canonical colored preset (Confluence-friendly soft palette covering component / database / queue / node / package / cloud / folder / artifact / interface / sequence / activity / state / class / usecase shapes). Documents trigger phrases, ordering rules (`!theme` slot, before `!include`), explicit no-apply list (C4 diagrams, DBA-audience ER, ≥15-message sequences), and the still-banned "color-only semantics" rule.
- **Updated** `SKILL.md` description (969 chars, cap 1024) — now mentions "opt-in colored preset when user explicitly asks for 'colored', 'styled', 'rich', or 'Confluence-ready' diagrams" so the model knows both modes exist.
- **Updated** `SKILL.md` opinion #3 — clarified that the colored preset is the only sanctioned alternative to `!theme plain`; bespoke skinparams remain anti-pattern.
- **Updated** `SKILL.md` GENERATE — added "Colored mode (opt-in)" block under universal defaults.
- **Updated** `SKILL.md` push-back — split color-coding-by-status (still suggest stereotypes) from colored-diagrams (now apply the preset).
- **Updated** `references/00-elicitation.md` — "What NOT to ask" carves out colored mode from the "don't ask theming" rule when prompt is ambiguous; added a one-line check.
- **Updated** `references/90-anti-patterns.md` — "Decorative skinparams" rule now reads "use `!theme plain` OR the documented preset"; "Color-only semantics" rule cross-references colored mode to make clear it still applies.
- **Updated** `references/91-output-contract.md` — theme fallback section adds the colored preset as a third documented option (alongside `!theme plain` and the minimal `skinparam monochrome true` fallback).
- **Verified** `scripts/lint.py` — no rule checks `skinparam` content, so the preset block won't false-fire. E010 (theme-before-include) doesn't apply because colored mode has no `!theme` directive.

## 2026-05-19 — refinement v1

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

## 2026-05-19 — Phase 5 description tuning

Ran skill-creator's `run_loop.py` (20-query trigger eval; 5 iterations; 300 `claude -p` calls). **Best_description came back identical to original** because the harness was structurally unable to measure: `run_eval.py` writes a synthetic slash command at `~/.claude/commands/<skill_name>-skill-<uuid>.md` and checks for the uuid-suffixed name in the `Skill` tool's input, but `claude -p` invoked the **real installed skill** at `~/.claude/skills/plantuml/` by its bare name `plantuml`. String-match never fired. The four LLM-generated description drafts were written to a file nobody read.

Empirical sanity check (manual `claude -p` runs against two opposing prompts):
- Should-trigger ("OAuth2 PKCE sequence diagram"): plantuml fired, read SKILL.md + references, wrote a `.puml`, ran `scripts/lint.py`. Full workflow.
- Should-not-trigger ("mermaid diagram for github readme"): plantuml did NOT fire; Claude produced a Mermaid `flowchart LR` directly.

Conclusion: the original description was already doing its job. Applied a small **surgical edit** to graft in genuine improvements surfaced by the LLM drafts: "ERD" added alongside "ER"; expanded exclusion list (D2, Excalidraw, gantt, sankey, user journey, mindmap, gitGraph, timeline); intent-based phrasing ("Trigger on the intent to diagram software... not just the word 'PlantUML'"); pointer to `references/92-not-plantuml.md`. Description is now 972 chars (cap 1024).

## 2026-05-19 — elicitation cap fix

Subagent eval run (see `evals/subagent-run-1.json`) flagged case 0 (ambiguous "draw a diagram of our system") as the lone PARTIAL because the model listed 6 candidate diagram types instead of the rule's 2–3. Root cause: the rule said "trim to 2–3 that fit" but didn't say what to do when nothing trims (maximally vague prompt). Tightened `references/00-elicitation.md` Q1 section: **cap at 3 candidates, always**. Added explicit fallback for the maximally-vague case (default to C4 Container / Sequence / ER as the three most common production-software intents; swap one out when the implied domain calls for it). Master nine-option list stays as the internal reference; the user sees at most three.

## 2026-05-19 — refinement v2: pipeline diagram + sprite catalogue

New diagram family + a generic sprite-inclusion reference any diagram type can pull in. Implements the plan in `docs/plans/refinement-v2.md`.

- **Added** `references/19-pipeline.md` — pipeline diagram type for horizontal data-flow / streaming / "system design" prompts. A focused variant of deployment (no new PlantUML primitives), with `left to right direction` as the non-negotiable, stage discipline, semantic-container rules per stage role, and a tight set of anti-patterns.
- **Added** `references/20-sprites.md` — catalogue of four sprite collections this skill knows: `gilbarbara-plantuml-sprites` (default for streaming/data tech, URL form pinned to v1.1), `tupadr3/plantuml-icon-font-sprites` (devicons / font-awesome fallback, different macro syntax), `aws-icons-for-plantuml` (AWS services, pinned to v23.0), `kubernetes-PlantUML` (k8s resources). Documents the Flink gap (no Flink sprite in plantuml-stdlib — use `<$apache>` + "Flink" label), the C4-PlantUML `$sprite="kafka"` integration, and the monochrome / labels-carry-meaning discipline.
- **Added** `templates/pipeline.puml` — horizontal Kafka-shaped pipeline skeleton: producer → Kafka topic → Flink (via `<$apache>` sprite) → Postgres / S3 / downstream Kafka topic, with the gilbarbara sprite preamble + labeled arrows. Drop the sprite preamble to get a plain-monochrome version.
- **Updated** `references/01-routing.md` — new pipeline row above deployment; "Pipeline vs deployment" and "Pipeline vs sequence" disambiguation paragraphs.
- **Updated** `references/00-elicitation.md` — pipeline added as option 10 in the master Q1 list; new "Streaming / pipeline / system-design prompt" entry in the trimmed-3-defaults rules with pipeline as the top pick.
- **Updated** `references/11-component.md`, `15-deployment.md`, `18-c4.md` — one cross-reference paragraph each pointing to `20-sprites.md`. C4 specifically documents the `$sprite="<name>"` arg on Container macros (preferred over raw `<$sprite>` syntax inside C4).
- **Updated** `SKILL.md` — pipeline added to the description's type list and trigger phrases ("kafka pipeline", "system design"); description now 988 chars (cap 1024). Pipeline row added to the GENERATE-phase routing table. References-at-a-glance gains rows for 19 and 20.

Notable correction to the plan during execution: the plan assumed `!include <gilbarbara/kafka>` worked via plantuml-stdlib short-form. WebFetch against the current plantuml-stdlib repo confirmed it doesn't — gilbarbara ships only as a separate `plantuml-stdlib/gilbarbara-plantuml-sprites` repo accessible via URL form (`!define SPRITESURL .../v1.1/sprites` + `!include SPRITESURL/<name>.puml`). The reference doc uses the URL form. Same for tupadr3 (uses prefix macros `DEV2_MYSQL(db1)`, not `<$>` — documented as the second-choice fallback).
