# Read-heavy / mobile

Load when the prompt describes high-read-volume systems with mobile clients, global users, CDN edge caching, offline-first sync, or any system where reads dominate writes by 100:1 or more.

The defining concern: **absorbing read load through aggressive caching at every layer (client, CDN, distributed cache, DB buffer pool), while handling mobile-specific constraints (intermittent connectivity, battery, slow app updates).**

## When this archetype fires

Signal cues:
- "Mobile app" / "iOS and Android" / "React Native"
- "High read traffic" / "feed" / "browse" / "discovery"
- "CDN" / "edge cache" / "Cloudflare" / "Fastly"
- "Global users" / "users worldwide"
- "Offline-first" / "works without connectivity" / "sync"
- "Read:write ratio" of 95:5 or more
- "Bandwidth-conscious" / "cellular network" / "low-bandwidth markets"

Non-signals:
- A web admin tool with low traffic — that's standard CRUD; no archetype.
- A B2B SaaS app where reads aren't dominant — `multi-tenant-saas` is the better archetype.
- A specifically write-heavy system (ingest, telemetry) — that's `write-heavy`, the opposite shape.

## Additional elicitation (beyond the universal seven)

1. **Read:write ratio.** 90:10 is "read-heavy"; 99:1 is "heavily read-skewed"; 99.9:0.1 is "almost read-only" (catalog, news feed). Different ratios justify different cache architectures.
2. **Cacheability profile.** Is the response identical across users (shared cache works) or per-user (per-user cache only)? Is the response stable for minutes, hours, days? Lifetime determines TTL.
3. **Offline tolerance.** Does the app work fully offline (offline-first)? Read-only offline (cache last-known state)? Online-only (graceful degradation)? Each is a different system.
4. **Bandwidth constraints.** Are users on 4G in mature markets (10+ Mbps) or 3G/EDGE in emerging markets (< 1 Mbps)? Response payload size matters more in the latter.
5. **Update cadence on the client.** Web app: ship a fix in minutes. Mobile app: App Store review is 1–7 days; not all users update immediately (a long tail of old versions). Server changes that require new client versions must degrade gracefully.
6. **Battery constraints.** Background sync, polling, push connections — each costs battery. Mobile users notice and uninstall.
7. **Sync conflict resolution** (offline-first only). Two devices write the same record while offline. When both come online, what wins? LWW, CRDT, per-field merge, ask the user? Document per record type.
8. **User-segmented load.** Logged-out browsing (shareable cache, anonymous, CDN-cacheable) vs logged-in personalized (per-user, less cacheable). The split is often the dominant design choice.
9. **Hot user / hot content.** Is one user's profile (a celebrity) viewed by millions? Is one piece of content viral? Hot keys appear in both.

## Recurring failure modes

### Cache invalidation lag

**Symptom.** User updates their profile. The app shows old data for 5 minutes. User refreshes — still old. Frustration.

**Why it happens.** Multiple cache layers (client app, CDN, distributed cache, DB) each with their own TTL. The update propagates slowly through them; the user's read might hit any layer's stale copy.

**Mitigation.** For writes by user X, immediately invalidate caches that user X reads. Versioned keys (`user:42:v17`) so a write bumps the version, making old keys cold and naturally evicted. Read-your-writes routing for the period after a write.

### CDN serving stale content during deploys

**Symptom.** Deploy goes live. New backend version expects new field. Old responses are still cached at CDN. Clients break.

**Why it happens.** CDN cache wasn't purged on deploy; new and old versions coexist briefly.

**Mitigation.** Versioned API paths (`/v2/feed`) so old and new responses are independently cached. Or: aggressive cache-bust on deploy. Or: backward-compatible responses (rarely fully achievable).

### Background sync battery drain

**Symptom.** Users complain the app eats battery. Investigation shows the app polls every 30s in background.

**Why it happens.** Polling was the easy implementation; the cost is paid by users.

**Mitigation.** Push notifications for fresh data; only poll when foregrounded. iOS background-fetch / Android WorkManager with reasonable intervals. Coalesce work into windows.

### Sync conflict resolution in offline-first

**Symptom.** User edits a note on phone (offline). User edits the same note on laptop (online). Phone comes online; sync happens. Phone's older edit overwrites the newer laptop edit silently.

**Why it happens.** Naive LWW based on client clock; client clock is drifted; phone's "last write" timestamp is newer than laptop's actual newer write.

**Mitigation.** CRDTs (Yjs, Automerge) for collaborative state; vector clocks; per-field versioning; manual conflict resolution (show both, let user pick) for irreconcilable cases.

### Hot user / hot content

**Symptom.** A celebrity's profile gets 100k views in the hour after a tweet. The cache node holding their profile saturates. Other users' reads degrade.

**Why it happens.** Cache distribution by key hash concentrates a single key on one node.

**Mitigation.** Replicate hot keys to multiple cache nodes (read from any). Local in-process cache layered on top of distributed cache for the very hottest keys. Specific routing for known celebrities.

### Cache stampede on cold start

