# Multi-tenant SaaS

Load when the prompt describes a system serving multiple customers/accounts/tenants on shared infrastructure: B2B SaaS, white-label platforms, per-customer SLAs, "our enterprise tier," "noisy neighbor," "tenant isolation."

The defining concern: **fairness and isolation between tenants with different sizes, importance, and behavior patterns.**

## When this archetype fires

Signal cues:
- "B2B SaaS" / "per-customer" / "per-tenant" / "our customers"
- "Enterprise tier" / "free tier" / "different SLAs by plan"
- "Noisy neighbor" / "one customer is affecting others"
- "Tenant isolation" / "data isolation" / "compute isolation"
- "GDPR delete per customer" / "tenant data export"
- "Per-customer customization" / "feature flags by account"

Non-signals (looks similar but isn't):
- A consumer product with millions of individual users — that's read-heavy mobile or write-heavy, not multi-tenant.
- An internal admin tool used by one organization — single-tenant.
- A multi-region deployment — that's geo-distributed; multi-tenant is about customer-level isolation, not geographic.

## Additional elicitation (beyond the universal seven)

1. **Tenant count and size distribution.** Are there 50 enterprise customers of similar size, or 50,000 customers with a long tail (one customer is 1000× the median)? The distribution shape decides the architecture.
2. **Per-tenant SLAs.** Does the enterprise tier get a stronger SLO? A dedicated environment? Faster support? Different rate limits? The SLA differentiation drives compute/data isolation choices.
3. **Tenant-level operations.** What operations exist per tenant: data export (GDPR), data deletion (GDPR), backup/restore (per-customer), tenant migration (move between shards/regions), tenant suspension? Each is a real workflow to design.
4. **Cost attribution.** Does the business need to know cost-per-tenant (for pricing decisions, profit analysis, internal chargeback)? If yes, tagging and metering are first-class concerns.
5. **Onboarding/offboarding.** What does provisioning a new tenant look like (instant via self-service, or sales-driven over days)? What does deprovisioning look like (immediate, or 30-day soft-delete)?
6. **Data sovereignty / residency.** Do some tenants require their data in specific regions for compliance (EU, US, AU)? This collides with geo-distributed concerns; resolve early.
7. **Customization scope.** Per-tenant features? Per-tenant branding? Per-tenant schema extensions? Per-tenant business logic? Each is a different cost.

## Recurring failure modes

### Noisy neighbor

**Symptom.** One tenant's heavy workload (a runaway query, a sudden spike, a batch job) degrades performance for all other tenants on shared infra.

**Why it happens.** Shared resources (DB connections, CPU, network bandwidth) have no per-tenant fairness mechanism. The hot tenant takes 100% of capacity until throttled.

**Mitigation.** Per-tenant resource budgets (rate limits, connection-pool quotas, query timeouts), separate queues per tenant for async work, bulkheads at the service level. For severe cases, dedicated infrastructure for the affected tier.

### Hot tenant

**Symptom.** One customer is 10×–100× the median in QPS, data size, or both. Their writes dominate write QPS; their data dominates the table size and cache.

**Why it happens.** Long-tail customer distributions are normal. The product can't refuse the customer; the architecture has to absorb them.

**Mitigation.** Tenant-aware sharding (the hot tenant on its own shard); dedicated capacity for top-N tenants; secondary sharding within a hot tenant's data (shard their orders by `hash(order_id)` rather than concentrating).

### Cross-tenant data leakage

**Symptom.** A bug returns one tenant's data to another tenant. Usually a missing `WHERE tenant_id = ?` clause; sometimes a cache poisoned by a missing tenant in the cache key.

**Why it happens.** Tenant isolation lives in application code. Every query, every cache key, every response, every log line must scope to the current tenant. One missed scope is a breach.

**Mitigation.** Tenant context is automatic at the framework level — request scope carries tenant_id; ORM enforces it; cache keys always include it; tests assert it. Defense in depth: schema-per-tenant or DB-per-tenant for highest-isolation tiers.

### Onboarding race conditions

**Symptom.** A new tenant signs up, the provisioning workflow is partially complete, the user starts using the product, hits inconsistent state.

**Why it happens.** Tenant provisioning is rarely a single transaction (create DB schema, seed default config, create admin user, send welcome email, register in usage-tracking, register in billing). Partial failure = inconsistent tenant.

**Mitigation.** Idempotent provisioning workflow; "tenant ready" flag the rest of the system checks; reconciliation job for stuck tenants; explicit rollback for failed provisioning.

### Cost attribution drift

**Symptom.** Finance asks "how much does customer X cost us to serve?" and no one knows.

**Why it happens.** Shared infrastructure means costs aren't naturally split by tenant. Without tagging at every layer, the answer is "we don't know" — which makes pricing decisions guesswork.

**Mitigation.** Tag every resource with tenant_id (cloud provider tags, internal metering, log lines). Aggregate costs per tenant in a regular report. Higher fidelity matters more as tenant size variance grows.

## What god-tier designers always ask

1. **Schema-per-tenant vs shared schema with `tenant_id` column?** Shared is cheapest operationally; schema-per-tenant gives stronger isolation but multiplies migrations by tenant count; DB-per-tenant is strongest isolation but operationally expensive.
2. **Pool vs silo for compute?** Pool (shared compute, all tenants on the same servers) is cheap; silo (dedicated compute per tenant) is isolated but expensive. The right answer is usually **pool by default, silo for the top tier**.
3. **What does the largest tenant look like in 12 months?** Long-tail distributions skew. If today's largest tenant is 10% of total traffic and growing 30%/year, plan for the moment they're 30%.
4. **How do you isolate a misbehaving tenant?** Without a kill switch, a runaway tenant takes down the platform. Per-tenant rate limits + circuit breakers + a tenant-suspension control are non-optional.
5. **Tenant data export / deletion — how fast?** GDPR's "right to erasure" has a 30-day window. If you can't enumerate where a tenant's data lives, deletion is a multi-quarter project.
6. **Tenant migration — possible?** Moving a tenant from one shard to another, from one region to another, from one tier to another. If never possible, you've locked tenants into their initial placement forever.
7. **Per-tenant config — where?** A per-tenant feature flag is a different system from per-tenant pricing rules is different from per-tenant branding assets. Don't conflate.
8. **What runs as background work per tenant?** Daily aggregations, weekly reports, periodic syncs — these scale with tenant count and can starve foreground requests if not isolated.

## Common pitfalls

### "We'll add multi-tenancy later"

Retrofitting multi-tenancy into a single-tenant system is a multi-quarter project. Every query gets a new clause, every cache key gets a new component, every test fixture gets new setup, every endpoint gets new authorization. If multi-tenancy is even possibly in the future, design for it now — at minimum, every internal API takes a tenant context object.

### Tenant ID derived from request data, not request identity

If your tenant_id comes from a query parameter or a request body field, you have an authorization bug waiting. The tenant context must come from the **authenticated identity** (JWT claim, session, API key → tenant mapping), not the request body.

### Per-tenant rate limiting that doesn't coordinate

Per-tenant rate limits enforced at each app instance independently means one tenant can use N×instances of capacity. Use a centralized rate limiter (Redis-backed) or shard requests by tenant for consistent enforcement.

### Shared connection pool across tenants without bulkhead

One tenant's slow queries hold all the connections. Bulkhead: separate connection pool per tenant tier (enterprise vs free), or per-tenant budgets within a shared pool.

### Forgetting tenant_id in cache keys

The classic cross-tenant bug. `cache.get(f"user:{user_id}")` works fine until two tenants have the same user_id (shouldn't happen but does — auto-incremented integers reused after deletion, UUIDs colliding under bad assumptions). Always: `cache.get(f"tenant:{tenant_id}:user:{user_id}")`.

### Per-tenant features stored as per-tenant code branches

If "tenant X gets feature Y" is implemented by an `if tenant.id == 'acme'` somewhere in the code, you've lost. Use per-tenant feature flags backed by a configuration store, not code.

## Anchor numbers

These are rough thresholds. The exact numbers depend on workload shape.

- **Pooled architecture (shared compute and shared DB)** is feasible up to **~10k–50k tenants** depending on per-tenant load.
- **Schema-per-tenant on shared Postgres** starts hurting around **~1000–5000 schemas per instance** (migrations get slow, catalog bloats).
- **DB-per-tenant** is typically used for top-tier enterprise customers (tens to hundreds of customers) where isolation justifies the cost, or for compliance-driven separation.
- **Tenant size distribution**: in practice the top 1% of tenants often drive 30–50% of load. Plan capacity around the top 10% of tenants, not the average.
- **Onboarding latency**: self-service tenants expect < 1 minute to "ready." Enterprise sales-driven tenants are fine with hours of manual provisioning.

## Cross-archetype interactions

- **Multi-tenant + geo-distributed**: data residency constraints (EU customers' data must stay in EU) collide with multi-region replication. Resolve by mapping tenants to home regions and replicating only within each tenant's region.
- **Multi-tenant + write-heavy**: per-tenant shards usually work well — tenants are natural shard boundaries with bounded growth.
- **Multi-tenant + observability**: tenant_id should be a dimension on every metric, log, and trace. Beware cardinality blowup if tenant count is large; aggregate to "top-N tenants + everyone else" for dashboards.
