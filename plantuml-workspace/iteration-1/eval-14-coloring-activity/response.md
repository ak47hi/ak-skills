```puml
@startuml payment-processing
!theme plain

start

:Validate input;
:Charge card;

if (charge succeeded?) then (yes)
    :Send receipt (success); <<#D5F5E3>>
    stop
else (no)
    :Log error (failure); <<#FFCCCC>>
    stop
endif

@enduml
```

Render: `plantuml -tsvg payment-processing.puml`

Payment processing activity diagram: validate input and charge card, then branch on charge outcome — green-tinted "Send receipt" on success, red-tinted "Log error" on failure. Each colored step also carries an explicit `(success)` / `(failure)` label so the happy/sad paths remain legible in monochrome rendering or for color-blind readers.

Two notes on the coloring approach:

- Inline `<<#hex>>` (after the semicolon) is the supported form in modern PlantUML. The older `#hex:text;` syntax still parses but emits a deprecation warning.
- I left `Validate input` and `Charge card` uncolored on purpose: they run on both paths, so painting them green would imply they only happen on success. Color is reserved for the branch-specific outcomes.
