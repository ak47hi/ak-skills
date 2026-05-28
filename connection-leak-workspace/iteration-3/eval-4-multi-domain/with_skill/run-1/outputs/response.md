# Two leaks, one root cause: `processRefund` holds a HikariCP connection across a Stripe HTTP call

You've got two symptoms but the signatures and timing tell me this is almost certainly **one bug** producing both:

- HikariCP timeouts every ~90 min → pool drained, `ThreadsAwaitingConnection > 0`, requests piling on `getConnection()` until the 30s connection-timeout fires.
- CLOSE_WAIT to `api.stripe.com` climbing ~5/min → **Stripe (remote) closed the TLS connection, your app never called `Response.close()`**. That's a per-request HTTP body leak.
- HikariCP leak-detection threshold tripping inside `PaymentService.processRefund` → that method acquires a JDBC connection and parks on a slow / hanging Stripe call without releasing it.

Classic "transaction held across an outbound HTTP call." The DB connection is held until the Stripe HTTP call returns (or times out). When Stripe occasionally hangs or returns slow, the connection sits in `idle in transaction` long enough to (a) trip the Hikari leak detector and (b) drain the pool every ~90 min. The CLOSE_WAIT count tells me the Stripe-side response body is **also** not being closed on at least one branch — likely the error path of the same method. So I'd treat this as a **JDBC scope-too-wide leak** layered on top of a **per-request HTTP response leak** in OkHttp / Apache HC / `com.stripe.net.HttpClient`.

Below is the diagnosis walkthrough, the fix, and the verification plan. We'll go JDBC-first because it's the faster-growing class (pool exhaustion is causing the 500s every 90 min; CLOSE_WAIT growth is slower).

---

## 1. TRIAGE — capture the baseline before touching anything

Don't skip this. The slope numbers are what you'll compare against in VERIFY.

```sh
POD=<your-pod>

# 1a. FD slope baseline (sample over 5 min minimum)
kubectl exec -it $POD -- sh -c 'for i in $(seq 1 10); do ls /proc/1/fd | wc -l; sleep 30; done'

# 1b. FD classification — confirm sockets dominate, mixed DB + non-DB
kubectl exec -it $POD -- sh -c 'ls -l /proc/1/fd | awk "{print \$11}" | cut -d: -f1 | sort | uniq -c | sort -rn'

# 1c. Top remotes — expect both <pg-host>:5432 and stripe IPs
kubectl exec -it $POD -- ss -tn state established | awk 'NR>1 {print $5}' | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head

# 1d. CLOSE_WAIT count — should match what alerts say (~400, climbing)
kubectl exec -it $POD -- ss -tn state close-wait | wc -l

# 1e. CLOSE_WAIT by remote — confirm Stripe is the dominant remote
kubectl exec -it $POD -- ss -tn state close-wait | awk 'NR>1 {print $4}' | awk -F: '{print $1}' | sort | uniq -c | sort -rn
```

Record:

```
LEAK CONFIRMED:
  Pod:         <pod>
  Slope:       <FDs/min> over <T> minutes
  Dominant:    socket (split: DB 5432 + stripe :443)
  Top remote:  <pg-host>:5432 — N FDs, api.stripe.com :443 — ~400 CLOSE_WAIT
  Toolchain:   jcmd, jstack, jmap, MAT
  Verdict:     JDBC first (slope dominance + customer 500s), then HTTP
```

---

## 2. DIAGNOSE — both code-audit and live probes in parallel

### 2a. Server-side: confirm `idle in transaction`

```sql
SELECT pid, state, wait_event_type, wait_event,
       now() - state_change AS idle_for,
       query
FROM pg_stat_activity
WHERE datname = '<your_db>'
  AND state IN ('idle in transaction', 'idle in transaction (aborted)')
ORDER BY state_change ASC;
```

You'll see sessions stuck `idle in transaction` for tens of seconds, running the query that comes **just before** the Stripe call in `processRefund` (probably a `SELECT ... FOR UPDATE` on the refund row or an `INSERT` into a refund/audit table).

### 2b. JVM side: confirm the holder thread

```sh
kubectl exec -it $POD -- jstack 1 > /tmp/stack.txt
kubectl cp $POD:/tmp/stack.txt ./stack.txt

# threads holding a Postgres connection — look for application frames
grep -B 2 -A 20 'PgConnection\|HikariProxyConnection' stack.txt

# threads blocked waiting for the pool
grep -B 2 -A 10 'HikariPool.*getConnection' stack.txt
```

