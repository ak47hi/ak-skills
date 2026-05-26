# Hikari connection leak — diagnosis and fix

You already have enough signal to call it: **you have a transaction-scoped connection leak caused by a blocking external HTTP call inside `@Transactional`.** Below is how I'd confirm it on the live pod, the fix, and how to make sure it never comes back.

## 1. What the symptoms tell us

- `HikariPool-1 - Connection is not available, request timed out after 30000ms` means Hikari's `connectionTimeout` (default 30s) elapsed with **no connection returned to the pool**. The pool is saturated.
- `maximumPoolSize: 20` and `pg_stat_activity` shows ~12 sessions in `idle in transaction` for 5+ minutes. "Idle in transaction" means: Postgres opened a transaction, ran at least one statement, and is now waiting for the client to send the next statement or COMMIT/ROLLBACK. The connection is checked out from Hikari, pinned to a thread, and that thread is doing something else — almost certainly blocked on I/O.
- 5+ minutes is way beyond any reasonable DB statement. It matches the latency profile of a hung external HTTP call (Stripe under retry, TLS handshake stall, no read timeout, etc.).
- "Every few hours" matches a slow leak: 20 - 12 = 8 connections still healthy now, but each Stripe blip pins one more until you fall off the cliff and `connectionTimeout` fires for unrelated requests.

The root cause is structural, not a tuning problem: **a `@Transactional` method is making a synchronous Stripe call between two DB statements.** While that HTTP call is in flight, the DB connection sits in `idle in transaction`, contributing nothing, blocking everyone.

## 2. Confirm it on the pod (5 minutes)

Get the offender's pid, query, and stack — three independent confirmations.

### 2a. Confirm from Postgres which queries are stuck

```sql
SELECT pid,
       usename,
       application_name,
       state,
       now() - xact_start    AS xact_age,
       now() - state_change  AS idle_age,
       wait_event_type,
       wait_event,
       left(query, 200)      AS last_query
FROM   pg_stat_activity
WHERE  state = 'idle in transaction'
ORDER  BY xact_age DESC;
```

What you're looking for:
- `last_query` will show the **last statement before the Stripe call** — e.g. `UPDATE payment SET status='PENDING' WHERE id=$1`. That pinpoints the `@Transactional` method.
- `xact_age` should be >5 min, `state = idle in transaction`, `wait_event = ClientRead` (Postgres is waiting for the JDBC driver to send the next command — driver is waiting for the app thread — app thread is in Stripe).

### 2b. Confirm from inside the pod which threads are stuck

```bash
kubectl exec -it <pod> -- bash
# find the Java pid
jps
# or:  pgrep -f java

# thread dump — do this 2-3 times, 10s apart, so you can see what's stuck vs transient
jcmd <pid> Thread.print > /tmp/td1.txt
sleep 10
jcmd <pid> Thread.print > /tmp/td2.txt
```

Grep the dumps:

```bash
grep -nE "Stripe|HttpClient|SocketRead|HikariProxyConnection|getConnection" /tmp/td1.txt
```

You should see ~12 threads parked in something like:

```
java.net.SocketInputStream.socketRead0 (Native Method)
...
com.stripe.net.LiveStripeResponseGetter.rawRequest(...)
...
com.example.payments.PaymentService.charge(PaymentService.java:NN)   <-- @Transactional method
...
org.springframework.transaction.interceptor.TransactionInterceptor.invoke(...)
```

Two facts to take away:
1. The `TransactionInterceptor` frame is **below** the Stripe frame — meaning the tx is open while the HTTP call is in flight. That's the leak.
2. Threads waiting on `getConnection` (Hikari pool exhausted) will appear in `HikariPool.getConnection` / `ConcurrentBag.borrow`. Those are *victims*, not the cause.

### 2c. Confirm from Hikari itself

If you have actuator on:

