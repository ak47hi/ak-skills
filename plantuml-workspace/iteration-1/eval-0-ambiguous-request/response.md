"Our system" can mean a few different diagrams — they answer different questions. To pick the right one, I need three things pinned down:

**1. Which diagram fits best?**

1. **C4 Container** — the architecture map: apps, services, datastores, external systems, and the tech behind each (most common ask for "our system").
2. **Sequence** — message flow over time for one specific scenario (e.g. "what happens when a user logs in").
3. **ER** — the data model: entities and how they relate.

(Or describe what you want to communicate and I'll pick.)

**2. Who's in it?**

Name the main pieces — e.g. "Web app (React), API (Go), Postgres, Stripe (external), background worker (Python)". For a sequence diagram, the actors/services involved in that one flow.

**3. What's the scope?**

"The whole system" is usually too much for one diagram. A good starting scope is one of:
- The public boundary (what users and external systems see)
- One subsystem (e.g. billing, auth, ingest)
- One flow end-to-end (e.g. signup, checkout)

Reply with the three answers (even one-liners are fine) and I'll generate it.
