# HikariCP exhaustion: `@Transactional` held across Stripe call

You already pasted the smoking gun — `idle in transaction` for 5+ minutes, HikariCP timing out at 30s, Stripe call inside `@Transactional`. That's the canonical "connection scope too wide" leak. Skipping elicitation; running an abbreviated TRIAGE to capture the slope baseline, then straight to DIAGNOSE → FIX → VERIFY.

---

## TRIAGE (capture baseline before you change anything)

Run these on the pod now so VERIFY has a number to compare against:

```sh
# 1. FD slope over 5 minutes — this is the number to beat
kubectl exec -it <pod> -- sh -c 'for i in $(seq 1 10); do date +%T; ls /proc/1/fd | wc -l; sleep 30; done'

# 2. Confirm sockets to Postgres dominate
kubectl exec -it <pod> -- ss -tn state established | awk 'NR>1 {print $5}' | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head

# 3. Server-side: how many sessions are stuck, and on what?
```

```sql
SELECT pid, state, wait_event_type, wait_event,
       now() - state_change AS idle_for,
       left(query, 120) AS query
FROM pg_stat_activity
WHERE datname = '<your_db>'
  AND state = 'idle in transaction'
ORDER BY state_change ASC;
```

The 12 stuck sessions you saw — pin the SQL on the `query` column. It's the last statement before the Stripe call. That tells you which `@Transactional` method is the offender (almost always one, sometimes two).

Record this block in your incident channel before deploying anything:

```
LEAK CONFIRMED:
  Slope:      <N> FDs/min
  Dominant:   sockets to <postgres-host>:5432
  Top remote: <postgres-host>:5432 — ~12 FDs idle-in-tx
  Verdict:    JDBC — connection scope held across Stripe API call
```

---

## DIAGNOSE

### Source audit — find the call site

The pattern is `@Transactional` method calling Stripe. Grep:

```sh
# Methods that are @Transactional AND call Stripe
rg -n -B 2 -A 30 '@Transactional' --type java | rg -B 30 'com\.stripe|Stripe\.|stripeClient'

# Or just find all Stripe call sites and check their enclosing annotation
rg -n 'com\.stripe\.|StripeClient|PaymentIntent\.create|Charge\.create|Customer\.create' --type java
```

For each hit, open the file and check whether the **enclosing method** (or any method on its call stack within the same `@Service`) is `@Transactional`. Self-invocation also counts as broken — `@Transactional` on a private method or same-class call is a no-op, but it can still acquire a connection in a wider scope via the outer transactional caller.

### Live confirmation — turn on HikariCP leak detection now

If it's not already on:

```yaml
# application.yml
spring:
  datasource:
    hikari:
      leak-detection-threshold: 30000   # 30s — just above your longest legitimate tx
      register-mbeans: true
```

Redeploy. The next time the pool exhausts, HikariCP logs the **acquire stack trace** of every connection held past 30s. That stack identifies the exact `file:line` of the offender — no guessing.

While you wait, dump the JVM:

```sh
kubectl exec -it <pod> -- jstack 1 > /tmp/stack.txt
kubectl cp <pod>:/tmp/stack.txt ./stack.txt

# Threads holding a PgConnection and parked inside Stripe / HTTP I/O
grep -B 2 -A 30 'PgConnection\|HikariProxyConnection' stack.txt | grep -B 5 -A 20 'stripe\|okhttp\|HttpClient\|socketRead'
```

You're looking for a thread frame that holds a `PgConnection` reference and is parked in `SocketInputStream.socketRead0` (or `HttpURLConnection`, OkHttp `RealCall`, etc). That thread is the leak.

### MBean confirmation

```sh
# Pool state — confirms the diagnosis from the JVM side
kubectl exec -it <pod> -- jcmd 1 ManagementAgent.start_local
# Then jmxterm or arthas to read com.zaxxer.hikari:type=Pool (<name>)
```

Expect: `ActiveConnections` pinned at 20, `IdleConnections` 0, `ThreadsAwaitingConnection` > 0. That confirms exhaustion, not contention.

---

## FIX

Two changes. Both are non-negotiable.

### 1. Shrink the connection scope — split the transaction around the Stripe call

This is the actual bug. Don't hold a DB connection across an outbound HTTP call.

**Before (the leak):**

