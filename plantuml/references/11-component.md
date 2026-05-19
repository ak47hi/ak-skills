# Component diagrams

Shows the static structure of software pieces and the interfaces between them. Use when the question is "what is the software made of and what does each part expose".

For C4-style component diagrams, use `references/18-c4.md` instead — C4 has stricter rules about abstraction level.

## Components

Two ways to declare:

```puml
[Auth Service]
component "Auth Service" as Auth
```

Prefer the `component` keyword with `as` alias for anything more than a single word — readability wins.

For typed components (database, queue, cloud-hosted), use the matching container keyword:

```puml
database "Users DB" as UsersDB
queue "Event Bus" as Bus
cloud "AWS S3" as S3
```

(See "Grouping containers" below for the full list — they double as typed components when they sit at the leaf level.)

## Interfaces

Two notations — pick one and stick to it within a diagram.

**Lollipop (compact):**

```puml
() "REST API" as API
() "Admin gRPC" as Admin
[Auth Service] -up- API
[Auth Service] -up- Admin
```

**Named (explicit):**

```puml
interface "REST API" as API
interface "Admin gRPC" as Admin
```

Use lollipops when interfaces are owned by one component (one provider, many consumers). Use named interfaces when multiple components implement or share the interface.

## Ports (advanced)

For modeling specific connection points on a component:

```puml
component MyService {
    portin "HTTP" as http_in
    portout "Webhook" as webhook_out
}
```

Use ports only when the diagram is specifically about wiring (e.g. firmware, hardware-software boundaries, service-mesh-style sidecars). For typical software architecture diagrams, ports add noise.

## Relations

| Syntax | Meaning |
|---|---|
| `-->` | Dependency / usage |
| `--` | Plain association |
| `..>` | Dashed dependency (looser coupling) |
| `..` | Dashed association |

Convention: use `-->` for "X depends on / uses Y", `..>` for "X knows about Y but doesn't directly call". Don't mix `-->` and `..>` randomly.

With a label:

```puml
[Web] --> [API] : HTTPS/JSON
[API] --> [Auth Service] : gRPC
[Auth Service] --> [Users DB] : SQL
```

Directional variants for layout control:

```puml
[A] -right-> [B]
[A] -down-> [B]
```

Use sparingly — overuse fights PlantUML's auto-layout.

## Grouping containers

| Keyword | When |
|---|---|
| `package` | Logical grouping (a subsystem, a bounded context) |
| `node` | Physical or runtime host |
| `cloud` | Cloud service / external SaaS |
| `database` | Datastore |
| `queue` | Message broker / topic |
| `frame` | Abstract container with no other semantics |
| `folder` | Filesystem-like grouping |
| `rectangle` | Last-resort generic container |

Syntax:

```puml
package "Frontend" {
    [Web App]
    [Mobile App]
}
node "Kubernetes cluster" {
    [API]
    [Auth Service]
}
cloud "AWS" {
    database "Postgres RDS" as DB
}
```

## Direction

Default is top-to-bottom. For wide, shallow architectures, switch to:

```puml
left to right direction
```

Place this immediately after `!theme plain`.

## Anti-patterns specific to component

- **`[box]` for everything.** Use semantic containers (`database`, `queue`, `cloud`) at the leaf level where they apply.
- **No interfaces.** A component diagram with only `[boxes] --> [boxes]` is a component diagram in name only. Show interfaces — lollipops or named — for at least the public components.
- **Implicit subsystem boundaries.** If three components are clearly part of one subsystem, wrap them in a `package` or `node`. Don't leave the grouping to the reader.
- **Mixing physical and logical containers.** `package "Backend" { node "K8s" { ... } }` is fine. `node "K8s" { package "Backend" { ... } }` is confused — physical containers should be outer, logical inner.

## Template

See `templates/component.puml`.
