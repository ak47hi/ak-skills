```puml
@startuml er-billing
!theme plain

skinparam linetype ortho

entity Customer {
    * id : uuid <<generated>>
    --
    * email : varchar
    * created_at : timestamp
    name : varchar
}

entity Order {
    * id : uuid <<generated>>
    --
    * customer_id : uuid <<FK>>
    * payment_method_id : uuid <<FK>>
    * status : varchar
    * total_cents : int
    * created_at : timestamp
}

entity LineItem {
    * id : uuid <<generated>>
    --
    * order_id : uuid <<FK>>
    * sku : varchar
    * quantity : int
    * unit_price_cents : int
}

entity PaymentMethod {
    * id : uuid <<generated>>
    --
    * customer_id : uuid <<FK>>
    * kind : varchar
    last4 : varchar
}

' Crow's-foot cardinality:
'   ||   exactly one         |o   zero or one
'   }|   one or many         }o   zero or many
Customer ||--o{ Order
Customer ||--o{ PaymentMethod
Order ||--|{ LineItem
PaymentMethod ||--o{ Order

note right of Order : payment_method_id must reference\na PaymentMethod owned by customer_id

@enduml
```

Render: `plantuml -tsvg diagram.puml`

Billing schema with Customer, Order, LineItem, and PaymentMethod, where each Order references both its owning Customer and one of that Customer's PaymentMethods (cross-entity ownership constraint captured as a note).
