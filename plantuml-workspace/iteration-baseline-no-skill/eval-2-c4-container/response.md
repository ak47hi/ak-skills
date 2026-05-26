Here's a C4 **Container** diagram for the order-management system. It uses the [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML) stdlib (loaded via `!include`), so no local install is needed beyond PlantUML itself.

```plantuml
@startuml C4_Container_OrderManagement
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

LAYOUT_WITH_LEGEND()
title Container Diagram - Order Management System

Person(customer, "Customer", "Places and tracks orders")

System_Boundary(oms, "Order Management System") {
    Container(web, "Web App", "React, TypeScript", "Single-page app for browsing products, placing orders, and viewing order history")
    Container(api, "API Gateway", "Go, gRPC", "Public-facing API; authenticates requests and routes to internal services")
    Container(orderSvc, "Order Service", "Go", "Manages order lifecycle: create, update, fulfill, cancel")
    Container(authSvc, "Auth Service", "Go", "Issues and validates auth tokens; manages user identities")
    ContainerDb(db, "Database", "PostgreSQL", "Stores users, orders, line items, and payment metadata")
    ContainerQueue(bus, "Event Bus", "AWS SQS", "Asynchronous order/payment/email events")
}

System_Ext(stripe, "Stripe", "Payment processing")
System_Ext(sendgrid, "SendGrid", "Transactional email delivery")

Rel(customer, web, "Uses", "HTTPS")
Rel(web, api, "Calls", "gRPC-Web / HTTPS")

Rel(api, authSvc, "Validates tokens, signs in users", "gRPC")
Rel(api, orderSvc, "Forwards order requests", "gRPC")

Rel(orderSvc, db, "Reads/writes orders", "SQL/TCP")
Rel(authSvc, db, "Reads/writes users", "SQL/TCP")

Rel(orderSvc, bus, "Publishes order events", "AWS SDK")
Rel(bus, orderSvc, "Delivers async events", "AWS SDK")

Rel(orderSvc, stripe, "Charges customer cards", "HTTPS/REST")
Rel_R(bus, sendgrid, "Sends order confirmation emails", "HTTPS/REST")

SHOW_LEGEND()
@enduml
```

### Modeling notes

- **Customer** is modeled as a `Person` outside the system boundary.
- The **Order Management System** boundary groups the six internal containers; **Stripe** and **SendGrid** are `System_Ext` (third-party SaaS).
- I used the specialized shapes `ContainerDb` for Postgres and `ContainerQueue` for SQS so they're visually distinct from regular services.
- The **API** is the only inbound entry point from the Web app; internal service-to-service calls (API → OrderService, API → AuthService) use gRPC.
- **SQS** is shown as a first-class container with bidirectional relations to OrderService (publish + consume), and an outbound relation to SendGrid representing a worker/consumer that turns order events into email sends. If you prefer, you can model that worker as its own `Container` instead of letting the queue "send" — happy to refactor.
- **Stripe** is called synchronously from OrderService during checkout (typical pattern); if your design uses a dedicated PaymentService, that should become its own container.

### Render it

```bash
plantuml diagram.puml          # PNG
plantuml -tsvg diagram.puml    # SVG
```

Or paste into the [PlantUML web server](https://www.plantuml.com/plantuml/uml/).

### Likely follow-ups

- Want a **Context diagram** (one step zoomed out) too?
- Should I split the API into separate **edge / BFF** containers, or break out a **Payment Service** in front of Stripe?
- Want me to add a deployment view (K8s pods, RDS, etc.) as a separate diagram?
