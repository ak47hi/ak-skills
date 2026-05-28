# Is this a leak or a sizing issue? Probably neither — it's burst contention. Here's how to prove it.

Short answer: **based on what you've described, this is most likely a sizing / burst-contention problem, not a leak.** But before either camp wins, you need to run a 5-minute triage that disambiguates the three possibilities. The triage itself is cheap. The wrong fix in either direction is expensive — raising the pool size masks leaks, and chasing leaks when the problem is burst contention wastes a sprint.

Here's the walkthrough.

---

## Why your symptoms don't look like a leak

A leak has a specific shape. The pool's `ActiveConnections` (or your process's overall FD count) climbs **monotonically over hours or days** and never recovers without a process restart. The shape on a dashboard is a sawtooth tied to deploys — flat-line growth between restarts, drops to zero on each restart, climbs again.

What you're describing is a different shape:

- `ActiveConnections` **oscillates between 0 and 18 all day** — it returns to 0. Connections are being released. The pool is breathing.
- The timeout errors are **scoped to an 8am peak window** and resolve by 9am as traffic settles — the pool recovers on its own.
- This pattern repeats daily and is bounded in time.

A leak does not recover on its own. If you had a real leak, by 9am the pool would still be pinned near 20, and by 10am, and tomorrow, and the day after, until you restart. You'd also see the error rate getting worse week-over-week, not the same handful every morning.

What this shape actually looks like is: **traffic at 8am briefly demands more than 20 concurrent connections, requests queue on `getConnection()`, some queue longer than the 30s `connectionTimeout`, and you get timeouts.** That's contention, not a leak.

---

## But — don't take my word for it. Run the triage.

There's a known failure mode where a slow leak hides inside an oscillating pool: most queries are well-behaved and the pool oscillates fine, but **one rare code path** (maybe an exception handler that runs only during the 8am surge, or a `@Transactional` method that calls an HTTP service that's slow under load) holds connections too long. The leak rate is low enough that GC and the connectionTimeout still recover the pool by 9am, so the oscillation looks healthy — but during the peak, a few slow holders push the pool to exhaustion just long enough to cause your 30s timeouts.

So we need to disambiguate three hypotheses with one set of measurements:

| Hypothesis | What you'd see |
|---|---|
| **(A) Pure sizing / burst contention** | At 8am: `ActiveConnections` pins at 20, `ThreadsAwaitingConnection > 0` momentarily, no sessions are `idle in transaction` server-side. Off-peak: pool oscillates 0–18 cleanly. FD slope is flat day-over-day. |
| **(B) Slow leak that surfaces only under burst** | At 8am: `ActiveConnections` pins at 20, `ThreadsAwaitingConnection > 0`, **and** some Postgres sessions are `idle in transaction` for 30+ seconds. FD slope is non-zero day-over-day even between deploys. |
| **(C) Held-too-long transactions (the most common "is it a leak?" question)** | Pool oscillates correctly off-peak. At 8am, sessions go `idle in transaction` for 10–30 seconds (not held forever, just held *during* a slow upstream call). Not a leak in the strict sense — connections do return — but the *effective* pool size during peak shrinks because connections are held longer than they should be. |

(C) is the one your team is actually disagreeing about, even if nobody named it. The argument "it's a leak" and the argument "it's sizing" can both be partially right if connections are being held across a slow upstream call during peak.

### The four measurements you need

Run these during the next 8am window. Each is one command. You'll have a verdict in 10 minutes.

**1. Confirm or rule out a true leak — sample the FD count over time.**

```sh
# run this at 7:30am, 8:30am, 9:30am, 11am, and at the same times tomorrow
kubectl exec -it <pod> -- sh -c 'ls /proc/1/fd | wc -l'
```

If this number is roughly the same off-peak today, off-peak yesterday, and off-peak last week — there is no leak. A leak's slope is measured in FDs/min over hours.

**2. Capture HikariCP state during the 8am incident.**

Enable Hikari MBeans and leak detection if you haven't already:

```yaml
spring.datasource.hikari.register-mbeans: true
spring.datasource.hikari.leak-detection-threshold: 30000   # 30s — same as your connectionTimeout
spring.datasource.hikari.metric-registry: <your micrometer registry>
```

Then during 8am, scrape (or look at the dashboard for):

- `hikaricp_connections_active` — does it hit 20 and stay there, or just touch 20 briefly?
- `hikaricp_pending_threads` (`ThreadsAwaitingConnection`) — is it > 0 for seconds, or only milliseconds?
- `hikaricp_connections_usage_seconds` (a histogram) — what's the p99 connection hold time during peak vs off-peak?

