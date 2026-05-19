# Deployment diagrams

Shows *where* software runs — physical hosts, runtime containers, datastores, queues, and the artifacts deployed onto them. Use when the question is "what's the runtime / infrastructure topology".

Component diagrams (`references/11-component.md`) are about *what* the software is made of. Deployment diagrams are about *where* it lives. If you find yourself drawing only logical components with no infrastructure, it's a component diagram.

## Containers

Pick the most specific keyword that matches what you're modeling:

| Keyword | Use for |
|---|---|
| `node` | Physical or virtual host, server, VM, pod |
| `cloud` | Cloud provider / SaaS / external boundary |
| `database` | Datastore (relational, KV, doc) |
| `queue` | Message broker, topic, stream |
| `stack` | A stack of components |
| `artifact` | Deployable unit (jar, container image, binary) |
| `folder` | Filesystem-like grouping |
| `file` | A specific file |
| `frame` | Generic container (last resort) |
| `package` | Logical grouping (rare in deployment — usually a node or cloud is more accurate) |
| `rectangle` | Generic shape (avoid unless none of the above fits) |

## Nesting

Deployment is about nesting:

```puml
cloud "AWS" {
    node "EKS Cluster (us-east-1)" as eks {
        node "Pod: api" {
            artifact "api-server.jar"
        }
        node "Pod: worker" {
            artifact "worker.jar"
        }
    }
    database "RDS Postgres" as db
    queue "SQS: events" as bus
}

node "Client" {
    artifact "browser app"
}
```

Hosts contain artifacts. Clouds contain hosts. The hierarchy is the point.

## Relations

```puml
[browser app] --> [api-server.jar] : HTTPS
[api-server.jar] --> db : SQL
[api-server.jar] --> bus : publish
[worker.jar] --> bus : consume
```

Use plain `--` for "deployed on" / "lives in" if you ever need to draw it (most of the time, nesting expresses this).

Arrow styles:
- `-->` solid for synchronous runtime calls
- `..>` dashed for asynchronous / loose coupling
- `==>` bold for high-volume / critical paths (use sparingly)

## Labels on relations

Always label cross-boundary relations with the protocol or volume info:

```puml
[Web] --> [API] : HTTPS/JSON
[API] --> db : SQL (read replicas)
[Worker] --> bus : Kafka
```

## Layout direction

Default top-to-bottom. For wide topologies (e.g. multi-region), use:

```puml
left to right direction
```

## Anti-patterns specific to deployment

- **Generic `node` for everything.** Use `cloud`, `database`, `queue` where they apply. A diagram where everything is `node` reads as "I didn't think about types".
- **Flat structure.** If the diagram is a single level of boxes with no nesting, it's a misrouted component diagram. Deployment is about hierarchy.
- **No protocols on cross-boundary lines.** "X talks to Y" tells the reader nothing. Label with protocol (HTTPS, gRPC, SQL, Kafka).
- **Mixing logical and physical inconsistently.** Pick: are you showing logical components on physical hosts (preferred), or pure physical infra? Don't mix the two granularities arbitrarily.

## Template

See `templates/deployment.puml`.
