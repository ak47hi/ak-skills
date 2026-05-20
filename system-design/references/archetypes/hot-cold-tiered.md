# Hot-cold tiered storage

Load when the prompt describes data lifecycle: hot/warm/cold tiers, archival, S3 Glacier, "data we rarely read but must keep," compliance retention, "we keep everything forever and storage is exploding."

The defining concern: **moving data through tiers (hot → warm → cold → archive) as it ages, balancing access latency, storage cost, and compliance requirements, while keeping deletion (GDPR) workable even on cold data.**

## When this archetype fires

Signal cues:
- "Hot tier" / "warm tier" / "cold tier" / "tiered storage"
- "Data lifecycle" / "lifecycle policy" / "archival"
- "S3 Glacier" / "Glacier Deep Archive" / "cold storage"
- "Compliance retention" / "7-year retention" / "regulatory archive"
- "GDPR delete" + "but the data is in cold storage"
- "Long retention" / "data we rarely access"
- "Storage cost is exploding" / "we keep too much"

Non-signals:
- A small system where everything fits in one storage tier — universal foundation handles it.
- Backup / disaster recovery — that's geo-distributed or operational, not data lifecycle.
- A caching tier in front of a database — that's `read-heavy-mobile` or general caching.

## Additional elicitation (beyond the universal seven)

1. **Tier definitions.** What does "hot" mean (sub-second queries, recent data)? Warm (seconds, analytical access)? Cold (minutes to retrieve, rare access)? Archive (hours to retrieve, compliance only)? The latency target per tier IS the design.
2. **Access pattern by data age.** What fraction of queries hit data from the last 24 hours? Last week? Last month? Year+? Tier transitions follow the access distribution.
3. **Lifecycle automation.** Auto-transition by age (move to cold after 90 days)? By access pattern (last accessed > 90 days ago)? Manual / batch-driven? Auto is cheapest but can move data while still being queried.
4. **Restore SLA from cold/archive.** How fast must cold data be available when needed? Glacier is hours; Glacier Instant is immediate but more expensive. Defines retrieval architecture.
5. **GDPR / deletion requirements.** Can a user's data be deleted from all tiers within the regulatory window (30 days for GDPR)? If cold-tier retrieval is hours, deletion is also hours of restore-rewrite-delete.
6. **Compliance retention floors.** Some data has minimum retention (financial records: 7+ years; HIPAA: 6 years; etc.). The minimum retention conflicts with cost optimization; resolve explicitly per data class.
7. **Cost per tier.** Hot DB: $100–1000/TB-month. S3 Standard: $23/TB-month. Glacier: $4/TB-month. Glacier Deep Archive: $1/TB-month. Plus per-retrieval costs that can dwarf storage savings if accessed frequently.
8. **Query routing across tiers.** Can the query interface read across tiers transparently (with expected latency per tier)? Or are separate tools for each (BigQuery for warm, Athena over S3 for cold)?

## Recurring failure modes

### Cold-tier retrieval cost surprise

**Symptom.** A query against archived data returns the right answer at a $10,000 retrieval cost. Or worse: a runaway script queries cold data repeatedly, costing tens of thousands per day before someone notices.

**Why it happens.** Cold-tier per-retrieval pricing is high ($/GB retrieved). Queries that scan large amounts of cold data are very expensive.

**Mitigation.** Per-user / per-team cold-tier query quotas. Pre-approval for large cold queries. Cost monitoring with alerts at unusual usage. Surface the cost estimate before query execution.

### GDPR deletion can't reach cold storage in time

**Symptom.** User requests data deletion. Hot and warm storage delete within hours. Cold storage requires retrieve-rewrite-delete cycle, takes weeks, breaches the 30-day GDPR window.

**Why it happens.** Cold storage was designed for "keep forever, cheap to store" without considering "delete on request."

**Mitigation.** Cold tier organized for deletability: per-user partitions on the cold side, deletable independently. Or: encrypt per-user data with per-user keys; deleting the key effectively deletes the data (crypto-shredding) even from immutable storage.

### Lifecycle moves data while it's being queried

**Symptom.** A lifecycle policy moves data from warm to cold at 90 days. A long-running batch job (started day 89) is reading the data. The move breaks the job mid-execution.

**Why it happens.** Lifecycle automation has no awareness of in-progress queries.

**Mitigation.** Lifecycle transitions in maintenance windows. Grace period before transition. Pause lifecycle for actively-queried partitions.

### Compliance retention vs cost optimization conflict

**Symptom.** Finance wants 7-year retention for tax records. Engineering wants 30-day retention to save cost. Without an explicit policy, one or the other is wrong.

**Why it happens.** Different teams own different stakes; no agreed policy.

**Mitigation.** Per-data-class retention policy, documented and enforced. Tag data at write time with its retention class. Lifecycle policies query the tag. Audit annually.

### Lifecycle policy drift

**Symptom.** Lifecycle rules in production don't match what people think they are. Data they expect to find is gone; data they expect to be deleted is still there.

**Why it happens.** Lifecycle rules edited piecewise over years without audit. The actual rules are documented somewhere but no one reads them.

**Mitigation.** Lifecycle rules in version-controlled config; reviewed in PRs; audited quarterly; query interfaces show "retention class for this data" alongside the data.

### Tier confusion at query time

