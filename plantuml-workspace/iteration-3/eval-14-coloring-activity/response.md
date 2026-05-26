```puml
@startuml payment-processing-flow
!theme plain

start

:Validate input;

if (input valid?) then (yes)
    :Charge card;
    if (charge succeeded?) then (yes)
        :Send receipt (success); <<#D5F5E3>>
        stop
    else (no)
        :Log error (charge failed); <<#FFCCCC>>
        stop
    endif
else (no)
    :Log error (invalid input); <<#FFCCCC>>
    stop
endif

@enduml
```

Render: `plantuml -tsvg payment-processing-flow.puml`

Payment processing flow: validates input, charges the card, then branches to a green "send receipt" success step or a red "log error" step (one for charge failure, one for invalid input).

Notes on the coloring approach:

- Per-action `<<#HexColor>>` after the semicolon is the current PlantUML syntax. The older `#color:text;` form (color before the colon) is deprecated and emits a render warning.
- Color is layered on top of labels ("success", "charge failed", "invalid input"), not replacing them — the diagram still reads correctly in monochrome and for color-blind viewers, which is the rule for color in this skill.
- `!theme plain` stays as the base; the canonical colored preset in `references/22-styling-colored.md` is for whole-diagram restyles, not targeted happy/sad highlighting of a couple of steps.