You'll find one thread per leaked connection parked deep inside an OkHttp / Apache HC / Stripe SDK frame (`SocketInputStream.read`, `Http2Reader.readPing`, etc.), with `PaymentService.processRefund` and `HikariProxyConnection` higher up on the stack. That's the smoking gun.

### 2c. Source audit — the `processRefund` shape

The Hikari leak-detection stack already points you at `PaymentService.processRefund`. Open it and look for this shape:

```java
@Transactional                                          // (1) DB transaction held for the whole method
public Refund processRefund(RefundRequest req) {
    Payment p = paymentRepo.findById(req.paymentId);    // connection acquired here
    auditRepo.recordRefundAttempt(p);                   // (2) holds connection

    com.stripe.model.Refund stripeRefund =              // (3) BLOCKING HTTP — connection still held
        com.stripe.model.Refund.create(params);

    p.setRefundId(stripeRefund.getId());                // (4) post-Stripe DB write
    paymentRepo.save(p);
    return toDomain(stripeRefund, p);
}
```

That's the JDBC scope-too-wide leak. The DB connection is held across an unbounded-time HTTP call to Stripe.

### 2d. Find the HTTP body leak

Stripe's Java SDK uses an internal `HttpClient` and returns parsed objects, so the per-request close is usually fine on the **happy path**. The CLOSE_WAIT growth tells me something on an **error path** isn't releasing. Two things to check:

```sh
# Is your code using OkHttp / Apache HC directly to call Stripe (rather than the SDK)?
rg -n 'api\.stripe\.com|stripe\.com/v1' --type java

# OkHttp Response not in try-with-resources
rg -n '\.execute\(\)' --type java | rg -v 'try\s*\('

# Apache HC missing EntityUtils.consume
rg -n '\.execute\(.*\)' --type java | rg -i 'httpclient' | rg -v 'try\s*\('

# Stripe SDK version — older versions had a known body-not-fully-drained bug on non-2xx
rg -n 'com\.stripe.*<version>' build.gradle pom.xml
```

If you're using the Stripe SDK directly, check the version — the SDK before 24.x had a known issue where non-2xx responses left the underlying connection in CLOSE_WAIT under certain timeout conditions. Upgrade to current.

If you're calling Stripe via your own OkHttp or Apache HC client, the body-on-error path is your problem.

### 2e. Confirm singleton clients (rule out per-client leak)

```sh
# Heap dump
kubectl exec -it $POD -- jcmd 1 GC.heap_dump /tmp/h.hprof
kubectl cp $POD:/tmp/h.hprof ./h.hprof
```

In MAT, count instances of:
- `okhttp3.OkHttpClient` — should be 1 (or a small known number)
- `com.stripe.net.HttpClient` — should be 1
- `org.apache.hc.client5.http.impl.classic.CloseableHttpClient` — same

If counts are in the hundreds/thousands, you've got an additional per-client construction leak — but with ~400 CLOSE_WAIT growing only 5/min, I doubt it. This is far more likely per-request body close.

---

## 3. FIX

There are **two fixes** because there are two distinct bugs. Apply both.

### Fix A — Shrink the JDBC scope (the dominant leak)

Pull the Stripe call **out of the transaction**. Two short DB transactions wrap one HTTP call. Combine with an idempotency key so the split doesn't introduce a crash window.

