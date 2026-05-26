# Type mismatch — sequence diagram is the wrong tool for a schema

A sequence diagram models **messages exchanged over time between participants** (caller → service → DB, with ordering, activations, and returns). A database schema is **static structure** — tables, columns, foreign keys, and their cardinality. Rendering it as a sequence would force every table to become a "participant" and every FK to become a fake message, which loses the actual information (column types, PK/FK marking, 1:N vs N:M cardinality) and produces a diagram that's wrong even if it compiles.

The right type for tables + columns + foreign keys is an **ER diagram** (`entity`, `*` for required columns, `<<PK>>` / `<<FK>>` stereotypes, crow's-foot cardinality on relations). If you want a behavior-flavored view in addition — e.g. "what queries run during checkout" — that second view is the legitimate sequence diagram, but it's a separate diagram from the schema itself.

## What I need to produce the ER diagram

I don't have the schema yet. Please share one of:

1. **DDL** — `CREATE TABLE` statements (Postgres / MySQL / SQLite all fine), or
2. **A table list** — for each table: name, columns (with types), primary key, and foreign keys (which column references which table.column), or
3. **An ORM model file** — SQLAlchemy / Prisma / Django models / TypeORM entities / etc.

Also useful but optional:

- Whether you want **all** tables or a scoped subset (auth tables only, billing only, etc.) — ER diagrams get unreadable past ~15 entities, so scoping matters.
- Whether any relations are **many-to-many** through a join table (so I can render the join table explicitly vs. collapse it into an N:M edge).
- Monochrome (default, `!theme plain`) or the colored Confluence-friendly preset.

Once you paste the schema I'll route to `references/16-er.md` + `templates/er.puml`, generate the diagram, run the lint pass, and emit a single named `.puml` file plus the render command.

## If you actually wanted a sequence diagram

If the real intent is "show the order of SQL operations during \<some flow\>" (e.g. signup, checkout, password reset), say so and name the flow — that's a legitimate sequence diagram with the app server and DB as participants, and I'll generate it. But that's a different artifact from the schema.
