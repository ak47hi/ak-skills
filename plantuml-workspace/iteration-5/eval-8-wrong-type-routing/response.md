A sequence diagram shows messages exchanged between participants over time — it can't represent tables, columns, or foreign keys. For a database schema (tables + columns + FKs with cardinality), the right type is an **ER diagram**.

Want me to generate that instead? If yes, paste the schema (table names, columns with types/PK/FK markers, and the FK → referenced-table relationships) and I'll produce an ER diagram with crow's-foot cardinality.

If you genuinely want a sequence diagram of something schema-adjacent — e.g. the flow of a query/transaction across tables, or an ORM's read/write path — tell me the participants (caller, ORM, DB, specific tables) and the scenario, and I'll route to sequence instead.
