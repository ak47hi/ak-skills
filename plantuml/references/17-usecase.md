# Use case diagrams

Shows actors and the goals (use cases) they pursue against a system. Use when the question is "who interacts with our system and what do they want to do".

Use case diagrams are about **goals at the system boundary**, not implementation. Don't try to show internal flow — that's sequence or activity.

## Actors

Declare actors outside any system boundary:

```puml
actor "Customer" as C
actor "Support Agent" as S
actor "Payment Gateway" as PG <<system>>
```

Use `<<system>>` stereotype for non-human actors (other systems, scheduled processes).

Short form `:Customer:` works but the `actor` keyword reads better and supports aliasing.

## Use cases

Use cases live *inside* the system boundary.

```puml
rectangle "Order Management System" {
    usecase "Place Order" as UC1
    usecase "Cancel Order" as UC2
    usecase "View Order History" as UC3
    usecase "Process Refund" as UC4
}
```

Use the `usecase` keyword with aliasing. Short form `(Place Order)` works but loses the alias for cross-references.

## System boundary

`rectangle "<system name>" { ... }` is the conventional boundary. `package` also works.

**Rule:** actors live outside the boundary. Use cases live inside. Mixing this is a common error.

## Associations

Actors associate with use cases via plain lines:

```puml
C --> UC1
C --> UC2
C --> UC3
S --> UC4
UC4 --> PG
```

The arrow direction conventionally goes from the initiator to the use case. For "primary" vs "secondary" actors (primary initiates, secondary is involved), put the primary on the left and the secondary on the right, with arrows accordingly.

## Include and extend

```puml
UC1 ..> UC5 : <<include>>
UC6 ..> UC2 : <<extend>>
```

- `<<include>>`: UC1 always uses UC5. UC5 is required behavior.
- `<<extend>>`: UC6 optionally adds to UC2. UC6 is conditional behavior.

Both use the `..>` (dashed arrow) — don't use `-->` for include/extend.

## Generalization

Actor inheritance:

```puml
actor User
actor Customer
actor Admin
Customer --|> User
Admin --|> User
```

Use case generalization:

```puml
usecase "Pay" as UCP
usecase "Pay by Card" as UCC
usecase "Pay by Transfer" as UCT
UCC --|> UCP
UCT --|> UCP
```

Use generalization only when it materially helps the diagram. For most diagrams, just listing the specific use cases is clearer.

## Direction

Default top-to-bottom; for typical use case diagrams, left-to-right reads better:

```puml
left to right direction
```

Apply this almost always for use case diagrams.

## Notes

```puml
note right of UC1 : requires authenticated session
```

## Anti-patterns specific to use case

- **Actor inside system boundary.** Actors are outside the `rectangle "..." { ... }`.
- **Wrong arrow for include/extend.** Use `..>` (dashed), not `-->`.
- **Decomposing into implementation steps.** "Validate input" / "Save to DB" are not use cases — they're implementation. Use cases are goals at the boundary.
- **30 use cases in one diagram.** Decompose by subsystem or by actor; one diagram per audience.
- **Internal calls between use cases.** Use cases aren't functions. They don't "call" each other (except via the formal `<<include>>` / `<<extend>>` relations).

## Template

See `templates/usecase.puml`.
