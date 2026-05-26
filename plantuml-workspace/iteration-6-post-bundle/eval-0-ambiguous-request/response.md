Before I draw anything I need to pin down three things — "our system" and "a diagram" are both unscoped, and I don't have prior context on this codebase in this session.

**1. Which diagram fits best?**

1. **C4 Container** — the architecture map (web app, API, DB, external systems) — most common ask for "our system"
2. **Sequence** — message exchange over time for one specific flow (e.g. login, checkout)
3. **ER** — data model entities and their cardinality

(Or describe what you want to communicate and I'll pick — e.g. "show how requests flow", "show what runs where", "show the data model".)

**2. Who's in it?**

Name the main pieces and (if relevant) their type — e.g. "Browser (actor), API (Go service), Postgres (DB), Stripe (external)". If you'd rather, point me at a repo / README / design doc and I'll derive the participants from there.

**3. What slice?**

"The whole system" is usually too much for one diagram. A subsystem, a public boundary, or a single user-facing flow renders better. If you genuinely want a bird's-eye view, C4 Container is the right level — anything narrower fits better as Sequence or Component.

Once I have those three, I'll generate the `.puml` and the render command in one shot.
