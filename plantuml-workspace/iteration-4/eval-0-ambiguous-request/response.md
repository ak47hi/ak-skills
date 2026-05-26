"Our system" is too broad to pick a diagram from — type, participants, and scope are all unpinned. A few quick questions and I'll generate it:

**1. Which diagram fits best?**
   1. **C4 Container** — the architecture map (web app, API, DB, external systems)
   2. **Sequence** — message flow for one specific scenario (e.g. login, checkout)
   3. **ER** — data model and entity relationships

   (Or describe what you want to communicate and I'll pick. Other options exist — component, state, activity, deployment, use case, pipeline — but the three above cover most "draw our system" asks.)

**2. Who's in it?**
   Name the participants — e.g. "Browser, API (Go), Postgres, Stripe (external)". If you'd rather I read from a repo or doc, point me at it.

**3. Which slice?**
   "The whole system" is usually too much for one diagram. A subsystem, a single critical flow, or the public boundary works better. Suggest a starting scope or I'll propose one once I know what the system does.

If you want to skip the questions: paste a one-paragraph description of what the system does and who talks to it, and I'll propose-and-go with a C4 Container diagram as the default.
