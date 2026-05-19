# Sequence diagrams

Shows messages exchanged between participants over time. Use when the question is "what happens in what order between which actors".

## Participants

Always declare participants explicitly at the top — don't let PlantUML infer them from message lines. The participant type affects the visual:

| Keyword | Visual | When to use |
|---|---|---|
| `actor` | Stick figure | Human users, external roles |
| `participant` | Box (default) | Generic process / service / object |
| `boundary` | Circle with line | UI boundary, gateway |
| `control` | Circle with arrow | Coordinator, orchestrator |
| `entity` | Circle with line under | Domain entity |
| `database` | Cylinder | Database, persistent store |
| `collections` | Stack of boxes | Collection, multi-instance |
| `queue` | Cylinder horizontal | Queue, broker, topic |

Syntax:

```puml
actor User
participant "Web App" as Web
control AuthService as Auth
database Users
queue EventBus
```

Use `as` to alias when the display label has spaces or differs from the variable.

## Grouping participants (`box`)

For diagrams with >5 participants, group them visually:

```puml
box "Frontend"
    actor User
    participant "Web App" as Web
end box
box "Backend"
    participant API
    control AuthService as Auth
end box
box "Data"
    database Users
end box
```

Don't use `box` for fewer than 4 participants — adds visual noise without value.

## Arrows

Pick one style per relation type and stay consistent within the diagram.

| Syntax | Meaning |
|---|---|
| `->` | Synchronous message (default for most cases) |
| `-->` | Response / return (dashed) |
| `->>` | Asynchronous message (thin arrow) |
| `-x` | Lost message |
| `<->` | Bidirectional (use sparingly) |

Convention this skill follows:
- **Request:** `->` (solid)
- **Response:** `-->` (dashed)
- **Fire-and-forget / async:** `->>` (thin)

If you find yourself using all three within one diagram and the user hasn't asked for that distinction, simplify to just `->` and `-->`.

## Messages and activation

Basic message:

```puml
User -> Web: POST /login {email, pwd}
Web -> Auth: verifyCredentials(email, pwd)
Auth -> Users: SELECT by email
Users --> Auth: row
Auth --> Web: {ok, token}
Web --> User: 200 {token}
```

Activation (lifeline rectangles showing when a participant is "active"):

```puml
User -> Web ++: POST /login
Web -> Auth ++: verify
Auth -> Users ++: query
Users --> Auth --: row
Auth --> Web --: ok
Web --> User --: 200
```

Rules:
- Use activation only when you want to show overlapping activity or nested calls. For linear flows, skip it.
- Every `++` needs a matching `--`. Unmatched activation reads as a stuck rectangle.

## Notes

Anchor every note. Free-floating `note: text` is ambiguous.

```puml
note left of User: starts logged out
note right of Auth: rate-limited
note over Web, Auth: TLS terminated at Web
```

## Grouping messages (control flow)

PlantUML supports common control-flow blocks:

```puml
alt happy path
    Auth --> Web: ok
else credentials invalid
    Auth --> Web: 401
else service down
    Auth --> Web: 503
end

opt user opted in
    Web -> Analytics: track(login)
end

loop until token valid
    Web -> Auth: refresh
end

par
    Web -> AuditLog: log(login)
also
    Web -> Cache: invalidate(session)
end
```

Use `alt`/`else` for mutually exclusive paths, `opt` for optional steps, `loop` for repetition, `par` for parallel branches.

## Autonumber

For sequences with 6+ messages, add `autonumber` after the participants. Skip it for short diagrams (3–5 messages); the numbers add visual noise without helping.

```puml
autonumber
User -> Web: ...
```

Customize: `autonumber 10 5` starts at 10, increments by 5.

## Dividers

For long sequences with phases, use `==` dividers:

```puml
== Authentication ==
User -> Web: login
...
== Session ==
Web -> User: 200 {token}
```

## Time gaps

`...` represents a passage of time:

```puml
Auth -> Email: send verification
...5 minutes later...
User -> Web: click verification link
```

## Direction

Default is top-to-bottom (each participant is a column, time flows down). Don't change this.

## Anti-patterns specific to sequence

- **Implicit participants.** `Alice -> Bob` without prior `participant Alice` declarations: works but renders both as plain boxes. Declare first.
- **Free-floating notes.** Always anchor.
- **Crossed lifelines.** If two participants' messages frequently jump across a third, reorder participants to put the most-communicating pairs adjacent.
- **Notes used as commentary.** Notes are part of the diagram, not the author's explanation of it. If you want to explain the diagram, that goes in the summary line, not in a note.

## Template

See `templates/sequence.puml` for the starting skeleton.