```java
@Service
public class PaymentService {

    private final PaymentRepository paymentRepo;
    private final AuditRepository auditRepo;
    private final RefundExecutor refundExecutor;     // see below

    // PUBLIC entry point: orchestrates two short transactions around the HTTP call.
    // No @Transactional here — this method must NOT hold a DB connection across the Stripe call.
    public Refund processRefund(RefundRequest req) {
        // Transaction 1: record intent + mint idempotency key.
        RefundAttempt attempt = recordAttempt(req);

        // No DB connection held here. Stripe call is the only thing happening.
        com.stripe.model.Refund stripeRefund;
        try {
            RequestOptions opts = RequestOptions.builder()
                .setIdempotencyKey(attempt.idempotencyKey())     // (A) idempotency-safe retries
                .build();
            stripeRefund = com.stripe.model.Refund.create(
                Map.of("payment_intent", req.paymentIntentId(),
                       "amount", req.amount()),
                opts);
        } catch (StripeException e) {
            markAttemptFailed(attempt.id(), e);                  // own short tx
            throw new RefundFailedException(e);
        }

        // Transaction 2: commit the outcome.
        return finalizeRefund(attempt.id(), stripeRefund);
    }

    @Transactional
    protected RefundAttempt recordAttempt(RefundRequest req) {
        Payment p = paymentRepo.findById(req.paymentId())
            .orElseThrow();
        return auditRepo.recordPending(p, UUID.randomUUID().toString());
    }

    @Transactional
    protected void markAttemptFailed(long attemptId, StripeException e) {
        auditRepo.markFailed(attemptId, e.getCode(), e.getMessage());
    }

    @Transactional
    protected Refund finalizeRefund(long attemptId, com.stripe.model.Refund stripeRefund) {
        RefundAttempt attempt = auditRepo.findById(attemptId);
        Payment p = paymentRepo.findById(attempt.paymentId()).orElseThrow();
        p.setRefundId(stripeRefund.getId());
        paymentRepo.save(p);
        auditRepo.markCompleted(attemptId, stripeRefund.getId());
        return toDomain(stripeRefund, p);
    }
}
```

Two things to call out about this fix:

1. **Idempotency key on Stripe.** Required, not optional. Splitting the transaction creates a crash window: process dies after Stripe succeeds but before `finalizeRefund` commits, and you've refunded the customer but your DB doesn't know. The idempotency key + a reconciliation job (below) closes the window.
2. **Reconciliation worker.** Periodically scan `RefundAttempt` rows in `PENDING` older than 5 minutes, query Stripe by idempotency key, and call `finalizeRefund` / `markAttemptFailed` based on the response. Without this, the split fix is strictly worse than the leak.

```java
// Run every minute via @Scheduled
@Scheduled(fixedDelay = 60_000)
public void reconcilePending() {
    for (RefundAttempt a : auditRepo.findPendingOlderThan(Duration.ofMinutes(5))) {
        try {
            com.stripe.model.Refund r = com.stripe.model.Refund.retrieve(
                Map.of("idempotency_key", a.idempotencyKey()),  // pseudo — use Stripe's search if needed
                RequestOptions.getDefault());
            finalizeRefund(a.id(), r);
        } catch (Exception e) {
            log.warn("reconcile failed for attempt {}", a.id(), e);
        }
    }
}
```

Also worth noting: `@Transactional` on protected methods works through the Spring proxy only when called from outside the class. The structure above keeps that invariant — `processRefund` is on the same class but the `@Transactional` methods are invoked via `this` only because they're separately-injected (or you split into a sibling bean). If you keep them on the same bean, **inject `self` and call `self.recordAttempt(...)`** to ensure proxy interception:

```java
@Autowired @Lazy private PaymentService self;
// then: self.recordAttempt(req), self.finalizeRefund(...), self.markAttemptFailed(...)
```

### Fix B — Close the Stripe response on every branch

If you're calling Stripe directly (not via the SDK):

```java
// OkHttp
try (Response r = okHttp.newCall(req).execute()) {
    if (!r.isSuccessful()) {
        // body still closes via try-with-resources on this exit
        throw new StripeApiException(r.code());
    }
    return objectMapper.readValue(r.body().byteStream(), StripeRefund.class);
}

// Apache HttpClient 5.x
try (CloseableHttpResponse r = apacheHc.execute(req)) {
    HttpEntity entity = r.getEntity();
    try {
        String body = EntityUtils.toString(entity);
        if (r.getCode() / 100 != 2) throw new StripeApiException(r.getCode(), body);
        return objectMapper.readValue(body, StripeRefund.class);
    } finally {
        EntityUtils.consume(entity);                  // drains and releases on every path
    }
}
```

If you're using the Stripe SDK, **upgrade to a current 24.x+ version** — the older releases had a known CLOSE_WAIT issue on non-2xx responses.

Also confirm `OkHttpClient` / Stripe `HttpClient` is a **per-process singleton** — `new OkHttpClient()` inside `processRefund` would explain rapid client-construction leak as well, but the slope you described (5/min) is consistent with per-request body close, not per-client.

### Fix C — Defense in depth (do these even after A+B land)

```yaml
# application.yml — already mentioned the leak-detection threshold is firing; tighten it
spring.datasource.hikari.leak-detection-threshold: 30000   # 30s
spring.datasource.hikari.register-mbeans: true
```

Set a Stripe HTTP timeout that's shorter than the DB statement timeout (an unbounded Stripe call is the original sin here):

