# Datastores

Load when entering **Phase 3 (Data & storage)**. Goal: derive the data model from access patterns (the functional core from Phase 1), then pick stores **per operation**, not per system. Default to relational. Treat each additional store as a cost that needs justification.

## The "relational until it hurts" default

Start with Postgres (or MySQL). Reach for anything else only when a specific access pattern provably doesn't fit. Reasons:

- A modern relational DB on a single instance handles tens of thousands of QPS on a warm cache (see `estimation.md`'s single-machine baseline). The throughput ceiling is usually higher than the team's first guess.
- ACID, schema, foreign keys, JOINs, and SQL's expressiveness are real engineering leverage. Replacing them with NoSQL is replacing a familiar set of tradeoffs with an unfamiliar set.
- Operational maturity matters more than benchmark wins. Most teams know how to back up, monitor, restore, tune, and on-call Postgres. They don't know how to do those for Cassandra or DynamoDB until they've been paged a few times.
- Postgres has extensions for most "we need a different DB for this" needs: JSONB (document-ish), pg_trgm (fuzzy search), PostGIS (geo), TimescaleDB (time-series), pgvector (embeddings). Adopting an extension is cheaper than adopting a new datastore.

**When does relational hurt enough to switch?**

- Write throughput exceeds what a single primary can sustain even after vertical scaling, partitioning the table, and using async replicas for reads.
- The natural access pattern is genuinely keyed (single-key reads, no joins) at a scale where the relational overhead is wasted.
- The data shape is graph-shaped and the queries are deep traversals.
- Full-text search becomes the dominant query and `pg_trgm` / `tsvector` aren't enough.

Until one of those is empirically true, Postgres is the answer.

## Selection matrix by family

For each family: when to reach for it, what it's bad at, common misuses.

### Relational (Postgres, MySQL, SQLite)

- **Reach for:** transactional state, anything with foreign keys, anything that ever asks "show me X where Y joined Z." Default choice.
- **Bad at:** write-heavy workloads at >100k sustained QPS without sharding; geo-replication with strong consistency; graph traversals more than 2–3 hops; full-text search at scale.
- **Common misuse:** using a key-value pattern (`SELECT * FROM kv WHERE key = ?`) and complaining Postgres is "too heavy." If the access pattern is genuinely just KV, fine, but most teams that think they have a KV pattern actually have a relational one with one table.

### Key-value (Redis, DynamoDB, Memcached)

- **Reach for:** caches (Redis/Memcached); session stores; rate-limit counters; deduplication keys; a primary store **only** when the access pattern is genuinely "give me this one row by this exact key, at scale, no secondary queries."
- **Bad at:** anything requiring secondary indexes, range scans, joins, transactions across keys. DynamoDB's GSIs paper over this at significant cost.
- **Common misuse:** Redis as a primary database. Redis is RAM-resident and AOF/RDB durability has gotchas; it shines as a cache, not a system of record.

### Document (MongoDB, Couchbase, Postgres JSONB)

- **Reach for:** schema-flexible domains where each entity is genuinely standalone (product catalogs with vendor-specific attributes; CMS content; user-uploaded structured documents). When the entity *is* the JSON.
- **Bad at:** anything that joins. "MongoDB doesn't do joins" isn't a marketing line; it's a real limit. Once you start denormalizing because you can't join, you're doing the database's work in application code, and your data is now denormalized — which means it can diverge.
- **Common misuse:** picking MongoDB because "schemas are restrictive" early in a project, then six months in writing application-layer validators because turns out you wanted a schema. Postgres JSONB gives you 80% of the flexibility with all the relational machinery still available.

### Wide-column (Cassandra, ScyllaDB, HBase, BigTable)

- **Reach for:** very high write throughput with linear scalability requirement; time-series-like data where you read by a partition key and a range; multi-DC deployments with eventual consistency.
- **Bad at:** ad-hoc queries (you design the schema for one access pattern; new access pattern = new table or full scan); transactional updates across partitions; small/medium-scale data where Postgres would work and the team doesn't have Cassandra operational experience.
- **Common misuse:** adopting Cassandra at small scale "for future-proofing." Operationally it's much more expensive than Postgres; the future you're proofing against may never arrive.

### Graph (Neo4j, JanusGraph, ArangoDB)

- **Reach for:** dominant queries are deep traversals (friends-of-friends, recommendation paths, fraud rings). When the depth makes recursive CTEs in SQL painful.
- **Bad at:** general-purpose OLTP; reads keyed by ID at scale (it's a real DB, but a specialized one).
- **Common misuse:** modeling things as a graph because the *domain* mentions "relationships," not because the *queries* are graph-shaped. A user-has-many-posts schema is not a graph problem.

### Search (Elasticsearch, OpenSearch, Algolia, Postgres tsvector/pg_trgm)

- **Reach for:** full-text search, faceted filters at scale, fuzzy matching, ranking. As a secondary index, not as a system of record.
- **Bad at:** being a source of truth (no transactional guarantees on indexing); strongly consistent reads (refresh interval is real); operational simplicity (Elasticsearch is its own pager rotation).
- **Common misuse:** writing primary data to Elasticsearch. It's an index. The source of truth lives in Postgres or similar; ES is rebuilt from there.

### Time-series (TimescaleDB, InfluxDB, Prometheus, M3, ClickHouse)

- **Reach for:** append-mostly timestamped data with time-range queries, downsampling, retention policies, high ingest rates. Observability metrics. IoT telemetry.
- **Bad at:** updates to historical data; relational joins with non-timeseries entities; small-scale data where Postgres + an index on `created_at` does fine.
- **Common misuse:** adopting a TSDB for low-volume operational logs that could live in Postgres with a partitioned table.

### OLAP / columnar (ClickHouse, Snowflake, BigQuery, DuckDB)

- **Reach for:** analytical queries over large tables, full scans, aggregations. Separate from OLTP.
- **Bad at:** point reads, transactional updates, low-latency individual-row access.
- **Common misuse:** running BI dashboards directly against the OLTP Postgres. Read replicas help for a while; eventually you need a separate analytical store.

## Consistency models — per operation, not per system

Consistency is chosen *per operation*, not as a global property of the system. The same database can serve linearizable reads for payments and eventual reads for trending-now.

From strongest to weakest:

1. **Linearizable.** Reads see the latest committed write, globally. Hard to scale; expensive coordination. Use for: financial state, inventory decrement, "is this username taken."
2. **Sequential.** All clients see writes in the same order, but not necessarily the latest. Less expensive than linearizable.
3. **Causal.** If write A caused write B, all clients see them in that order. Sufficient for "comments under my comment appear in order."
4. **Read-your-writes.** After you write, *you* always see your write (others might not for a moment). Sufficient for "I posted a tweet, I see it in my feed."
5. **Monotonic reads.** Subsequent reads from the same client never go backwards in time. Prevents the "I refreshed and the post disappeared, refreshed again and it came back" experience.
6. **Eventual.** Given no further writes, all replicas converge. Acceptable for: feeds, counters, trending lists, view counts.

**The discipline:** for each dominant operation in the Phase 1 functional core, name the weakest consistency level that's still correct for the user. Stronger consistency than required is wasted latency and availability.

## CAP, said practically

The standard CAP framing — "pick 2 of Consistency, Availability, Partition tolerance" — is famously confusing. The useful framing:

- Network partitions happen. You don't get to choose P.
- During a partition, you pick C or A: either refuse writes (preserve consistency) or accept writes (preserve availability) and reconcile later.
- Outside partitions, CAP says nothing useful.

The interesting question is **PACELC**: during a Partition, pick A or C — Else (no partition), pick Latency or Consistency. PACELC captures the everyday tradeoff: even when nothing is broken, stronger consistency costs latency (synchronous replication, quorum reads).

This is why most real systems are PA/EL (eventual, low latency) or PC/EC (strong, higher latency) — not the corners.

## Replication patterns

### Single-leader (Postgres streaming replication, MySQL primary-replica)

- **Writes:** all go to leader.
- **Reads:** can go to leader (strong) or followers (eventually consistent, may be stale).
- **Failover:** elect a new leader. Real cost: split-brain risk, replica promotion lag, read-your-writes breakage if app reads from a different replica than where it just wrote.
- **Default for most systems.** Mature tooling, well-understood failure modes.

### Multi-leader (CRDTs, multi-master Postgres, Cassandra multi-DC)

- Multiple leaders, each accepts writes, replicate to peers.
- **Useful for:** active-active geo deployments where local writes need local latency.
- **Hazard:** conflict resolution. Two writes to the same key in different leaders — what wins? Last-write-wins is data loss in disguise; CRDTs require schema design for mergeability; per-entity ownership avoids conflicts but requires routing.

### Leaderless quorum (Cassandra, DynamoDB, Riak)

- N replicas. Write to W replicas, read from R replicas. If `W + R > N`, you're guaranteed at least one replica with the latest write.
- **Useful for:** high availability with tunable consistency per operation.
- **Hazard:** read repair, hinted handoff, anti-entropy — the system spends real CPU keeping replicas in sync, and there are subtle bugs.

## Replication-lag bugs (read every design for these)

- **Read-your-writes.** User writes to leader, immediately reads from replica that hasn't caught up — sees stale data. Mitigate: route the user's reads to leader for N seconds after their write, or sticky-route them.
- **Monotonic reads.** User reads from replica A (fresh), then from replica B (stale), sees data move backward. Mitigate: pin a session to one replica.
- **Causal violations.** B references A, but A's replica hasn't arrived at B's replica yet. Mitigate: bundle causally related writes, or use a system that tracks causality (vector clocks).

These bugs are not "could happen" — they happen in any leader-follower system during lag spikes.

## Partitioning (sharding)

Three strategies:

### Hash partitioning

- Hash the partition key, mod by shard count. Even distribution by design.
- **Hazard:** range scans are gone (you'd have to query every shard). Resharding is painful (changing the modulus moves every key).
- **Mitigate range scans:** secondary indexes, or accept that range queries hit every shard.
- **Mitigate resharding pain:** **consistent hashing** (only a fraction of keys move when shards are added/removed) — used by Cassandra, DynamoDB, distributed caches.

### Range partitioning

- Each shard owns a range of keys (A–F, G–M, ...).
- **Hazard:** monotonically increasing keys (timestamps, auto-incremented IDs) create a hot tail — all writes go to the latest range's shard. Mitigate by hashing a prefix into the key.

### Directory-based

- Explicit mapping: this key lives on this shard. The most flexible, the most operational overhead.
- **Useful when:** the data has natural tenants (per-customer sharding) and tenants have very different sizes.

### Shard-key hazards (universal)

- **Hotspots.** A celebrity user, a viral post, a Black-Friday SKU. One shard takes 100× the traffic of others. Mitigate: secondary sharding within the hot partition (e.g., shard by `(user_id, hash(post_id) % 16)` for the celebrity case).
- **Cross-shard transactions.** Almost always need a two-phase commit or a saga. Avoid by choosing a shard key that keeps related entities together (shard by `customer_id`, not by `order_id`).
- **Rebalancing.** Adding shards costs real downtime or real complexity. Plan capacity 2–3× ahead of need, or use consistent hashing.

## Polyglot persistence as a cost

Adding a second store is not free. Each store is:

- A new failure mode (it can be down independently).
- A new consistency boundary (data written to one isn't visible in the other immediately).
- A new operational pager (backups, monitoring, version upgrades).
- A new place for bugs (the dual-write problem: you wrote to Postgres but not to ES, now your search index is stale forever).

**Count consistency boundaries.** Each additional store is one more. A system with Postgres + Redis + Elasticsearch has 3 stores and 3 pairwise consistency boundaries (PG↔Redis, PG↔ES, Redis↔ES). Each boundary is a class of bugs.

**The dual-write problem** is the canonical hazard. Solutions:

- **Outbox pattern:** write to Postgres in the same transaction as a row in an `outbox` table; a separate process reads `outbox` and publishes to the other store. Single source of truth (Postgres); eventually consistent everywhere else.
- **CDC (Debezium, Postgres logical replication):** stream Postgres's WAL into Kafka, then to ES/cache. Same idea, different mechanism.
- **Synchronous dual-write:** application writes to both stores in sequence. **Don't do this.** One of them will eventually fail and you'll have permanent divergence.

If a design adopts a second store, the answer to "how do you keep them in sync" must be a real mechanism (outbox or CDC), not "we'll just write to both."

## Selection checklist (Phase 3 gate)

Walk this before choosing a store:

1. What are the 2–3 dominant access patterns? (Not "all queries" — the *dominant* ones.)
2. What's the read:write ratio per access pattern?
3. What consistency does each access pattern require (linearizable / read-your-writes / eventual / etc.)?
4. What's the data shape per pattern (single row by key / range scan / join / full text / aggregation / graph traversal)?
5. What's the scale per pattern at 12 months (rows, QPS, payload size)?
6. Does Postgres handle this with the right indexes? (If yes, stop here.)
7. If not, which family from the matrix above fits the binding constraint?
8. Does the team have operational experience with the candidate? If not, what's the cost of acquiring it?
9. If polyglot: what's the sync mechanism? (Outbox, CDC, or "we don't and we accept divergence.")
10. How many consistency boundaries does the final design have? (Each is a class of bugs.)

If question 6 is "yes" and you proposed something other than Postgres, go back.
