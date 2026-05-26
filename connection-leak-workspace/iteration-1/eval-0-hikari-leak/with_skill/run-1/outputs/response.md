# Connection leak: HikariCP exhaustion from `@Transactional` wrapping a Stripe HTTP call

## What was leaking

- **Resource:** Postgres connections (held across blocking network I/O)
- **Library:** HikariCP 5.x + Spring `@Transactional`
- **Call site:** the handler whose `@Transactional` method calls Stripe in the middle. The transaction opens a Postgres session (the `BEGIN` is sent on first DB access), then the thread parks on the Stripe socket. Spring won't release the connection until the method returns — so the pool drains 1 connection per concurrent in-flight Stripe call, and Postgres sees each one as `idle in transaction`.
- **Pattern:** scope-too-wide. Not a missing `close()` — the connection is held correctly per Spring's contract; the contract is being abused.

This is a textbook diagnosis. You don't need to keep hunting — the smoking gun matches:

1. HikariCP `Connection is not available, request timed out after 30000ms` — pool exhausted.
2. `pg_stat_activity` shows ~12 sessions `idle in transaction` for 5+ minutes — server side confirms the app started transactions and walked away.
3. The handler has `@Transactional` wrapped around a Stripe API call. Stripe API p99 can be multi-second, and on network blips it'll wait for the JVM read timeout (default for most clients is well past 30s, sometimes infinite).

12 stuck sessions × Stripe call duration > pool capacity is exactly the math that pages you every few hours, not every minute. As traffic comes in waves, the pool occasionally drains faster than Stripe drains. Once `ActiveConnections == 20` and `ThreadsAwaitingConnection > 0`, the 30s `connectionTimeout` starts firing and every other request 500s until Stripe unblocks.

## Triage signature (before fix)

- **Slope:** episodic — not a monotonic FD climb, but `HikariCP.ActiveConnections` saturates at 20 every few hours and stays pinned until Stripe drains.
- **Dominant FD class:** sockets to `:5432` paired with sockets to Stripe's API endpoint (`api.stripe.com:443`). One-to-one correspondence is the tell.
- **Confirming artifact:** `pg_stat_activity` row — `state = 'idle in transaction'`, elapsed > 5min, `wait_event` typically `ClientRead` (Postgres is waiting on the client to send the next statement; the client is in `socketRead0` on Stripe).

If you want to nail the call site beyond reasonable doubt before deploying, run this from the pod — it'll print the exact thread holding the connection on the stack:

```sh
kubectl exec -it <pod> -- jstack 1 > /tmp/stack.txt
# threads parked in Stripe HTTP read while holding a Pg connection
grep -B 2 -A 30 'socketRead0\|sun.nio.ch.SocketChannelImpl.read' /tmp/stack.txt \
  | grep -B 20 -A 5 'PgConnection\|HikariProxyConnection\|TransactionAspectSupport'
```

You'll see a stack like:

```
"http-nio-8080-exec-7" #... waiting on condition
  at sun.nio.ch.SocketChannelImpl.read(...)             <- parked on Stripe
  at okhttp3.internal.connection.Exchange.readResponseHeaders(...)
  at com.stripe.net.HttpURLConnectionClient.request(...)
  at com.acme.PaymentService.charge(PaymentService.java:NNN)  <- your code
  at com.acme.PaymentService$$EnhancerBySpringCGLIB$$...      <- proxy
  at org.springframework.transaction.interceptor.TransactionInterceptor.invoke(...)
  ...
  - locked <0x...> (a org.postgresql.jdbc.PgConnection)       <- the held connection
```

That `PaymentService.java:NNN` is the offending site. Source-audit equivalent — grep for `@Transactional` methods that make outbound HTTP calls:

```sh
rg -nB 2 -A 30 '@Transactional' --type java | rg -B 30 'stripe|httpClient|restTemplate|webClient|okhttp'
```

## Fix

Move the Stripe call **out** of the transaction. The right shape is: read inputs from DB → commit → call Stripe → start a second transaction to record the result. Two short transactions instead of one long one. The connection is never held across the network I/O.

### Before (the leak)

```java
@Service
public class PaymentService {

    @Transactional
    public PaymentResult charge(long orderId, String idempotencyKey) {
        Order order = orderRepo.findById(orderId).orElseThrow();
        // *** Stripe call inside the transaction — connection pinned for the
        //     entire round-trip, including any retries / network stalls ***
        Charge charge = stripe.charges().create(
            ChargeCreateParams.builder()
                .setAmount(order.getAmountCents())
                .setCurrency(order.getCurrency())
                .setCustomer(order.getStripeCustomerId())
                .build(),
            RequestOptions.builder().setIdempotencyKey(idempotencyKey).build()
        );
        paymentRepo.save(new Payment(order.getId(), charge.getId(), charge.getStatus()));
        return PaymentResult.of(charge);
    }
}
```

### After (scope-shrunk, idempotent)

