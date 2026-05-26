# Type mismatch — sequence diagram is wrong for this

A sequence diagram shows **messages exchanged over time between participants** (lifelines, calls, returns). A database schema is **static structure** — tables, columns, foreign keys, cardinality. There is no time axis and nothing is sending messages.

If I emitted a sequence diagram here it would either be invalid (no way to attach columns to a lifeline, no way to express FK cardinality with `->` arrows) or it would silently misrepresent the schema as a sequence of calls between tables, which is meaningless.

## What you almost certainly want: an **ER diagram (ERD)**

ERDs are the canonical PlantUML output for "tables, columns, foreign keys":

- `entity` per table
- `*column : type` for required columns, `column : type` for nullable
- `<<PK>>` / `<<FK>>` stereotypes on key columns
- Crow's-foot cardinality on the relation lines (`||--o{`, `}o--o{`, etc.)

Confirm and I'll generate it. To produce a useful ERD I need either:

1. The table list with columns + types + which columns are PK/FK + which table each FK points to, **or**
2. A `CREATE TABLE` SQL dump (or schema file path) I can read and translate.

## Other things "diagram of our database" sometimes means — say so if one of these fits instead

- **Class diagram** — if you want methods / behavior attached to entities (ORM models, domain objects). Reference: `references/12-class.md`.
- **Deployment diagram** — if you actually meant "where the databases run" (primary / replicas / shards across nodes), not the schema. Reference: `references/15-deployment.md`.
- **Sequence diagram (legitimately)** — if you want the *queries* against the schema over time (e.g. "checkout flow: which tables get hit in what order"). That's a flow, not a schema, and would name tables as participants but would not show columns or FKs.

No `.puml` written — waiting on your call between ERD (default) or one of the alternatives above, plus the schema input.
