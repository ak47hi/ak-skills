A sequence diagram is the wrong type here: it models messages exchanged over time between participants, not static structure. Tables, columns, and foreign keys are a static data model — that routes to an **ER diagram** (entity-relationship, with crow's-foot cardinality on the FK edges).

If you want a sequence diagram instead, it would need to be of *something happening against* the schema (e.g. "the read path for an order lookup", "the write path for a checkout"), with services / DB as participants — not the schema itself.

To produce the ER diagram I need the schema. Paste either:

- A `CREATE TABLE ...` DDL dump (Postgres / MySQL / SQLite all fine), or
- A table list with columns, PKs, and FK relationships (e.g. `orders.customer_id -> customers.id`).

Once I have that, I'll emit a single `schema.puml` ER diagram with `*` on PK/required columns, `<<FK>>` stereotypes on foreign keys, and crow's-foot cardinality (`}o--||`, `}|--||`, etc.) on every relation.

Adjacent options if ER isn't quite what you want:

- **Class diagram** — if you want methods / inheritance alongside fields (ORM-style models rather than raw tables).
- **C4 Component (data layer)** — if the question is really "which services touch which tables", not the schema itself.

Tell me which, and paste the schema.
