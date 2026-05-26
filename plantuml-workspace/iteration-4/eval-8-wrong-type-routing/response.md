A sequence diagram is the wrong fit here — sequence diagrams show message exchange over time between participants, but a database schema (tables, columns, foreign keys) is static structure with cardinality. The right type is an **ER diagram** (`entity` blocks with `*` for required columns, `<<PK>>` / `<<FK>>` stereotypes, and crow's-foot relations for cardinality). A class diagram is a reasonable second choice if you also want to model behavior alongside the data, but for pure schema-with-FKs, ER is the canonical mapping.

To generate it, I need the schema. Either:

1. Paste the `CREATE TABLE` statements (or a DBML / Prisma / SQLAlchemy / Django / `information_schema` dump), or
2. List the tables and, for each, the columns (with PK markers) and the FK targets (e.g. `orders.customer_id -> customers.id, many-to-one`).

Once I have that, I'll produce a single named ER `.puml` with crow's-foot cardinality on every relation and `<<PK>>` / `<<FK>>` stereotypes on the relevant columns.

If you genuinely want a sequence diagram of something schema-adjacent — e.g. the message flow of a specific query path, a migration rollout, or a replication handshake — tell me which interaction and I'll route to sequence instead. But "tables, columns, foreign keys" by itself is ER.

No diagram produced this turn (would be a routing error to emit a sequence diagram of static structure).
