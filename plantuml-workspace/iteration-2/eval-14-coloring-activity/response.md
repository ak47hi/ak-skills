# Payment processing activity diagram (colored happy/sad paths)

```puml
@startuml payment-processing-flow
!theme plain

start

:Validate input; <<#D5F5E3>>

if (valid?) then (yes)
    :Charge card; <<#D5F5E3>>
    if (charge succeeded?) then (yes)
        :Send receipt; <<#D5F5E3>>
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

Activity diagram of the payment flow with the happy path (validate, charge, send receipt) tinted green and the sad path (log error — on either invalid input or charge failure) tinted red.

## Notes on the coloring

- Per-action inline color uses the post-semicolon form `:text; <<#hex>>`. The pre-colon form `#hex:text;` is deprecated in current PlantUML and emits a render warning.
- Color is layered on text labels (`Send receipt`, `Log error`), so the diagram still reads correctly in monochrome or for color-blind viewers — the success/failure meaning is not color-only.
- I split the original "on failure log error" into two failure actions (invalid input vs. charge failed) because the prompt has two failure points (validation and charge). Both stay red. If you'd rather collapse them into a single shared `:Log error;` action joined from both branches, say so and I'll restructure.
- I used a per-action inline `<<#hex>>` rather than the skill's full colored preset because you wanted targeted happy/sad emphasis, not a whole-diagram restyle. If you do want the Confluence-friendly preset applied across the whole diagram (uniform action backgrounds, colored start/stop circles, styled decision diamonds), let me know.
