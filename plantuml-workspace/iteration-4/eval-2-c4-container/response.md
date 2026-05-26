```puml
' C4 Container diagram — Order Management System.
' Shows the apps/services/datastores inside the system, plus external touchpoints.
' Does NOT show container internals — that would be the Component level.
'
' Stdlib include. Fallback for older PlantUML builds:
'   !include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

@startuml c4-container-order-management
!include <C4/C4_Container>

SHOW_LEGEND()

title Container Diagram — Order Management System

Person(customer, "Customer", "Places orders, tracks delivery, manages account.")

System_Boundary(oms, "Order Management System") {
    Container(web, "Web App", "React, TypeScript", "Customer-facing SPA.")
    Container(api, "API Gateway", "Go, gRPC", "Entrypoint; authn/authz, routing.")
    Container(auth, "Auth Service", "Go", "Authentication, session and token management.")
    Container(orders, "Order Service", "Go", "Order lifecycle, pricing, business rules.")
    ContainerDb(db, "Application DB", "Postgres", "Customers, orders, payment metadata.")
    ContainerQueue(bus, "Event Bus", "AWS SQS", "Domain events: order placed, paid, shipped.")
}

System_Ext(stripe, "Stripe", "Payment processing and refunds.")
System_Ext(sendgrid, "SendGrid", "Transactional email delivery.")

Rel(customer, web, "Uses", "HTTPS")

Rel(web, api, "Calls", "gRPC-Web / HTTPS")

Rel(api, auth, "Verifies sessions via", "gRPC")
Rel(api, orders, "Routes order operations to", "gRPC")

Rel(auth, db, "Reads/writes user data", "SQL")
Rel(orders, db, "Reads/writes order data", "SQL")

Rel(orders, bus, "Publishes domain events to", "AWS SDK")
Rel(orders, stripe, "Charges and refunds via", "HTTPS/JSON")
Rel(orders, sendgrid, "Sends transactional email via", "HTTPS/JSON")

@enduml
```

Render: `plantuml -tsvg c4-container-order-management.puml`

Container-level view of the order-management system: the customer reaches a React/TypeScript web app, which calls a Go gRPC API gateway that routes to the Auth and Order services backed by Postgres, with the Order service publishing to SQS and integrating outbound to Stripe and SendGrid.