```java
@Service
public class CheckoutService {

    @Transactional
    public OrderResult checkout(long orderId, BigDecimal amount) {
        Order order = orderRepo.findById(orderId).orElseThrow();
        order.markPending();
        orderRepo.save(order);

        // DB connection held for the entire Stripe round-trip (200ms - 30s+)
        PaymentIntent intent = PaymentIntent.create(
            PaymentIntentCreateParams.builder()
                .setAmount(amount.movePointRight(2).longValueExact())
                .setCurrency("usd")
                .build()
        );

        order.markPaid(intent.getId());
        orderRepo.save(order);
        return new OrderResult(order.getId(), intent.getId());
    }
}
```

**After (two short transactions, idempotent Stripe call in between):**

```java
@Service
public class CheckoutService {

    private final OrderTxService orderTx;     // separate bean — proxy boundary matters
    private final StripeClient stripe;        // singleton, NOT constructed per call

    // NOT @Transactional — orchestrates two transactions with a network call between
    public OrderResult checkout(long orderId, BigDecimal amount) {
        // Tx 1: short — mark pending, commit, release connection
        orderTx.markPending(orderId);

        // No DB connection held here. Idempotency key derived from orderId so
        // retries (process crash, network blip) converge on the same PaymentIntent.
        PaymentIntent intent = PaymentIntent.create(
            PaymentIntentCreateParams.builder()
                .setAmount(amount.movePointRight(2).longValueExact())
                .setCurrency("usd")
                .build(),
            RequestOptions.builder()
                .setIdempotencyKey("order-" + orderId)
                .build()
        );

        // Tx 2: short — mark paid, commit, release connection
        orderTx.markPaid(orderId, intent.getId());

        return new OrderResult(orderId, intent.getId());
    }
}

@Service
public class OrderTxService {

    private final OrderRepository orderRepo;

    @Transactional
    public void markPending(long orderId) {
        Order o = orderRepo.findById(orderId).orElseThrow();
        o.markPending();
        orderRepo.save(o);
    }

    @Transactional
    public void markPaid(long orderId, String paymentIntentId) {
        Order o = orderRepo.findById(orderId).orElseThrow();
        o.markPaid(paymentIntentId);
        orderRepo.save(o);
    }
}
```

Why a separate `@Service`: Spring's `@Transactional` works via proxy interception. If `markPending` and `markPaid` lived on `CheckoutService` itself, the calls from `checkout()` would be self-invocations and bypass the proxy — no transaction would begin. Moving them to `OrderTxService` forces the call through the proxy.

### 2. Idempotency + reconciliation — required, not optional

Splitting the transaction introduces a **crash window**: process can die between `PaymentIntent.create` succeeding and `markPaid` committing. Stripe charged the customer; your DB doesn't know. Two requirements:

- **Idempotency key on the Stripe call** (shown above — `order-<orderId>`). If the process crashes and the request retries, Stripe returns the existing `PaymentIntent` instead of charging twice.
- **Reconciliation job.** Periodic worker scans `Order` rows in `PENDING` state older than N minutes, calls `PaymentIntent.retrieve(idempotencyKeyDerivedFromOrderId)`, and resolves local state.

```java
@Scheduled(fixedDelay = 60_000)
public void reconcilePending() {
    List<Order> stuck = orderRepo.findPendingOlderThan(Duration.ofMinutes(5));
    for (Order o : stuck) {
        // Query Stripe by the idempotency-derived ID; resolve locally based on result
        ...
    }
}
```

Without this, the transaction split replaces a connection-pool leak with silent payment / DB divergence — strictly worse.

### 3. Defense-in-depth (apply regardless)

**HikariCP leak detection — leave it on in prod:**

```yaml
spring:
  datasource:
    hikari:
      leak-detection-threshold: 30000
      register-mbeans: true
```

**Postgres-side circuit breaker** — kills any future regression at the database before the pool exhausts:

```sql
ALTER ROLE app_user SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app_user SET statement_timeout = '15s';
```

`idle_in_transaction_session_timeout` is precisely the right tool for this leak shape. If the application ever holds a transaction open across an external call again, Postgres terminates the session, the client gets a clear error, the connection returns to the pool. It doesn't fix the bug — it prevents the cascade.

**CI guardrail — prevent the next instance** (ArchUnit rule):

```java
@ArchTest
static final ArchRule transactional_must_not_call_stripe = noMethods()
    .that().areAnnotatedWith(Transactional.class)
    .should().callMethodWhere(target(owner(assignableTo("com.stripe.net.ApiResource")
        .or(assignableTo("com.stripe.net.StripeResponseGetter"))
        .or(assignableTo("org.springframework.web.client.RestTemplate"))
        .or(assignableTo("org.springframework.web.reactive.function.client.WebClient"))
        .or(assignableTo("okhttp3.OkHttpClient")))))
    .because("DB connection must not be held across outbound HTTP calls");
```

