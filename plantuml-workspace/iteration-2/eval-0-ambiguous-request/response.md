"Our system" is too broad to draw in one diagram — different diagram types answer different questions about it. Three quick questions, then I'll generate:

**1. Which diagram fits best?**

1. **C4 Container** — architecture map: apps, services, datastores, external systems (the most common "draw our system" ask)
2. **Sequence** — message flow for one specific scenario over time
3. **ER** — data model and entity cardinality

(Or describe what you want to communicate and I'll pick — e.g. state machine for an entity's lifecycle, deployment for where things run, pipeline for streaming/data flow.)

**2. Who's in it?**

Name the participants/containers/entities and (if relevant) their type — e.g. "Web app (React), API (Go), Postgres (DB), Stripe (external)".

**3. What slice?**

"The whole system" is usually too much for one diagram. A useful scope is one of:
- A single public boundary (e.g. customer-facing surface)
- One subsystem (e.g. checkout, auth)
- One flow end-to-end (e.g. signup, order placement)

Answer those and I'll produce a named `.puml` plus the render command.
