```puml
' C4 Container diagram — Order Management System.
' Shows: containers inside the OMS, plus external systems and the customer.
' Does NOT show internals of any container — that's the Component level.
'
' Stdlib include. Fallback for older PlantUML builds:
'   !include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

@startuml oms-c4-container
!include <C4/C4_Container>

' Optional modernized style (C4-PlantUML v2.13.0+).
' !ROUNDED_STYLE=1
' !NEW_C4_STYLE=1

SHOW_LEGEND()

title Container Diagram — Order Management System

Person(customer, "Customer", "Places orders, manages account.")

System_Boundary(oms, "Order Management System") {
    Container(web, "Web", "React, TypeScript", "Customer-facing SPA.")
    Container(api, "API", "Go, gRPC", "Edge API; authn/authz, routes requests to internal services.")
    Container(auth, "AuthService", "Go", "Authentication and session management.")
    Container(orders, "OrderService", "Go", "Order lifecycle, pricing, business rules.")
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
Rel(orders, sendgrid, "Sends order email via", "HTTPS/REST")

@enduml
```

Render: `plantuml -tsvg oms-c4-container.puml`

Container-level view of the Order Management System showing the customer, six internal containers (Web, API, AuthService, OrderService, Postgres, SQS event bus), and two external SaaS dependencies (Stripe, SendGrid) with the protocol on every edge.
