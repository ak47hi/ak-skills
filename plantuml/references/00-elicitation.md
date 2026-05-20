# Elicitation

When to ask, what to ask, when to skip. The bar is high: asking when the prompt already pinned the answer wastes a turn and signals the skill doesn't read.

## Three axes to pin down

A diagram request is "complete" when these three are unambiguous:

1. **Type** — sequence, component, class, state, activity, deployment, ER, use case, or a specific C4 level.
2. **Participants** — the named things (services, classes, actors, entities) the diagram contains.
3. **Scope** — which slice of the system to show. "The login flow" is scoped. "Our architecture" is not.

If all three are pinned, skip elicitation and go straight to ROUTE.

## Decision: skip or ask

| Signal in the prompt | Action |
|---|---|
| Names the diagram type AND lists participants AND gives a clear scope | Skip elicitation |
| Names the diagram type AND describes a behavior in enough detail that participants are derivable | Skip elicitation; derive participants from the description |
| Names the diagram type but scope is "everything" / "the whole system" | Ask only about scope |
| Doesn't name a type, but describes a behavior over time | Skip elicitation, route to sequence |
| Doesn't name a type, but describes static structure | Ask one question (component vs C4 container — they overlap) |
| Doesn't name a type, scope is broad, participants vague | Ask all three questions |
| Pastes existing `.puml` and asks for changes | Skip elicitation; treat as iteration |

**Heuristic:** if a skilled human reading the prompt would also need to ask, ask. If they could just produce a reasonable first draft, do that.

## The questions, when needed

Phrase questions as a numbered short list, not paragraphs. One round of questions max — if the user's first response is still ambiguous, make your best guess and explain it in the VERIFY step's summary.

### Q1: Type (when not pinned)

```
Which diagram fits best?
1. Sequence — message exchange over time between participants
2. Component — static structure of software pieces and their interfaces
3. C4 container — same level of abstraction, but C4-styled (web app, API, DB, external systems)
4. Class — object-oriented type structure
5. State — lifecycle of one entity
6. Activity — procedural flow with branches and loops
7. Deployment — where things physically run
8. ER — data model and cardinality
9. Use case — actor goals against a system boundary
10. Pipeline — left-to-right data flow (producers → broker → processors → sinks); use for streaming / "system design" prompts

(Or describe what you want to communicate and I'll pick.)
```

**Cap the list at 3 candidates, always.** The full ten-option list above is the master reference for you to pick from — what the user sees is at most three options trimmed to what their prompt suggests. Showing all ten signals indecision and forces the user to do triage work.

How to pick the three:

- **Specific prompt** ("I want to show how login works") — list the obvious 2–3 (sequence / activity / C4-dynamic). Drop anything irrelevant.
- **Streaming / pipeline / system-design prompt** ("kafka flow", "streaming architecture", "system design for our ingest", "data pipeline", "ETL diagram") — default three are:
  1. **Pipeline** — left-to-right data flow (top pick)
  2. **C4 Container** — if architecture-level abstraction matters more than stages
  3. **Deployment** — if the user is asking about where the pipeline runs more than how it's shaped
- **Maximally vague prompt** ("draw a diagram of our system") — even when nothing else trims the candidate set, **still cap at 3**. The default three for production software are:
  1. **C4 Container** — the architecture map (most common ask for "our system")
  2. **Sequence** — message flow for one scenario
  3. **ER** — data model

  In the rare case those three don't fit the implied domain, swap one out (e.g. State for an embedded/device-control product, Deployment for an ops-heavy ask, Pipeline for a data-heavy ask). Three options is the ceiling regardless.

Resist the urge to list 5–6 "just in case." That defeats the purpose of trimming. If you can't decide between 4 candidates, pick the 3 most likely and offer "Or describe what you want to communicate and I'll pick" as the escape hatch — that catches the rest.

### Q2: Participants (when not pinned)

```
Who's in the diagram? Name the participants/components/entities and (if relevant) their type — e.g. "Browser (actor), API (Go service), Postgres (DB), Stripe (external)".
```

### Q3: Scope (when "everything")

```
Which slice? A single flow / a subsystem / a public boundary — vs "the whole system" which is usually too much for one diagram. Suggest a starting scope.
```

## What NOT to ask

Don't ask:
- Theming preferences. Default is `!theme plain`. The user can override after.
- Render format. Default is SVG; the output contract documents PNG as an alternative.
- File name. Derive from scope ("login-sequence.puml").
- Direction (LR vs TB). The reference for each type sets a sensible default.

These are decisions the skill makes, not the user.

## Propose-and-go (alternative to questions)

For mildly ambiguous prompts, prefer **propose-and-go** over a question:

> "Treating this as a sequence diagram of the login flow with three participants: Browser, API, Auth Service. Generating now — say so if you wanted a different scope or type."

This keeps the conversation moving and gives the user something concrete to react to. Use it when one interpretation is clearly the most likely; fall back to questions only when two interpretations are equally plausible.

## When the user pastes an existing `.puml`

Iteration mode. Skip ELICIT entirely. Read the existing file:
- Diagram type is whatever the existing file declares.
- Participants are already named.
- Scope is whatever's in there.

Apply the requested change minimally — don't rewrite the diagram unless asked. Preserve the existing diagram name and structure.
