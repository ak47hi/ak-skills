```puml
@startuml payment-processing
!theme plain

start

:Validate input;
:Charge card;

if (charge successful?) then (yes)
    :Send receipt; <<#D5F5E3>>
    stop
else (no)
    :Log error; <<#FFCCCC>>
    stop
endif

@enduml
```

```bash
plantuml -tsvg payment-processing.puml
```

Activity diagram of the payment flow: validate input, charge card, then branch to send receipt (green) on success or log error (red) on failure, with explicit text labels carrying the meaning so color is additive rather than load-bearing.
