```puml
' C4 Container diagram — Order Management System.
' Stdlib include. Fallback for older PlantUML builds:
'   !include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

@startuml c4-container-order-management
!include <C4/C4_Container>

SHOW_LEGEND()

title Container Diagram — Order Management System

Person(customer, "Customer", "Places orders, manages account.")

System_Boundary(oms, "Order Management System") {
    Container(web, "Web", "React, TypeScript", "Customer-facing SPA.")
    Container(api, "API", "Go, gRPC", "Public-facing API gateway; routes requests, authn/authz.")
    Container(orderSvc, "Order Service", "Go", "Order lifecycle and business rules.")
    Container(authSvc, "Auth Service", "Go", "Authentication and session management.")
    ContainerDb(db, "Postgres", "Postgres", "Customers, orders, sessions.")
    ContainerQueue(bus, "Event Bus", "AWS SQS", "Domain events: order placed, paid, fulfilled.")
}

System_Ext(stripe, "Stripe", "Payment processing.")
System_Ext(sendgrid, "SendGrid", "Transactional email.")

Rel(customer, web, "Uses", "HTTPS")
Rel(web, api, "Calls", "gRPC-Web / HTTPS")
Rel(api, authSvc, "Verifies sessions via", "gRPC")
Rel(api, orderSvc, "Routes order operations to", "gRPC")
Rel(authSvc, db, "Reads/writes user and session data", "SQL")
Rel(orderSvc, db, "Reads/writes order data", "SQL")
Rel(orderSvc, bus, "Publishes domain events to", "AWS SDK")
Rel(orderSvc, stripe, "Charges and refunds via", "HTTPS")
Rel(orderSvc, sendgrid, "Sends transactional email via", "HTTPS")

@enduml
```

Render: `plantuml -tsvg diagram.puml`

C4 Container view of the Order Management System showing the Customer interacting with the Web SPA, which calls the API gateway that fans out to Order Service and Auth Service over gRPC, both backed by Postgres; the Order Service publishes domain events to an SQS event bus and integrates with Stripe (payments) and SendGrid (email).