**Symptom.** Engineer queries "events from last year." The hot store doesn't have them. Query returns empty / no-error. Engineer concludes "no events," makes wrong decision.

**Why it happens.** Query interface doesn't surface which tier holds the data or that data exists in another tier.

**Mitigation.** Unified query interface that reads across tiers (with documented latency expectations). Or: explicit "this query covers data from N days, oldest in cold tier" indicators.

### Restore-from-archive failed test

**Symptom.** Compliance auditor asks for 2018 records. The team tries to restore from Glacier Deep Archive. Restore fails / takes weeks / costs more than expected. Audit deadline missed.

**Why it happens.** Archive restore was never tested.

**Mitigation.** Quarterly restore tests of a sample from each archive class. Document the procedure, the latency, and the cost.

## What god-tier designers always ask

1. **Per-tier latency budget.** What does "hot" mean specifically? "Cold"? Without latency targets, tiering is fuzzy.
2. **Access pattern by data age.** The decision to tier (and when) follows the access distribution. Measure it.
3. **Lifecycle automation rules + when do they run?** Automated, in maintenance windows, with grace periods.
4. **Deletion guarantees with retention.** GDPR delete vs compliance retain — these CAN conflict. Resolve per data class.
5. **Restore SLA from each tier + tested when?** Quarterly restore tests are cheap insurance.
6. **Cost per tier per GB-month + per-retrieval.** Storage cost is one variable; retrieval cost is the other and frequently surprises.
7. **Query interface — transparent across tiers, or one tool per tier?**
8. **Crypto-shredding feasible?** Per-user encryption keys make deletion effectively-immediate even on immutable storage.
9. **Tier transitions in dev/test, not just prod.** Lifecycle rules tested only in dev rot in prod.

## Common pitfalls

### Everything in hot tier forever

The opposite of this archetype: no tiering. Hot storage is 10–100× more expensive than cold; keeping rarely-accessed data hot is pure cost.

### Cold-tier compute

Running queries (SELECT) against deeply cold storage. Often each query restores the data first (hours), then runs. Per-query cost in dollars. Cold storage is for retain-not-query.

### Lifecycle rules tested only in dev

In dev, the system has a few GB of recent data; lifecycle does nothing visible. In prod, lifecycle policies transition petabytes; subtle bugs surface.

### Forgetting GDPR delete on cold storage

The compliance officer asks "can we delete a user's data within 30 days?" The answer is "yes" for hot/warm and "we hadn't thought about cold." Audit finding follows.

### No retention tagging at write time

Data is written without metadata about its retention class. Years later, lifecycle policies have to guess. Guessing produces wrong outcomes (keeping things too long, deleting things too soon).

### Compliance retention as engineering's job to figure out

Engineering doesn't have legal context for retention requirements. Legal/finance defines the floors; engineering enforces them. Without this split, retention is over-conservative ("keep everything forever") or under-conservative ("delete to save cost") — both expensive.

### Treating archive as deletion

Archive ≠ delete. Archive is "in cold storage, hard to query, still exists." For data that should really be gone, delete; for data that must be retained but rarely accessed, archive. Conflating them leaves data in a "neither queryable nor deleted" limbo.

## Anchor numbers (AWS pricing examples; concept applies to other clouds)

Pricing changes; treat these as relative magnitudes.

- **Hot database (RDS, Aurora)**: typically **$100–1000/TB-month** depending on instance type and IOPS.
- **S3 Standard**: ~**$23/TB-month**, immediate access, fast retrieval, no retrieval fees beyond bandwidth.
- **S3 Standard-IA (Infrequent Access)**: ~**$12/TB-month**, immediate access, **$10/TB retrieval**.
- **S3 Glacier Instant Retrieval**: ~**$4/TB-month**, immediate access, **$30/TB retrieval**.
- **S3 Glacier Flexible Retrieval**: ~**$3.6/TB-month**, **minutes to 12 hours** retrieval, **$10/TB retrieval**.
- **S3 Glacier Deep Archive**: ~**$1/TB-month**, **12+ hours retrieval**, **$20/TB retrieval**.
- **Cold-tier query cost**: a single ad-hoc query that scans 100 TB of Glacier Flexible costs ~**$1000** in retrieval alone.

**Storage cost ratio**: cold archive is roughly **20× cheaper** than hot DB; the savings can dwarf the engineering cost of tiering for any system with significant rarely-accessed data.

**Access decay typical**: in many systems, **80% of queries hit data < 30 days old**; **15%** hit 30 days – 1 year; **5%** older. Tier accordingly.

## Cross-archetype interactions

- **Hot-cold-tiered + multi-tenant**: per-tenant tier policies (enterprise gets longer hot retention; free tier ages faster); per-tenant retention rules where GDPR / sovereignty differ.
- **Hot-cold-tiered + write-heavy**: write-heavy data ages fast; tiering is mandatory at scale. Hot for ingest + recent reads; warm for analytical; cold for compliance / rare investigation.
- **Hot-cold-tiered + observability**: observability data has natural tier shape. Metrics: hot 30 days, warm 1 year. Logs: hot 14 days, warm 30, cold for compliance. Traces: hot 7 days, warm 30, rarely worth archiving.
- **Hot-cold-tiered + batch ETL**: ETL pipelines often shuffle data across tiers (hot→cold for old data; cold→hot for retrieval). Pipeline IS the lifecycle mechanism.
