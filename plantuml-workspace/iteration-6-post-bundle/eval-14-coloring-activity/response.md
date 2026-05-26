```puml
@startuml payment-processing-activity
!theme plain

start

:Validate input;

if (valid?) then (yes)
    :Charge card;
    if (charge successful?) then (yes)
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

```bash
plantuml -tsvg payment-processing-activity.puml
```

Activity diagram of payment processing: validate input then charge card, with the success path (send receipt) shaded green and both failure paths (log error) shaded red as a redundant signal alongside the text labels.
