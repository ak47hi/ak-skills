# Anti-patterns

Walk this list against every generated diagram before emitting. These are not refusals — they're prompts to fix or re-discuss with the user before shipping a diagram that misleads.

## Universal

### God-diagram

Symptom: one diagram with >15 nodes (component, deployment, C4) or >20 participants (sequence).

Why it's bad: nobody reads a god-diagram. The reader gives up and the diagram fails its purpose.

Fix: decompose by use case (one sequence per scenario), by subsystem (one component diagram per bounded context), or by abstraction level (C4 zoom-in).

### Color-only semantics

Symptom: red boxes for "deprecated", green for "new", with no other indicator.

Why it's bad: breaks in monochrome rendering, breaks for color-blind readers, breaks when copy-pasted into a doc that strips color.

Fix: use stereotypes (`<<deprecated>>`), notes, or text prefixes. Color, if used at all, is an *additional* signal layered on top of a text-readable one.

**Note:** this rule applies in both default monochrome mode AND in colored mode (`references/22-styling-colored.md`). The colored preset paints shapes by structural **role** (component vs database vs queue), not by semantic **status**. Status meaning still needs a non-color carrier.

### Missing diagram name

Symptom: `@startuml` with no name.

Why it's bad: when the file is referenced elsewhere, the render output is anonymous. Multi-diagram pages can't distinguish.

Fix: always `@startuml <descriptive-name>`. The name matches the filename minus `.puml`.

### Inconsistent arrow styles

Symptom: same diagram uses `->`, `-->`, `->>` interchangeably for the same kind of relation.

Why it's bad: in PlantUML, arrow style is semantic. `->` is solid (sync), `-->` is dashed (async or dependency), `->>` is thin (often async). Mixing them randomly looks like the differences mean something when they don't.

Fix: pick one arrow style per relation type and use it consistently. Per-type references document which style means what.

### Decorative skinparams

Symptom: ad-hoc `skinparam` for backgroundColor, shadow, rounded corners, custom fonts, gradients — invented per-diagram.

Why it's bad: bloats the source, doesn't render consistently across PlantUML versions, distracts from the content, every diagram looks different.

Fix: pick one of the **three documented options** — nothing else.

1. `!theme plain` — the default.
2. The colored preset block from `references/22-styling-colored.md` — opt-in when the user explicitly asks for colored / styled / Confluence-ready diagrams.
3. The minimal `skinparam` block from `references/91-output-contract.md` — fallback for older PlantUML builds that don't ship the `plain` theme.

Bespoke skinparam blocks outside these three are anti-pattern. If the colored preset isn't quite right for one shape in one diagram, use an inline override (`component "Engine" #FAD7A0`) — see `references/22-styling-colored.md` § "Inline overrides".

### `!theme` after `!include` (ordering pitfall)

Symptom: a `!theme foo` directive appears later in the file than an `!include` (or inside an included file).

Why it's bad: themes layer on top of the renderer's defaults — including the style choices baked into stdlib `!include`s. If theme comes after include, the theme either gets overridden by the include's own styling or fights it, producing visually inconsistent output. PlantUML doesn't error; it silently produces a worse diagram.

Fix: `!theme` is always the first non-comment directive, before any `!include`. lint.py catches this as `E010`.

### `!theme plain` on a C4 diagram

Symptom: a `.puml` file has both `!include <C4/C4_*>` and `!theme plain`.

Why it's bad: C4-PlantUML applies its own visual conventions and color palette via the include. Stacking `!theme plain` on top either gets overridden or fights the stdlib styling. Inconsistent output, no error.

Fix: on C4 diagrams, drop `!theme plain` entirely — the stdlib handles theming. Use `SHOW_LEGEND()` (or `LAYOUT_WITH_LEGEND()`) to expose visual element types instead. lint.py catches this as `E011`. See `references/18-c4.md` § "No `!theme plain` on C4 diagrams".

## Mechanical lint pass

Many of the rules above can be checked deterministically. Run `scripts/lint.py <file.puml>` against the generated source as the first pass of VERIFY — it's faster and more reliable than walking this list by hand. The prose walk below catches what static checks can't (intent mismatches, abstraction-level choices, scope decisions).