**Symptom.** Cache is empty (deploy, restart). The DB takes the full load. DB saturates, requests time out, retries pile up.

**Why it happens.** No cache warming on startup; all reads go to the DB simultaneously.

**Mitigation.** Pre-warm with the top-N critical keys before serving traffic. Rolling deploy so only a fraction of cache is cold at once. Rate-limit cold-start traffic to the DB.

### Old client version compatibility

**Symptom.** Server team ships a new feature requiring a backend response shape. Some clients on old app versions (haven't updated) break.

**Why it happens.** Forced-upgrade signals are weak; the long tail of un-updated clients persists. Server can't assume all clients are current.

**Mitigation.** Backward-compatible response shapes (new fields are added; old fields kept). Per-client-version response shaping when necessary. Hard force-upgrade signal for security-critical or breaking changes (with respectful UI).

## What god-tier designers always ask

1. **What's the cacheability profile of each response type?** Per-user vs shared; minutes vs hours vs days of TTL; immediate-invalidation requirements.
2. **CDN cache hit ratio target — and current?** 90%+ for static; lower (sometimes far lower) for dynamic. Measure first; tune second.
3. **Offline behavior expectation: full offline, read-only offline, or graceful degradation?**
4. **Mobile bandwidth budget per screen.** Listing screen: a few hundred KB max. Detail screen: depends on media. Don't ship megabytes of JSON for a list view.
5. **Background work strategy: push, pull, hybrid?**
6. **Forced upgrade strategy: how do you handle a security or correctness fix that requires a new client?**
7. **Hot key detection: what tells you about a viral piece of content before it brings the cache down?**
8. **Personalization vs cacheability tradeoff.** Each personalized field reduces cache hit ratio. Audit the personalization budget.
9. **Anonymous vs logged-in routing: are anonymous users on a separate, more aggressively cached path?**

## Common pitfalls

### Per-user data on a CDN

CDNs cache by URL. Per-user data appears at unique URLs for each user. Cache hit ratio is ~0. The CDN provides no benefit except latency from edge POPs (which may or may not justify the cost).

### "Sync everything" without conflict resolution

The app syncs all local state to the server; the server is "the source of truth." Two devices producing conflicting writes are not handled; one wins silently, the other's edits are lost.

### App-side caching that doesn't expire

The app caches API responses indefinitely. Days later, the data is stale. The app shows wrong information. No mechanism to refresh except clearing the app's storage.

### Server changes that require client updates without graceful degradation

The server stops returning a field that old clients depend on. Old clients crash on null. Server-side changes must consider the long tail of old clients.

### Polling at fixed intervals

Every client polls every 30s. Multiply by user count = constant load floor that scales linearly with users. Push (long-polling, websockets, native push) is more efficient at scale.

### Cache key collision across logged-out users

If logged-out users see a cached "homepage" but the cache key doesn't include locale, currency, A/B variant — users see each other's variants. Cache keys must include every dimension that varies the response.

### Treating mobile as a thin client

The design assumes the app is just a UI. But mobile has constraints (battery, bandwidth, intermittent connectivity, offline) that the server can't ignore. APIs designed for browsers waste mobile capability.

## Anchor numbers

- **CDN cache hit ratio**: target **90%+** for static assets; **50–80%** for dynamic content with good TTL strategy; **< 50%** suggests the responses are too personalized to cache.
- **Mobile bandwidth (cellular)**: 4G in mature markets averages **10–30 Mbps**; emerging markets (3G/EDGE) **< 1 Mbps**; tune payload sizes accordingly.
- **App store update tail**: it takes **2–4 weeks** for a forced-launch update to reach 90% of users; ~5% may never update. Design for backward compatibility.
- **Battery target**: background app battery use **< 1%/hour** is acceptable; **> 5%/hour** triggers user complaints and uninstalls.
- **Push connection cost**: maintaining a persistent push connection (websocket) is cheap on the client (~1mA), but adds server-side memory per active user. ~1k connections per GB of server RAM is a reasonable order of magnitude.
- **Cache TTL spectrum**:
  - **Static assets (immutable)**: years; hashed URLs.
  - **Catalog data (changes daily)**: hours.
  - **User profile (changes occasionally)**: minutes, with explicit invalidation on update.
  - **Personalized feed (changes often)**: seconds to minutes, or never-cache.

## Cross-archetype interactions

- **Read-heavy-mobile + multi-tenant**: per-tenant CDN cache pollution can be a problem (one tenant's content evicts others). Separate cache namespaces per tenant tier.
- **Read-heavy-mobile + geo-distributed**: CDN at the edge solves many "users far away" problems without full geo-distribution of the backend. Use the CDN as the geo-distribution layer for static/cacheable content.
- **Read-heavy-mobile + observability**: per-screen / per-API-endpoint cache hit rate is a first-class metric. CDN-edge-vs-origin ratio.
- **Read-heavy-mobile + write-heavy**: the write side of a mostly-read system (user posting, voting, commenting) is still real; design those endpoints separately from the read-heavy paths.
