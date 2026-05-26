```puml
@startuml support-refund-flow
!theme plain

|Customer|
start
:Submit refund request;

|Agent|
:Review refund request;

if (approved?) then (yes)
    |BillingSystem|
    :Issue refund;
    :Notify customer of refund;
    |Customer|
    :Receive refund notification;
else (no)
    |Agent|
    :Send rejection email;
    |Customer|
    :Receive rejection email;
endif

stop

@enduml
```

Render: `plantuml -tsvg support-refund-flow.puml`

Activity diagram of the support refund flow across three swimlanes (Customer, Agent, BillingSystem), branching on the agent's approve/reject decision.