The p99 hold time is the diagnostic gold. If off-peak p99 is 50ms and 8am p99 is 8 seconds, **connections are being held longer at peak** — that's the (C) pattern, and it tells you the fix is not "raise the pool" but "find why this code path holds longer under load."

**3. Capture leak-detection stack traces.**

With `leak-detection-threshold: 30000`, any connection held longer than 30 seconds logs a stack trace of the thread that acquired it. If the timeouts at 8am are caused by held-too-long connections, those stack traces are the answer — they point directly at the call site. If no leak-detection warnings fire during 8am at all, you can rule out (B) and (C) and you're left with pure (A): true burst contention.

**4. Look at Postgres-side state during the incident.**

```sql
SELECT pid, state, wait_event_type, wait_event, state_change,
       now() - state_change AS idle_for, query
FROM pg_stat_activity
WHERE datname = '<your_db>'
  AND state IN ('idle in transaction', 'idle', 'active')
ORDER BY state_change ASC;
```

What you want to see at 8am:

- If most sessions are `active` (running a query) and a few are `idle` (returned to pool): healthy. You have (A) — pure contention. Add pool capacity, but cautiously.
- If sessions are `idle in transaction` for 10–30 seconds: you have (C). Something — an HTTP call, a slow service call, a lock — is being awaited *while a transaction is open*. The fix is to shrink transaction scope, not raise the pool size.
- If sessions are `idle in transaction` for minutes (well past 30s): you have (B), a real leak. Stack traces from leak-detection-threshold tell you which call site.

---

## The decision tree (based on what triage shows)

### If triage shows pure contention (A)

You can raise the pool — but raise it deliberately, not reactively.

**Sanity-check the pool size against the database side first.** The "right" pool size is bounded by what your Postgres instance can handle, not by what makes the timeout go away. The widely-cited HikariCP formula:

```
pool_size = ((core_count * 2) + effective_spindle_count)
```

…is a starting point for a single application instance against a server. If you have N app instances behind a load balancer, multiply that by N and check it against your Postgres `max_connections` (typical default: 100). A pool of 20 × 10 instances = 200 connections, which **already exceeds** a default Postgres `max_connections`. Going to 30 puts you at 300.

If you're not pgbouncer-fronted yet, that's the bigger architectural fix — front Postgres with pgbouncer in transaction-pooling mode, and you can have small pool sizes per instance without worrying about Postgres connection-count ceilings.

If you are pgbouncer-fronted (or your Postgres can comfortably handle the increase), then a measured bump — 20 → 25, monitor a week, then 25 → 30 if needed — is reasonable. **Do not jump straight to 50.** Each new connection consumes Postgres backend memory (~10MB), and you'd rather find the smallest pool that absorbs the peak than the largest pool you can get away with.

Also consider: instead of more concurrency, can you make individual queries faster at peak? A missing index, a slow N+1 pattern triggered only when traffic crosses a certain threshold, or an analytics query that overlaps with the 8am batch can each contribute. Pool exhaustion is often a symptom of "queries are getting slower, not requests getting denser."

### If triage shows held-too-long transactions (C)

This is the case where raising the pool size *technically* makes the timeouts go away but for the wrong reason — you're papering over a structural issue. The fix is to shrink the connection scope at the call sites the leak-detection traces point to.

The canonical fix:

```java
// LEAK-SHAPED — holds DB connection across an outbound HTTP call
@Transactional
public void enrichAndSaveUser(long id) {
    User u = userRepo.findById(id);              // uses connection from pool
    EnrichmentResponse er = httpClient.fetch(u); // network I/O, possibly slow under 8am load
    userRepo.saveEnrichment(id, er);             // uses same connection
}

// FIX — two short transactions, no DB connection held during HTTP I/O
public void enrichAndSaveUser(long id) {
    User u = loadUser(id);                       // tx 1, fast
    EnrichmentResponse er = httpClient.fetch(u); // no DB connection held
    saveEnrichment(id, er);                      // tx 2, fast
}

@Transactional(readOnly = true)
public User loadUser(long id) { return userRepo.findById(id); }

@Transactional
public void saveEnrichment(long id, EnrichmentResponse er) {
    userRepo.saveEnrichment(id, er);
}
```

Important caveat: when you split a transaction around an external call, you introduce a crash window between the two transactions. If the process dies after the HTTP success but before the second transaction, the external side-effect happened but the database doesn't know it. To make this safe:

