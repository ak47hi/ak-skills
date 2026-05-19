# Class diagrams

Shows object-oriented type structure: classes, interfaces, enums, fields, methods, and the relations between them. Use when the question is "what types exist and how do they relate".

For data schemas (tables, PK/FK, cardinality), use ER (`references/16-er.md`) instead.

## Declarations

```puml
class Order
abstract class PaymentMethod
interface Repository
enum OrderStatus {
    DRAFT
    SUBMITTED
    PAID
    CANCELLED
}
```

With fields and methods:

```puml
class Order {
    - id: UUID
    - customerId: UUID
    - status: OrderStatus
    - total: Money
    + submit(): void
    + cancel(reason: String): void
    {static} + draft(customerId: UUID): Order
    {abstract} # validate(): boolean
}
```

## Visibility

Required on every member. Read as "I thought about access":

| Symbol | Meaning |
|---|---|
| `+` | Public |
| `-` | Private |
| `#` | Protected |
| `~` | Package-private |

Omitted visibility is an anti-pattern (see `references/90-anti-patterns.md`).

## Modifiers

- `{static}` — class-level (not instance)
- `{abstract}` — abstract member

Place modifiers before the visibility marker or before the name:

```puml
{static} + createDefault(): Order
{abstract} # validate(): boolean
```

## Generics

```puml
class Repository<T> {
    + findById(id: UUID): T?
    + save(entity: T): void
}
class OrderRepository extends Repository<Order>
```

## Relations

Pick the right arrow — they each mean something specific.

| Syntax | Meaning |
|---|---|
| `A <\|-- B` | B inherits from A (specialization) |
| `A <\|.. B` | B implements interface A (realization) |
| `A *-- B` | A composes B (lifetime owned, "part of") |
| `A o-- B` | A aggregates B (references, lifetime independent) |
| `A --> B` | A has association with B (uses, refers to) |
| `A ..> B` | A depends on B (transient, e.g. via parameter) |

Convention to follow:

```puml
PaymentMethod <|-- CreditCard
PaymentMethod <|-- BankTransfer
Repository <|.. OrderRepository
Order *-- LineItem
Order o-- Customer
Order --> PaymentMethod
OrderService ..> Order
```

## Multiplicity on associations

Always label multiplicity on associations and aggregations:

```puml
Order "1" *-- "1..*" LineItem
Customer "1" o-- "*" Order
```

Common values: `1`, `0..1`, `*` (zero or more), `1..*` (one or more), specific numbers.

## Packages

```puml
package "domain.order" {
    class Order
    class LineItem
}
package "domain.payment" {
    abstract class PaymentMethod
    class CreditCard
    class BankTransfer
}
```

## Notes

```puml
note right of Order: invariant: status transitions only forward
note "Implements PCI-DSS" as N1
Order .. N1
```

## Layout hints

For wide hierarchies:

```puml
left to right direction
```

For orthogonal (right-angled) connectors:

```puml
skinparam linetype ortho
```

Apply orthogonal layout only when the diagram is dense — for sparse diagrams, the default curved/diagonal layout reads better.

## Hiding noise

For overview diagrams that should show structure without member detail:

```puml
hide members
hide empty members
hide circle
```

Use `hide members` for high-level "shape of the model" diagrams; show members only when the methods/fields are the point.

## Anti-patterns specific to class

- **No visibility markers.** Every member needs one of `+ - # ~`.
- **`-->` for everything.** Pick the relation type that matches the semantics (composition vs aggregation vs association vs dependency vs inheritance).
- **No multiplicity.** `Order --> LineItem` doesn't say whether one order has one line item or many. Label it.
- **Stuffed methods.** If a class has 30 methods, the diagram is documenting code, not modeling. Show only the methods that matter for the relationships being illustrated.

## Template

See `templates/class.puml`.