```java
// Stripe SDK
Stripe.setConnectTimeout(5_000);
Stripe.setReadTimeout(10_000);
// or RequestOptions per call: .setConnectTimeout(...).setReadTimeout(...)
```

Postgres-side circuit breakers — apply per role:

```sql
ALTER ROLE app_user SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app_user SET statement_timeout = '15s';
```

These don't fix the bug but they keep a future variant of it from cascading to pool exhaustion.

ArchUnit rule to prevent the next person from doing this:

```java
@ArchTest
static final ArchRule no_http_calls_inside_transactional =
    noMethods()
        .that().areAnnotatedWith(Transactional.class)
        .should().callMethodWhere(target(owner(assignableTo("com.stripe.net.HttpClient")
            .or(assignableTo("okhttp3.OkHttpClient"))
            .or(assignableTo("org.springframework.web.client.RestTemplate"))
            .or(assignableTo("org.springframework.web.reactive.function.client.WebClient"))
            .or(assignableTo("org.apache.hc.client5.http.classic.HttpClient")))));
```

---

## 4. VERIFY

Re-run TRIAGE under the same load and check all four signals simultaneously. The slope must be **flat**, not just lower.

```sh
# 1. FD slope — must be flat
kubectl exec -it $POD -- sh -c 'for i in $(seq 1 10); do ls /proc/1/fd | wc -l; sleep 30; done'

# 2. CLOSE_WAIT to Stripe — should drop to ~0
kubectl exec -it $POD -- ss -tn state close-wait | grep -c stripe

# 3. HikariCP MBean — ActiveConnections should oscillate, ThreadsAwaitingConnection ~0
kubectl exec -it $POD -- jcmd 1 ManagementAgent.start_local
# then via jmxterm or actuator: com.zaxxer.hikari:type=Pool (HikariPool-1)
```

```sql
-- 4. No more idle-in-transaction sessions
SELECT count(*)
FROM pg_stat_activity
WHERE datname = '<your_db>'
  AND state = 'idle in transaction'
  AND now() - state_change > interval '5 seconds';
-- expected: 0
```

**Pass criteria (all four must hold for a full traffic cycle, minimum 24h):**

1. FD count oscillates, doesn't climb monotonically.
2. CLOSE_WAIT to `api.stripe.com` returns to near-zero and stays there.
3. HikariCP `ActiveConnections` oscillates well below `maximumPoolSize`; `ThreadsAwaitingConnection` is 0 except during transient bursts.
4. `pg_stat_activity` shows no `idle in transaction` sessions older than a few seconds.

If FD slope is flat but CLOSE_WAIT is still climbing, Fix B is incomplete — there's another response-body-not-closed path. Re-run the source audit grep narrowed to the Stripe code path.

If CLOSE_WAIT is flat but HikariCP still occasionally pins at max, Fix A is incomplete — there's another `@Transactional` method calling out to an external service. The ArchUnit rule above will surface it.

---

## 5. Watch list (after deploy)

- **Metric:** `hikaricp_connections_active`, `hikaricp_connections_pending`, `process_open_fds`, `node_sockstat_TCP_inuse{state="CLOSE_WAIT"}`.
- **Watch window:** 24h covering one full traffic cycle; specifically check the ~90-min cadence — the absence of the cyclical timeout pattern is your strongest signal.
- **Alert:** re-fire on FD slope > 1/min sustained over 10 min, or `hikaricp_connections_pending > 0` sustained over 1 min, or CLOSE_WAIT to `api.stripe.com` > 50.
- **Reconciliation worker** must be deployed at the same time as the transaction split — verify its first run logs cleanly. Without it, any pod crash between `recordAttempt` and `finalizeRefund` leaks money (refund succeeded at Stripe, DB doesn't know).

---

## Summary

| Resource | Library | Pattern | Fix |
|---|---|---|---|
| JDBC connection | HikariCP | Scope-too-wide (transaction across Stripe call) | Split into two short txns + idempotency key + reconciliation worker |
| HTTP socket | OkHttp / Apache HC / Stripe SDK | Per-request body not closed on error path | try-with-resources on `Response` + `EntityUtils.consume`; upgrade Stripe SDK |

Fix A is the urgent one (causing customer 500s every 90 min). Fix B is the slow leak (FD exhaustion in ~hours-to-days depending on traffic). Apply both, then run the verification suite under real traffic for a full 24h cycle.
