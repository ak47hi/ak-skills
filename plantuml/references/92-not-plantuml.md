# When PlantUML is the wrong tool

PlantUML is great at sequence, component, class, state, activity, deployment, ER, use case, and C4. It is not the right tool for every diagramming request that lands in this skill. The right behavior in those cases is to **name the better tool, explain the trade-off in one sentence, and stop** — not to grudgingly produce a PlantUML diagram the user will throw away.

This file enumerates the exit cases. Routing (`01-routing.md`) consults this list before falling into the diagram-type tree.

## Exit case 1 — "I want to paste this into a GitHub / GitLab / Notion / Slack README"

**Better tool: Mermaid.** GitHub, GitLab, Notion, and many markdown viewers render Mermaid natively from a fenced code block. PlantUML diagrams need an external renderer (`plantuml -tsvg`) and either an embedded image or a service like Kroki/PlantUML server.

**When to override**: if the user says "yes I know, but we run our own PlantUML server" or "we embed renders into our README", produce PlantUML. Otherwise, default to Mermaid for embed-in-markdown use cases.

**Phrasing the exit**:

> For a diagram that renders inline in GitHub / Notion / Slack, Mermaid is the right tool — it ships in their markdown engines and PlantUML doesn't. Want me to draft a Mermaid version, or do you already have a PlantUML renderer set up and want a `.puml` you can pipe through it?

## Exit case 2 — Diagram families PlantUML doesn't cover (or covers awkwardly)

| Request | Better tool |
|---|---|
| Gantt / project timeline / roadmap | Mermaid (`gantt`) |
| User journey, persona flow | Mermaid (`journey`) |
| Mindmap, idea tree | Mermaid (`mindmap`) |
| Git branching history | Mermaid (`gitGraph`) |
| Sankey (flow magnitude) | Mermaid (`sankey-beta`) |
| Quadrant chart (effort/impact matrix) | Mermaid (`quadrantChart`) |
| Network / packet diagram | Mermaid (`packet-beta`) or specialized tools |
| Block diagram with rich connectors | D2 |
| Requirement diagrams (SysML-ish) | Mermaid (`requirement`) |

PlantUML technically supports gantt and mindmap in newer releases, but the tooling is immature compared to Mermaid for those families and the syntax surprises users coming from the sequence/class/C4 world. Default to Mermaid; cite this file when explaining.

## Exit case 3 — "Make it look good without me styling it"

**Better tool: D2.** D2's TALA layout engine produces visually polished diagrams from minimal input — what most users actually want when they say "make it look professional". PlantUML's strength is *correctness and breadth* across UML diagram types; it is not its strength to produce a beautifully laid-out architecture diagram with zero styling effort.

This is a soft exit — recommend D2 if the user's stated goal is aesthetics over UML correctness, but stay with PlantUML if they're producing diagrams for code review, design docs, or anything where UML semantics matter.

## Exit case 4 — Free-form drawing / whiteboarding

Excalidraw, tldraw, drawio, FigJam. Not in PlantUML's wheelhouse. Refuse politely and suggest the right canvas tool.

## What NOT to do

- Don't refuse without a redirect. "I can't do Mermaid" is half an answer; "Mermaid is the right tool for GitHub READMEs because it renders natively, want me to draft one?" is the full answer.
- Don't silently produce PlantUML when the request was clearly Mermaid-flavored. The user will paste it into GitHub, see it not render, and lose trust.
- Don't try to support Mermaid syntax inside this skill. The skill's contract is PlantUML; the exit case is "stop and point at the right tool".
- Don't proselytize. One sentence on the trade-off is plenty. If the user wants more, they'll ask.

## How to phrase the exit in the response

The Phase 4 VERIFY output contract still applies, but instead of `.puml` + render command + summary, an exit looks like:

> *Brief one-sentence diagnosis of why this is a non-PlantUML request*, *one-sentence recommendation of the better tool*, *one-question offer to switch or override*.

Three sentences. No code block. No PlantUML. If the user overrides with "produce PlantUML anyway", drop back into the normal Phase 2 (ROUTE) flow.
