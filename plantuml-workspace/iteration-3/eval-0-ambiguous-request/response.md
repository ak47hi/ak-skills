"Our system" is too broad to draw as one diagram — type, participants, and scope are all unspecified. Three quick questions so the diagram lands on what you actually want to communicate:

1. **Which diagram fits best?** The three most common for "our system":
   1. **C4 Container** — architecture map: web apps, services, datastores, external systems
   2. **Sequence** — message flow for one specific scenario (e.g. login, checkout)
   3. **ER** — data model and entity cardinality

   (Or describe what you want to communicate and I'll pick.)

2. **Who's in it?** Name the participants / components / entities — e.g. "Browser, API (Go), Postgres, Stripe (external)".

3. **Which slice?** A single flow / a subsystem / a public boundary. "The whole system" is usually too much for one diagram — pick a starting scope and we can add more diagrams from there.

Default styling is monochrome (`!theme plain`). If you want the Confluence-friendly colored preset instead, say so.