Codes the script emits: `E001`–`E004` (universal: missing/unnamed `@startuml`, missing `@enduml`), `E010`–`E011` (theme/include ordering), `W020`–`W022` (sequence: god-diagram count, autonumber-on-small-diagram, implicit participants), `E030`/`W031` (state: missing `[*]`, unlabeled transitions), `E040`/`W041` (ER: class-style arrow in ER, missing crow's-foot), `W050`/`E051`/`E052` (C4: missing tech label, missing `Rel` label), `W060` (class: missing visibility), `W070`/`W080` (component / deployment: no semantic containers).

## Per-type

### Sequence

- **Unnamed lifelines.** `Alice -> Bob` with no `participant` declaration: the participants render but their visual type (actor, database, queue) is wrong. Declare participants explicitly at the top.
- **Notes that aren't anchored.** `note: text` with no `left of` / `right of` / `over` floats arbitrarily. Always anchor.
- **Activation/deactivation imbalance.** `++` without matching `--` produces visual rectangles that never close. Use either symmetric `++`/`--` or none.
- **Autonumber on micro-diagrams.** Sequence diagrams with 3 messages don't need autonumbering. Reserve for 6+ message diagrams.

### Component

- **`[box]` for everything.** Components have types: `package`, `node`, `cloud`, `database`, `queue`, `frame`, `folder`. Pick the right one — it conveys deployment intent.
- **No interfaces.** Component diagrams that don't show interfaces are just "blobs and lines". Use `()` lollipops or `interface` declarations to show what each component exposes.
- **Implicit grouping.** If components belong together (one subsystem, one team's responsibility), wrap them in a `package` or `node`.

### Class

- **No visibility markers.** Every field/method should have `+`, `-`, `#`, or `~`. Omitted visibility reads as "I didn't think about access".
- **`-->` for everything.** Class diagrams have specific arrows: `<|--` inheritance, `<|..` realization, `*--` composition, `o--` aggregation, `-->` association, `..>` dependency. Each means something different.
- **No multiplicity on associations.** `Order --> LineItem` without `"1" --> "*"` doesn't communicate the relationship's cardinality.

### State

- **No `[*]`.** Every state diagram needs a start (`[*] -->`) and usually an end (`--> [*]`). Otherwise the diagram doesn't define the entry/exit.
- **Flat state list.** If states cluster (e.g. multiple "Processing" sub-states), use composite states with `state Parent { ... }`.
- **Choice without `<<choice>>`.** Branching by condition should use a `<<choice>>` pseudostate, not three transitions out of one state.

### Activity

- **Mixing beta and legacy syntax.** Don't mix `:action;` (beta) with `(*) --> action` (legacy). Pick beta — it's the supported syntax.
- **Swimlanes used as decoration.** Swimlanes (`|name|`) are for showing *who* does each step. If there's only one actor, don't add swimlanes.
- **Unbalanced if/endif, while/endwhile, fork/end fork.** PlantUML parses these strictly; missing `endif` etc. breaks the render.

### Deployment

- **Generic `node` for everything.** Deployment diagrams have semantic containers: `cloud`, `database`, `queue`, `node`, `artifact`, `folder`, `file`. Pick the right one.
- **Flat structure.** Deployment is about nesting (artifacts live in nodes, nodes live in clouds). A flat diagram is usually a misrouted component diagram.

### ER

- **No cardinality.** Every relation needs crow's-foot notation: `}|--||`, `}o--|{`, etc. An ER diagram without cardinality is just a class diagram with no methods.
- **Everything marked required.** `*` should mark only attributes that are truly NOT NULL. Marking everything required is no information.
- **Missing `<<FK>>`.** Foreign-key attributes should be marked `<<FK>>` so the reader can trace relations to columns.

### Use case

- **Actor inside the system boundary.** Actors live outside the `rectangle "System" { ... }`. Use cases live inside.
- **Wrong arrow for include/extend.** `<<include>>` and `<<extend>>` use `..>` (dashed arrow), not `-->` or `<|--`.
- **Too many use cases.** A use case diagram with 30 use cases is unreadable. Decompose by subsystem.

### C4

- **Mixed abstraction levels.** Internal components inside a Context diagram. External users inside a Component diagram. Container-level details in a Context diagram. Each C4 level is exclusive — see `references/18-c4.md`.
- **No `Rel` labels.** `Rel(a, b, "")` produces a line with no description. Always describe the relationship ("Reads from", "Notifies", "Authenticates via").
- **`System_Ext` confused with `System`.** External systems we don't own use `System_Ext` (greyed visually). Our own systems use `System`. Mixing them lies about ownership.
- **Missing tech labels on Container/Component.** `Container(api, "API")` is less useful than `Container(api, "API", "Go, gRPC")`. The tech label is part of why C4 is useful.
