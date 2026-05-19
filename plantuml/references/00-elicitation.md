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

(Or describe what you want to communicate and I'll pick.)
```

Trim to the 2–3 candidates that actually fit the user's prompt — don't show all nine if the user said "I want to show how login works" (that's sequence vs activity vs C4-dynamic).

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
