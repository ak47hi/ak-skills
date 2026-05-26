# Colored styling preset

The skill's default is monochrome (`!theme plain`) because most diagrams ship into spec docs, terminals, and printers where color is noise or lost. This reference defines the **canonical opt-in alternative**: a Confluence-friendly soft-pastel palette applied via a documented `skinparam` block.

This is the only sanctioned alternative. Bespoke / ad-hoc `skinparam` blocks remain an anti-pattern (see `references/90-anti-patterns.md` § "Decorative skinparams") — pick the documented preset or `!theme plain`, nothing in between.

## When to apply

Apply this preset when the user **explicitly** asks for it. Trigger phrases include:

- "colored", "color", "colorful diagrams"
- "rich diagrams", "styled diagrams", "pretty diagrams", "nice diagrams"
- "for Confluence", "for the design doc", "for presentation", "presentation-quality"
- "match the style in <file>" — when the referenced file uses a colored palette
- explicit override: "don't use monochrome", "skip `!theme plain`"

When ambiguous (e.g. user says "rich PlantUML diagrams" with no other signal — "rich" can mean information-rich), **ask one question** in ELICIT:

> Default styling is monochrome (`!theme plain`). Want the colored preset (Confluence-friendly soft palette) instead?

Do **not** infer colored mode from phrases like "good diagrams", "well-formed", "production-grade" — those refer to content quality, not styling.

## What NOT to apply it to

- **C4 diagrams.** C4-PlantUML stdlib applies its own visual conventions and color palette. Stacking this preset on top fights the stdlib styling. C4 stays as-is; if the user wants color in C4, use the C4-PlantUML tag system (`AddElementTag` / `AddRelTag`) — see `references/18-c4.md`.
- **ER diagrams when the consumer is a DBA / schema-doc audience.** Crow's-foot notation reads cleaner in monochrome. Apply only if the user explicitly asks.
- **Sequence diagrams ≥ 15 messages.** The participant-band coloring becomes visually busy at scale. Suggest decomposition first; apply if user insists.

## The preset

Replace the `!theme plain` line (or, for templates that don't have one yet, insert this block immediately after `@startuml <name>`):

```puml
' Colored preset — Confluence/presentation friendly. Documented in references/22-styling-colored.md.
skinparam shadowing true
skinparam roundCorner 8
skinparam defaultFontName "Helvetica"
skinparam ArrowColor #555555
skinparam ArrowFontColor #333333
skinparam ArrowFontSize 11

skinparam component {
    BackgroundColor #D4E6F1
    BorderColor SteelBlue
    FontColor #1A5276
}
skinparam database {
    BackgroundColor #A9DFBF
    BorderColor #1E8449
    FontColor #145A32
}
skinparam queue {
    BackgroundColor #F5CBA7
    BorderColor #CA6F1E
    FontColor #784212
}
skinparam node {
    BackgroundColor #EBDEF0
    BorderColor #6C3483
    FontColor #4A235A
}
skinparam package {
    BackgroundColor #FCF3CF
    BorderColor #B7950B
    FontColor #7D6608
}
skinparam cloud {
    BackgroundColor #D6EAF8
    BorderColor #2874A6
    FontColor #1B4F72
}
skinparam folder {
    BackgroundColor #FADBD8
    BorderColor #C0392B
    FontColor #78281F
}
skinparam artifact {
    BackgroundColor #F2F3F4
    BorderColor #5D6D7E
    FontColor #2C3E50
}
skinparam interface {
    BackgroundColor #FFFFFF
    BorderColor #34495E
}

skinparam sequence {
    ParticipantBackgroundColor #D4E6F1
    ParticipantBorderColor SteelBlue
    ParticipantFontColor #1A5276
    ActorBackgroundColor #FCF3CF
    ActorBorderColor #B7950B
    LifeLineBorderColor #888888
    GroupBackgroundColor #F8F9F9
    GroupBorderColor #999999
}

skinparam activity {
    BackgroundColor #D4E6F1
    BorderColor SteelBlue
    FontColor #1A5276
    DiamondBackgroundColor #FCF3CF
    DiamondBorderColor #B7950B
    DiamondFontColor #7D6608
    StartColor #1E8449
    EndColor #C0392B
}

skinparam state {
    BackgroundColor #D4E6F1
    BorderColor SteelBlue
    FontColor #1A5276
    StartColor #1E8449
    EndColor #C0392B
}

skinparam class {
    BackgroundColor #FFFFFF
    BorderColor #34495E
    HeaderBackgroundColor #D4E6F1
    AttributeFontColor #555555
    StereotypeFontColor #6C3483
}

skinparam usecase {
    BackgroundColor #FCF3CF
    BorderColor #B7950B
    FontColor #7D6608
    ActorBackgroundColor #D4E6F1
    ActorBorderColor SteelBlue
}
```

Yes, it's long. It's also fixed — copy verbatim, don't adapt per-diagram. The whole point of having a canonical preset is that every colored diagram from this skill looks like every other colored diagram from this skill.

## Ordering rules

- The preset block goes **after `@startuml <name>`** and **before any `!include`** — same ordering rule as `!theme` (see `90-anti-patterns.md` § "`!theme` after `!include`").
- Do **not** keep `!theme plain` alongside the preset. Pick one. The preset replaces the theme.
- Sprite includes (`!define SPRITESURL ...`, `!include SPRITESURL/...`) come after the preset.

## Color-only semantics — still banned

The preset paints shapes by their **structural role** (component vs database vs queue), not by **semantic status** (deprecated, new, deferred). The anti-pattern rule against color-only semantics (`references/90-anti-patterns.md`) still applies in colored mode:

- ❌ "Red box = deprecated, green box = new" with no other indicator.
- ✅ `<<deprecated>>` stereotype on the box; the box's role-color is incidental.

Color is decoration. Meaning is carried by labels, stereotypes, and notes.

**Mimicry-mode exception (different mode, not a loophole).** If the user explicitly asked for a diagram that mirrors a specific tool's UI (Flink dashboard, Spark UI, Airflow DAG view, GitHub Actions workflow graph), status coloring *is* legitimate — but the diagram switches modes entirely. It uses the dashboard-specific palette in `references/23-dashboard-mimicry.md`, **not** this preset, and adds a mandatory inline `legend bottom` block that maps every color to its meaning. The legend is what carries semantics; the color is the visual amplifier. Don't smuggle status colors into a role-based preset diagram — pick the right mode up front.

## Inline overrides

If a single shape needs to stand out from the role-palette default — e.g., highlighting the one component the diagram is about — use a single inline override on that shape, not a sweeping `skinparam` change:

```puml
component "Forecast Engine" as engine #FAD7A0
```

Use sparingly. One or two highlights per diagram, never as the primary signal.

## Lint behavior

`scripts/lint.py` does **not** currently flag `skinparam` lines — the deterministic anti-pattern checks deliberately stay out of the styling space. The prose pass in VERIFY is responsible for catching bespoke skinparam blocks that aren't this documented preset.

## Render note

The preset uses hex colors with shadows and rounded corners — PlantUML versions before 1.2020 render colors but ignore `roundCorner`; very old versions ignore shadows too. Output stays sensible on every version (degrades to plain colored boxes); no version-specific fallback needed.