```java
@Service
public class PaymentService {

    private final OrderRepository orderRepo;
    private final PaymentRepository paymentRepo;
    private final StripeClient stripe;
    private final PaymentTxOps tx;   // see below — separate bean for tx boundaries

    public PaymentResult charge(long orderId, String idempotencyKey) {
        // Tx #1: read-only — load what we need, commit, release the connection.
        OrderSnapshot snap = tx.loadOrderSnapshot(orderId);

        // Network I/O OUTSIDE any transaction. No DB connection held here.
        // Idempotency key makes this safe to retry without double-charging.
        Charge charge = stripe.charges().create(
            ChargeCreateParams.builder()
                .setAmount(snap.amountCents())
                .setCurrency(snap.currency())
                .setCustomer(snap.stripeCustomerId())
                .build(),
            RequestOptions.builder().setIdempotencyKey(idempotencyKey).build()
        );

        // Tx #2: short write — record the Stripe outcome.
        tx.recordCharge(snap.orderId(), charge.getId(), charge.getStatus());
        return PaymentResult.of(charge);
    }
}

@Service
public class PaymentTxOps {

    private final OrderRepository orderRepo;
    private final PaymentRepository paymentRepo;

    // readOnly = true → Postgres opens a read-only tx; HikariCP returns the
    // connection on commit, not on method exit.
    @Transactional(readOnly = true, timeout = 5)
    public OrderSnapshot loadOrderSnapshot(long orderId) {
        Order o = orderRepo.findById(orderId).orElseThrow();
        return new OrderSnapshot(o.getId(), o.getAmountCents(),
                                 o.getCurrency(), o.getStripeCustomerId());
    }

    @Transactional(timeout = 5)
    public void recordCharge(long orderId, String stripeChargeId, String status) {
        paymentRepo.save(new Payment(orderId, stripeChargeId, status));
    }
}
```

Three reasons `PaymentTxOps` is a **separate** bean and not a private method on `PaymentService`:

1. **Spring proxy interception only fires on cross-bean calls.** `@Transactional` on a private method, or on a public method called via `this.foo()` from the same class, does nothing — the proxy is bypassed and you're back to a single ambient connection. This is the most common silent regression of this exact fix.
2. **`timeout = 5`** caps each leg at 5 seconds. If either transaction hangs (lock contention, etc.) you get an exception instead of a 30s pool timeout.
3. **`readOnly = true`** on the load lets Postgres skip MVCC bookkeeping it doesn't need, and makes the intent explicit — anyone reading this code knows that leg cannot write.

### Belt-and-braces: always-on leak detection

Add these to `application.yml` regardless. The cost is one stack trace in the log per leak event — cheap insurance against the next time this pattern slips in:

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20          # leave it; do NOT raise it as a "fix"
      connection-timeout: 30000
      leak-detection-threshold: 20000  # 20s — just above your longest legit tx
      register-mbeans: true            # so you can read ActiveConnections live
```

`leak-detection-threshold` will log the *thread stack* of any thread that holds a connection past 20s. If anyone re-introduces a long-held connection — Stripe or anything else — it'll page with the offending stack instead of a generic timeout.

### Stripe client timeouts (separate hygiene, do this anyway)

Even with the connection scope fixed, an unbounded Stripe call ties up an HTTP thread forever. The Java SDK defaults are usually sane but verify:

```java
Stripe.setConnectTimeout(5_000);   // ms
Stripe.setReadTimeout(15_000);     // ms — Stripe's own p99.9 is well under this
```

This is not part of the leak fix — it's so that when Stripe goes down, you fail fast instead of accumulating stuck HTTP threads.

### Cross-cutting patterns this touched

- [ ] Close-on-every-path discipline — not applicable; not a missing-close bug.
- [x] **Connection scope shrunk** — primary fix.
- [ ] Singleton client hoisted — not applicable.
- [ ] Shutdown hook added — not applicable.

## Verification (after fix)

Run all four checks under the **same load** that produced the original alert. A canary at 10–25% production traffic for one full traffic cycle is the right call here; mocked load won't reproduce Stripe latency variance.

1. **FD slope flat.** Sample over 5+ minutes:

   ```sh
   kubectl exec -it <pod> -- sh -c 'for i in $(seq 1 10); do ls /proc/1/fd | wc -l; sleep 30; done'
   ```

   Count should oscillate around steady-state, not climb. If it climbs, there's a second leak (was masked by the dominant one — re-route via TRIAGE).

2. **`pg_stat_activity` clean.** Re-run:

   ```sql
   SELECT pid, state, now() - state_change AS idle_for, query
   FROM pg_stat_activity
   WHERE state = 'idle in transaction'
     AND now() - state_change > interval '5 seconds';
   ```

   Expected: **zero rows**, or rows that disappear within a second. Anything held past 5s under canary load means the fix didn't land on every path — check for another `@Transactional` method that calls out, or `this.`-prefixed self-invocation that bypasses the proxy.

3. **HikariCP MBean oscillates.** Via `jmxterm` or any JMX client, watch `com.zaxxer.hikari:type=Pool (*)`:

   | Attribute | Pass condition |
   |---|---|
   | `ActiveConnections` | oscillates between ~0 and a small number (≪ 20) under load |
   | `IdleConnections` | replenishes promptly after bursts |
   | `ThreadsAwaitingConnection` | 0 the vast majority of the time |

4. **No `HikariPool-1 - Connection is not available` log lines** for the duration of the canary window.

If all four are clean for one full traffic cycle (typically 24h to cover the daily peak), promote the fix.

## Watch list

Over the next 24h after rollout:

- **Metric:** `HikariCP.ActiveConnections` (Micrometer publishes this if you have `spring-boot-starter-actuator`), and `process_open_fds{pod=~"<service>-.*"}` from kube-state-metrics.
- **Watch window:** 24h, must include one peak-traffic period.
- **Alert (re-fire):** `HikariCP.ActiveConnections > 15` for > 60s, OR any log line matching `Connection is not available, request timed out`.
- **Leak-detection-threshold trips:** any `Apparent connection leak detected` log line — investigate the stack immediately; this is now your tripwire for any regression of the same shape elsewhere in the codebase.

If a similar pattern shows up again in a different handler, the source-audit grep above will find it — consider running it in CI as a pre-merge check.
