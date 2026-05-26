```puml
' C4 Container diagram — Order Management System.
' Shows the apps/services/datastores inside the system, plus external touchpoints.
' Does NOT show internals of any container — that's the Component level.
'
' Stdlib include. Fallback for older PlantUML builds:
'   !include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

@startuml c4-container-order-management
!include <C4/C4_Container>

SHOW_LEGEND()

title Container Diagram — Order Management System

Person(customer, "Customer", "Places orders, manages account.")

System_Boundary(system, "Order Management System") {
    Container(web, "Web", "React, TypeScript", "Customer-facing SPA.")
    Container(api, "API", "Go, gRPC", "Entry point; routes RPCs, applies authn/authz.")
    Container(auth, "AuthService", "Go", "Authentication and session validation.")
    Container(orders, "OrderService", "Go", "Order lifecycle and business rules.")
    ContainerDb(db, "Postgres", "PostgreSQL", "Customers, orders, payment metadata.")
    ContainerQueue(bus, "Event Bus", "AWS SQS", "Domain events: order placed, paid, cancelled.")
}

System_Ext(stripe, "Stripe", "Payment processing.")
System_Ext(sendgrid, "SendGrid", "Transactional email delivery.")

Rel(customer, web, "Uses", "HTTPS")
Rel(web, api, "Calls", "gRPC-Web / HTTPS")
Rel(api, auth, "Verifies sessions via", "gRPC")
Rel(api, orders, "Routes order operations to", "gRPC")
Rel(auth, db, "Reads/writes user data", "SQL/TCP")
Rel(orders, db, "Reads/writes order data", "SQL/TCP")
Rel(orders, bus, "Publishes domain events to", "AWS SDK")
Rel(orders, stripe, "Charges and refunds via", "HTTPS/REST")
Rel(orders, sendgrid, "Sends transactional email via", "HTTPS/REST")

@enduml
```

Render: `plantuml -tsvg diagram.puml`

C4 Container view of the order management system, with the Customer as a Person, the six internal containers (Web, API, AuthService, OrderService, Postgres, SQS event bus) inside the system boundary, and Stripe + SendGrid as external systems.