1. **Pass an idempotency key to the external call**, derived from the unit-of-work id, so retries see the same outcome.
2. **Add a reconciliation job** that scans rows in a `PENDING` state older than N minutes, queries the external service by idempotency key, and resolves the local state.

If the external call doesn't support idempotency keys and you can't add a reconciler, then the transaction-split fix is risky and you should instead focus on making the upstream call faster (timeout it aggressively, circuit-break, cache) so it doesn't dominate transaction time.

### Belt-and-braces: Postgres-side guardrails (do this regardless of A/B/C)

```sql
ALTER ROLE app_user SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app_user SET statement_timeout = '15s';
```

`idle_in_transaction_session_timeout` is precisely the circuit breaker for case (C) — Postgres terminates a session that's been in a transaction without running a statement for >60s, the connection returns to the pool, the application gets a clear error. This won't fix your bug, but it prevents one slow upstream call from cascading into pool exhaustion across the cluster.

Set it tighter than your slowest legitimate transaction. If your real transactions never exceed 5 seconds, set this to 10s; the cushion catches accidents without firing on legitimate work.

### If triage shows a true slow leak (B)

This is the least likely scenario given the daily oscillation, but possible. Leak-detection stack traces are the smoking gun — they'll point to the unclosed Connection / Statement / ResultSet. The fix is try-with-resources at the offending call site. Re-run TRIAGE after the fix; if the FD slope across a week is flat (not just slower), you're done.

---

## Don't raise the pool size first

I want to flag this directly because it's the easy answer and it's wrong in three of the four scenarios above. Even in scenario (A) — pure burst contention — jumping from 20 to (say) 50 has costs:

- **Masking effect.** If there's a low-grade hold-too-long bug, a bigger pool absorbs it silently. Now the leak compounds in the background and your dashboard says "fine" until the day it really isn't.
- **Database-side pressure.** 50 connections × N app instances may exceed `max_connections`. The first failure mode you hit then isn't application timeouts — it's database connection refusals, which are much harder to debug.
- **Memory cost.** Each Postgres backend allocates work_mem + maintenance buffers. 50 idle backends per instance × 10 instances × 10MB = 5GB of Postgres-side memory holding pool slack you mostly don't use.

The HikariCP author's note that's worth internalizing: **a smaller pool with low contention is faster than a larger pool with high contention.** Queue depth at the application's `getConnection()` call is not necessarily worse than queue depth at the database's CPU scheduler. The number worth optimizing is end-to-end request latency, not pool active count.

---

## Verification plan

Run this whole sequence:

1. **Before changing anything** — instrument Hikari with `register-mbeans: true` and `leak-detection-threshold: 30000`. Capture the four measurements above during one 8am window. Record the verdict (A/B/C).
2. **Apply the matching fix** from the decision tree above. Resist the urge to apply more than one — you want to know which one moved the needle.
3. **Re-measure during the next 8am window** under the same load. Specifically:
   - p99 `connection_acquire_time` should be < 100ms (was timing out at 30s).
   - `ThreadsAwaitingConnection` should be 0 or near-zero throughout peak.
   - No leak-detection stack traces in the logs.
   - No Postgres sessions `idle in transaction` for > a few seconds.
   - FD count returns to the same baseline by 9am as it did pre-fix.
4. **Hold off on declaring victory for a full week.** A leak shows as a slow daily upward drift in steady-state FD count. One morning of clean metrics isn't enough; the pattern is daily.

If after the fix you still see timeouts at 8am, re-run the triage — the dominant hypothesis may have shifted (e.g., you fixed (C) and now the residual is pure (A) at a higher load watermark), and the right next move differs.

---

## TL;DR for the team disagreement

- **"It's a leak"** — almost certainly wrong as stated, because the pool returns to 0 every day. Real leaks don't recover.
- **"It's a sizing issue, raise to 30 or 50"** — possibly right, but unsafe to apply without the four triage measurements. There's a real chance you have a held-too-long transaction (case C) that a bigger pool will mask.
- **What's actually going on (most likely)** — at 8am, either (a) you genuinely need more concurrency than 20 (then raise it 20→25 deliberately, after sanity-checking Postgres `max_connections`), or (b) a code path holds a connection across a slow upstream call that only gets slow at peak (then shrink the transaction scope and the pool of 20 will be plenty).
- **Get the leak-detection stack traces during the next 8am window.** Those 30+ second hold traces — or their absence — collapse the disagreement to a single answer in one day.