```bash
kubectl exec -it <pod> -- curl -s localhost:8080/actuator/metrics/hikaricp.connections.active
kubectl exec -it <pod> -- curl -s localhost:8080/actuator/metrics/hikaricp.connections.pending
```

`active` near 20, `pending` > 0 confirms saturation. Enable leak detection (see fix below) and Hikari itself will log the stack of the thread holding each connection.

## 3. The actual fix

### Principle

**A database transaction must never span an external network call.** Treat the DB transaction as a critical section: enter it, do DB work, commit, *then* call Stripe, *then* (if needed) open a second short transaction to record the result. This is the standard "do the side effect outside the transaction" pattern, and for payments specifically it pairs with an idempotency key so the second transaction can survive a crash.

### Anti-pattern (what you have)

```java
@Service
public class PaymentService {

    @Transactional
    public PaymentResult charge(ChargeRequest req) {
        Payment p = paymentRepo.findById(req.paymentId()).orElseThrow();
        p.setStatus(PENDING);
        paymentRepo.save(p);                           // tx now has writes, connection pinned

        Charge stripeCharge = stripe.charges().create( // <-- BLOCKING HTTP, tx still open
            Map.of("amount", p.getAmount(),
                   "currency", p.getCurrency()));

        p.setStatus(SUCCEEDED);
        p.setStripeChargeId(stripeCharge.getId());
        paymentRepo.save(p);
        return PaymentResult.of(p);
    }                                                  // commit here
}
```

### Fix (split the transaction around the Stripe call)

```java
@Service
public class PaymentService {

    private final PaymentRepository paymentRepo;
    private final StripeClient stripe;
    private final PaymentTxn txn; // self-injected helper, see below

    public PaymentResult charge(ChargeRequest req) {

        // 1. Short tx: reserve the payment row + persist an idempotency key.
        ReservedPayment reserved = txn.reserve(req);

        // 2. NO transaction here. Stripe call is bounded by HTTP timeouts,
        //    not by the DB connection.
        Charge stripeCharge;
        try {
            stripeCharge = stripe.charges().create(
                Map.of("amount", reserved.amount(),
                       "currency", reserved.currency()),
                RequestOptions.builder()
                    .setIdempotencyKey(reserved.idempotencyKey()) // critical
                    .build());
        } catch (StripeException e) {
            txn.markFailed(reserved.paymentId(), e.getCode());
            throw new ChargeFailedException(e);
        }

        // 3. Short tx: record the outcome.
        return txn.complete(reserved.paymentId(), stripeCharge.getId());
    }
}

@Component
class PaymentTxn {

    private final PaymentRepository paymentRepo;

    @Transactional
    public ReservedPayment reserve(ChargeRequest req) {
        Payment p = paymentRepo.findById(req.paymentId()).orElseThrow();
        if (p.getStatus() != NEW) {
            // idempotent re-entry; return existing reservation
            return ReservedPayment.from(p);
        }
        p.setStatus(PENDING);
        p.setIdempotencyKey(UUID.randomUUID().toString());
        paymentRepo.save(p);
        return ReservedPayment.from(p);
    }

    @Transactional
    public PaymentResult complete(long paymentId, String stripeChargeId) {
        Payment p = paymentRepo.findById(paymentId).orElseThrow();
        p.setStatus(SUCCEEDED);
        p.setStripeChargeId(stripeChargeId);
        paymentRepo.save(p);
        return PaymentResult.of(p);
    }

    @Transactional
    public void markFailed(long paymentId, String errorCode) {
        Payment p = paymentRepo.findById(paymentId).orElseThrow();
        p.setStatus(FAILED);
        p.setFailureCode(errorCode);
        paymentRepo.save(p);
    }
}
```

Two things to notice:

1. `PaymentTxn` is a **separate Spring bean**. Don't try to call `@Transactional` methods on `this` — Spring's proxy won't apply the transaction. Inject a sibling component (or self-inject, but a separate bean is cleaner here).
2. **The Stripe idempotency key is non-optional.** Once you split the transaction, a crash between steps 2 and 3 leaves a `PENDING` row with no recorded charge id. Retries that reuse the same idempotency key let Stripe return the original charge instead of double-charging. Add a reconciliation job that scans `PENDING` rows older than N minutes and queries Stripe by idempotency key to repair state.