---

## Anti-patterns I'm NOT recommending (and why)

You will be tempted by these. Don't.

- **Raise `maximumPoolSize` from 20 to 50.** Masks the leak. Slope is the same; alert fires later, bigger. Each leaked connection is an `idle in transaction` session on Postgres — that side gets worse too.
- **Wrap the Stripe call in `@Transactional(propagation = NOT_SUPPORTED)`.** Suspends the transaction but the outer transaction still holds a connection in some cases (depends on `TransactionManager` implementation). Cleaner to restructure the method, not annotate around it.
- **Async the Stripe call with `@Async` and `CompletableFuture` inside the `@Transactional` method.** Looks clever, isn't. The transaction commits before Stripe responds, but the DB connection in the outer call is still held until the `@Transactional` returns. And now you have a race between commit and payment-confirmation.
- **Lower `connectionTimeout` from 30s to 5s.** Makes the alert quieter (fails fast instead of waiting). Doesn't change the slope. User-visible 500s replace the original symptom.

---

## VERIFY

After deploying the fix, re-run the same triage commands. All four must hold simultaneously:

```sh
# 1. FD slope flat (was +N/min, must be ~0 within startup-churn noise)
kubectl exec -it <pod> -- sh -c 'for i in $(seq 1 10); do date +%T; ls /proc/1/fd | wc -l; sleep 30; done'
```

```sql
-- 2. No idle-in-transaction sessions older than a few seconds
SELECT count(*), max(now() - state_change) AS oldest
FROM pg_stat_activity
WHERE datname = '<your_db>' AND state = 'idle in transaction';
-- Expect: count low, oldest < 5s
```

```
# 3. MBean state — ActiveConnections oscillates, doesn't pin
ActiveConnections           oscillating, peak << 20
IdleConnections             > 0 most of the time
ThreadsAwaitingConnection   0
```

```
# 4. Five-restart smoke test on the same pod — FD returns to baseline between restarts
```

A reduced slope is **not** success — `+5/min` is still a leak, it just takes 8 hours instead of 1 to page someone. The slope must be flat.

Verify under realistic load (canary or staging mirror of prod traffic), not a unit test with mocked Stripe. The leak is dynamic; it only shows up under sustained traffic.

---

## Final report (paste into the incident channel)

```markdown
# Connection leak: @Transactional held across Stripe API call

## What was leaking
- Resource: PostgreSQL connections via HikariCP
- Library: HikariCP 5.x, Spring @Transactional
- Call site: CheckoutService.checkout(...) — Stripe PaymentIntent.create inside @Transactional
- Pattern: scope-too-wide (DB connection held across outbound HTTP call)

## Triage signature (before fix)
- Slope: <N> FDs/min over <T> minutes
- Dominant FD class: sockets to <postgres>:5432
- Confirming artifact: pg_stat_activity — 12 sessions idle-in-transaction 5+ min;
  HikariPool-1 connection timeout 30s

## Fix
- Split @Transactional method into two short transactions on a separate @Service
  (OrderTxService) — Stripe call sits between them with no DB connection held
- Added Stripe idempotency key derived from orderId
- Added reconciliation job for orders stuck PENDING > 5 min
- Enabled HikariCP leak-detection-threshold=30000
- Set Postgres idle_in_transaction_session_timeout=60s, statement_timeout=15s
- Added ArchUnit rule forbidding HTTP-client calls from @Transactional methods

[x] Close-on-every-path discipline (existing try-with-resources unchanged)
[x] Connection scope shrunk
[ ] Singleton client hoisted (StripeClient was already singleton)
[ ] Shutdown hook added (n/a)

## Verification (after fix)
- Slope: flat at ~<baseline> FDs (was +<N>/min)
- pg_stat_activity: 0 sessions idle-in-transaction > 5s
- HikariCP ActiveConnections: oscillating 2-8, never pins at 20
- ThreadsAwaitingConnection: 0 throughout
- Load profile: canary at 10% prod for 24h, then full rollout

## Watch list
- Metric: HikariCP ActiveConnections, pg_stat_activity idle-in-transaction count
- Watch window: 7 days post-deploy across one full weekly traffic cycle
- Alert: page if idle-in-transaction count > 3 OR ActiveConnections sustained > 15
```
