```puml
@startuml payment-processing-activity
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

```bash
plantuml -tsvg payment-processing-activity.puml
```

Activity diagram of the payment flow: validate input, charge card, then branch on charge outcome to a green success node (send receipt) or a red failure node (log error), with text labels so the happy/sad paths read in monochrome too.
