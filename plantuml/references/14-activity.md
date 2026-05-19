# Activity diagrams (beta syntax)

Shows a procedural flow with branches, loops, parallel paths, and optional swimlanes. Use when the question is "what are the steps of this procedure / process".

PlantUML has two activity syntaxes: legacy (`(*) --> :step;`) and beta (`:step;` with structured control flow). **Always use beta.** It's the supported modern syntax; legacy will eventually be removed.

## Start, actions, stop

```puml
start
:Receive request;
:Authenticate user;
:Authorize action;
:Execute;
stop
```

Each action is `:text;`. `start` and `stop` (or `end`) bookend the flow.

## Conditionals

```puml
if (authenticated?) then (yes)
    :Load user profile;
else (no)
    :Return 401;
    stop
endif
```

Multiple branches:

```puml
switch (status?)
case (DRAFT)
    :Allow edits;
case (SUBMITTED)
    :Lock for review;
case (PAID)
    :Trigger fulfillment;
endswitch
```

## Loops

```puml
while (more items?) is (yes)
    :Process item;
endwhile (no)

repeat
    :Try connection;
repeat while (failed?) is (yes) not (no)
```

Use `while` when the condition is checked at the top, `repeat` when at the bottom (do-while).

## Parallel

```puml
fork
    :Send confirmation email;
fork again
    :Update analytics;
fork again
    :Write audit log;
end fork
```

Use `end merge` instead of `end fork` when the parallel paths must synchronize before the next step (rare).

## Swimlanes

When multiple actors execute different steps, swimlanes show *who* does each:

```puml
|User|
start
:Submit form;
|System|
:Validate;
if (valid?) then (yes)
    :Persist;
    |User|
    :Receive confirmation;
else (no)
    |User|
    :Show errors;
endif
stop
```

Swimlanes are columns. Switch by writing `|<name>|` before the actions for that lane.

Don't add swimlanes if there's only one actor — they add noise without value.

## Partitions (logical grouping)

```puml
partition "Authentication" {
    :Verify token;
    :Load user;
}
partition "Authorization" {
    :Load permissions;
    :Check policy;
}
```

Partitions are visual grouping by step phase. Use them when the procedure has clear phases that aren't owned by different actors (otherwise prefer swimlanes).

## Notes

```puml
:Charge card;
note right: idempotency key required
```

## Detach / kill

For paths that intentionally don't rejoin:

```puml
if (timeout?) then (yes)
    :Cancel request;
    kill
endif
```

`kill` ends the path here without joining back. Use sparingly.

## Connectors

For arrow labels on transitions:

```puml
:A;
-> takes the happy path;
:B;
```

## Anti-patterns specific to activity

- **Mixing beta and legacy.** Don't write `(*) --> :step;` inside a beta diagram. Pick one (always beta).
- **Decorative swimlanes.** Single-actor procedures don't need swimlanes.
- **Unbalanced control flow.** Every `if` needs `endif`, every `while` needs `endwhile`, every `fork` needs `end fork`. PlantUML parses strictly.
- **Sequence-shaped activity.** If the diagram is fundamentally about message exchange between participants, it's a sequence diagram, not an activity diagram.

## Template

See `templates/activity.puml`.