### Defense-in-depth config — apply regardless of the fix

These don't fix the leak. They make the next leak loud and survivable.

`application.yml`:

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20
      connection-timeout: 10000        # fail fast (10s, not 30s) so callers see backpressure
      leak-detection-threshold: 20000  # log a stack trace if any conn is held >20s
      validation-timeout: 3000
      keepalive-time: 30000
      max-lifetime: 1800000            # 30m; less than any upstream idle killer

logging:
  level:
    com.zaxxer.hikari.pool.ProxyLeakTask: WARN
```

Stripe HTTP timeouts — set them explicitly so a Stripe stall can't outlive your DB statement timeout:

```java
RequestOptions.builder()
    .setConnectTimeout(2_000)
    .setReadTimeout(10_000)
    .build();
```

Postgres-side guardrail (per-role, so it can't escape):

```sql
ALTER ROLE app_user SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app_user SET statement_timeout = '15s';
```

That last one is the single highest-leverage change you can make today. It would have aborted these 5-minute idle-in-transaction sessions automatically and surfaced the bug months ago instead of letting it slowly poison the pool.

## 4. Verification plan

Order matters — verify the diagnosis first, then verify the fix, then verify it stays fixed.

1. **Reproduce locally / in staging.** With the unfixed code, point Stripe at a request-bin or a sleep-proxy that holds the connection open for 60s. Fire 25 concurrent charges against `maximumPoolSize: 20`. Confirm:
   - You see exactly the production error: `HikariPool-1 - Connection is not available, request timed out`.
   - `pg_stat_activity` shows 20 `idle in transaction` rows.
   - With `leak-detection-threshold` set, Hikari logs the stack trace of the leaking thread and it points at your `@Transactional` method.
   This proves the diagnosis before you ship anything.
2. **Apply the fix in a branch, re-run the same load test.** Expectations:
   - `pg_stat_activity` shows zero rows in `idle in transaction` even mid-test; transactions are sub-millisecond, only `active` or absent.
   - `hikaricp.connections.active` peaks well below 20 even with 25 concurrent callers, because connections are no longer pinned for the duration of Stripe.
   - Total request latency goes *up* slightly per call (two tiny tx instead of one) but throughput goes way up under contention.
3. **Idempotency / crash test.** Kill the pod between `reserve()` and `complete()`. Restart. Re-drive the same request. Confirm Stripe returns the original charge (idempotency key worked), the reconciliation job repairs the row, and you don't double-charge. This is the part people skip and regret.
4. **Add a regression guard.** Two cheap ones:
   - A unit/architecture test (ArchUnit) asserting no method annotated `@Transactional` calls anything in `com.stripe.*` or any class annotated `@ExternalApi`.
   - An alert on `pg_stat_activity` for `state = 'idle in transaction' AND now() - xact_start > '30 seconds'`. If this ever fires again, you'll know within a minute, not three hours.
5. **Ship to one pod, watch for one full traffic cycle.** Specifically watch `hikaricp.connections.pending` (should stay at 0), `hikaricp.connections.usage` percentile (p99 should drop sharply), and the count of `idle in transaction` sessions in Postgres (should be ~0). Then roll out.

## TL;DR

Your `@Transactional` method is holding a Postgres connection open across a synchronous Stripe call. Twelve hung Stripe calls = twelve pinned connections = pool exhausted = the 30s `connectionTimeout` for unrelated requests. Fix is structural: split the transaction so Stripe runs outside any tx, use a Stripe idempotency key plus a reconciliation job to handle the gap, and add `idle_in_transaction_session_timeout`, Hikari leak detection, and an ArchUnit rule so this can't silently come back.
