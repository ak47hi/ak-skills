# JDBC / DB pool leaks

Java, Kotlin, Python. Assumes TRIAGE is done — leak is confirmed and the dominant FD class is sockets to a DB port.

Two paths run **in parallel**:

- **Source-code audit** finds candidates: missing-close patterns in the user code.
- **Live-process diagnosis** confirms which candidate is the actual offender.

Source-only over-reports (lots of code "could" leak that doesn't); live-only under-reports (the symptom is a held connection, not its source).

---

## Source-code audit

### Java — try-with-resources

Every `Connection`, `Statement`, `PreparedStatement`, `ResultSet` must be inside try-with-resources, or `close()` must run in a `finally` that handles exceptions in close itself.

Grep the anti-patterns:

```sh
# Connection obtained but not in a try-with-resources head
rg -n 'getConnection\(\)' --type java | rg -v 'try\s*\('

# Statement created without try-with-resources
rg -n '\.(prepareStatement|createStatement)\(' --type java -A 1 | rg -B 1 -v 'try\s*\('

# ResultSet not closed (rs not in a try head)
rg -n '\.executeQuery\(' --type java | rg -v 'try\s*\('
```

Also flag:

- **`Connection` stored as a field** — almost always wrong unless it's a pooled `DataSource` reference, not a `Connection`.
- **Method returns `Connection` to caller** — close ownership becomes ambiguous and gets dropped on exception paths.
- **`try { ... } finally { conn.close(); }`** without a nested try around the close itself — close can throw and mask the real exception; more importantly any prior `Statement`/`ResultSet` close is skipped.

Idiomatic:

```java
try (Connection c = ds.getConnection();
     PreparedStatement ps = c.prepareStatement(sql)) {
    ps.setLong(1, id);
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) { ... }
    }
}
```

### Kotlin — `.use { }`

`Closeable.use` is the equivalent of try-with-resources. Grep for connections obtained without it:

```sh
rg -n '\.connection\b|getConnection\(\)' --type kotlin | rg -v '\.use\s*\{'
rg -n 'prepareStatement|createStatement' --type kotlin | rg -v '\.use\s*\{'
```

Common Kotlin-specific bug: **`let` instead of `use`** — `let` does not close.

```kotlin
// LEAK
ds.connection.let { conn ->
    conn.prepareStatement(sql).executeQuery().let { rs ->
        while (rs.next()) { ... }
    }
}

// CORRECT
ds.connection.use { conn ->
    conn.prepareStatement(sql).use { ps ->
        ps.executeQuery().use { rs ->
            while (rs.next()) { ... }
        }
    }
}
```

**Coroutines + JDBC:** JDBC is blocking, so any suspending function that does JDBC work must dispatch to `Dispatchers.IO`, and the connection must not escape the coroutine scope. A connection captured by a `launch` that outlives the parent scope is a leak waiting to happen — confirm structured concurrency.

### Python — context managers

`psycopg2` / `psycopg3`:

```sh
rg -n 'psycopg2?\.connect|psycopg\.connect' | rg -v 'with\s'
rg -n '\.cursor\(\)' --type py | rg -v 'with\s'
```

`asyncpg`:

```sh
# acquire without a context manager
rg -n 'pool\.acquire\(\)' --type py | rg -v 'async with'
```

`SQLAlchemy`:

- Sessions must be closed. `Session()` constructed manually but never closed leaks the underlying connection back to the pool only on GC.
- `engine.connect()` outside a `with` block leaks.
- Watch for sessions stored on long-lived objects (request-scoped sessions stored on a singleton service).

```python
# LEAK
session = Session()
result = session.query(User).all()
return result   # session never closed; connection returns to pool only on GC

# CORRECT
with Session() as session:
    return session.query(User).all()

# OR for FastAPI-style dependency injection
def get_session():
    with Session() as s:
        yield s
```

`asyncpg` correct usage:

```python
async with pool.acquire() as conn:
    await conn.fetch("SELECT ...")
# connection released on exit, including exception paths
```

---

## Live-process diagnosis

### HikariCP MBeans (Java / Kotlin)

Enable JMX MBean registration and leak detection:

```yaml
# Spring Boot
spring.datasource.hikari.register-mbeans: true
spring.datasource.hikari.leak-detection-threshold: 30000  # 30s
```

Once enabled, leak detection logs a stack trace of the thread that acquired a connection and held it past the threshold — that stack is your culprit.

Read live pool state without a JMX client:

```sh
kubectl exec -it <pod> -- jcmd 1 ManagementAgent.start_local
kubectl exec -it <pod> -- jcmd 1 JFR.start name=hikari duration=2m settings=profile
# or pull MBean values via jmxterm
```

Key MBean attributes (`com.zaxxer.hikari:type=Pool (<name>)`):

| Attribute | Healthy | Leaking |
|---|---|---|
| `ActiveConnections` | oscillates around steady-state | climbs monotonically toward `maximumPoolSize` |
| `IdleConnections` | replenished after burst | drains and stays at 0 |
| `ThreadsAwaitingConnection` | mostly 0 | persistently > 0 |
| `TotalConnections` | == max once warmed | == max with all active |

If `ActiveConnections == maximumPoolSize` and `ThreadsAwaitingConnection > 0` for sustained periods, the pool is exhausted. Combine with leak-detection stack traces to pinpoint the holder.

### Server-side session inspection

**Postgres:**

```sql
SELECT pid, state, wait_event_type, wait_event, state_change,
       now() - state_change AS idle_for, query
FROM pg_stat_activity
WHERE datname = '<your_db>'
  AND state IN ('idle in transaction', 'idle')
ORDER BY state_change ASC;
```

Sessions stuck `idle in transaction` for many seconds are the smoking gun — application acquired a connection, started a transaction, then drifted off (waiting on an HTTP call, blocked on a lock, returned without commit/rollback).

**MySQL:**

```sql
SELECT id, user, host, db, command, time, state, info
FROM information_schema.processlist
WHERE command = 'Sleep' AND time > 30
ORDER BY time DESC;
```

### Thread state from the JVM side

```sh
kubectl exec -it <pod> -- jstack 1 > stack.txt

# threads blocked on getConnection
grep -B 2 -A 10 'HikariPool.*getConnection' stack.txt

# threads holding a connection (look for JDBC driver frames + application frame)
grep -B 2 -A 10 'PgConnection\|MysqlConnection' stack.txt
```

A thread parked deep inside an HTTP client call while holding a `PgConnection` reference on its stack is the canonical "long-running transaction" leak.

### Heap dump path (when leak detection threshold isn't enough)

```sh
kubectl exec -it <pod> -- jcmd 1 GC.heap_dump /tmp/heap.hprof
kubectl cp <pod>:/tmp/heap.hprof ./heap.hprof
```

In Eclipse MAT, run "Path to GC roots" on `HikariProxyConnection` instances. Filter for instances where the proxy is reachable from anything other than the pool itself — that path identifies the thread/object holding the leaked connection.

### Python live diagnosis

```sh
# socket count to DB
kubectl exec -it <pod> -- sh -c 'ss -tn | grep :5432 | wc -l'

# stack of every thread/coroutine
kubectl exec -it <pod> -- py-spy dump --pid 1
```

`py-spy dump` shows what every coroutine is waiting on. Look for coroutines parked inside an HTTP/IO call while holding an asyncpg connection or SQLAlchemy session — same pattern as the JVM side.

**SQLAlchemy connection accounting** — instrument checkouts to capture acquire stacks:

```python
from sqlalchemy import event
@event.listens_for(engine, "checkout")
def on_checkout(dbapi_conn, conn_record, conn_proxy):
    import traceback
    conn_record.info['stack'] = traceback.format_stack()
```

Then on a stuck pool, iterate `engine.pool.checkedout()` and print the stacks of who holds checked-out connections.

**asyncpg pool inspection:**

```python
print(pool._holders)  # list of holders
print(pool.get_size(), pool.get_idle_size())
```

---

## Fix patterns

### Shrink the connection scope (most common fix)

The most common JDBC "leak" isn't a missing `close()` — it's holding the connection for too long. A connection acquired inside an HTTP handler should not span an outbound HTTP call.

```java
// LEAK - holds DB connection across slow upstream call
try (Connection c = ds.getConnection()) {
    User u = loadUser(c, id);
    EnrichmentResponse er = httpClient.fetch(u);  // network I/O while holding DB conn
    saveEnrichment(c, er);
}

// FIX - two short transactions, no DB conn during HTTP I/O
User u;
try (Connection c = ds.getConnection()) { u = loadUser(c, id); }
EnrichmentResponse er = httpClient.fetch(u);
try (Connection c = ds.getConnection()) { saveEnrichment(c, er); }
```

### Pool sizing

Pool size larger than `(cores * 2) + effective_spindle_count` is rarely useful and often masks leaks. If raising `maximumPoolSize` "fixed" the symptom, the bug is still there. See `references/90-anti-patterns.md` for why this is a refusal-worthy fix in isolation.

### Idempotent transaction boundaries

Wrap with explicit `commit/rollback` in a finally; do not rely on autocommit semantics under exceptions.

### Java / Kotlin `@Transactional` pitfalls

- **`@Transactional` on a private method** or self-invocation does nothing — connection is acquired without proxy interception, so close timing is unmanaged.
- **`@Transactional(propagation = REQUIRES_NEW)` inside a loop** creates a new physical session per iteration. Often the leak is structural here.

### Add HikariCP leak detection (always, even in prod)

Set `spring.datasource.hikari.leak-detection-threshold` to a value just above the longest legitimate transaction duration (30s is a safe default for most services). The cost is one stack trace per leak event in the log — cheap insurance.

### Postgres-side guardrails (highest-leverage defense-in-depth)

Set these per role so the database itself aborts misbehaving sessions even when the application doesn't:

```sql
ALTER ROLE app_user SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app_user SET statement_timeout = '15s';
```

- `idle_in_transaction_session_timeout` kills sessions that have started a transaction but aren't running a statement. This is precisely the "transaction held across an outbound HTTP call" leak — Postgres terminates the session, the client gets a clear error, the connection returns to the pool. Set it tighter than your slowest legitimate transaction.
- `statement_timeout` caps individual statement duration. Doesn't directly address connection leaks but prevents a runaway query from holding a connection indefinitely.

These are server-side circuit breakers. They don't fix the application bug but they prevent the symptom (pool exhaustion under failure) from cascading.

### Idempotency for split-transaction fixes

When you apply the "shrink connection scope" fix and split a transaction around an external call (DB → HTTP → DB), you introduce a crash window between the two transactions. If the process dies between the HTTP success and the second transaction, the external side-effect happened but the database doesn't know it.

Two requirements:

1. **Idempotency key on the external call.** Stripe, Twilio, AWS SNS, internal APIs — all support an idempotency token. Pass one (derived from the unit-of-work id) so retries see the same outcome.
2. **Reconciliation job.** A periodic worker that scans `PENDING` rows older than N minutes, queries the external service by idempotency key, and resolves the local state. This handles the crash window the application can't.

This isn't optional for production payment / messaging flows. The transaction-split fix without idempotency replaces a connection-pool leak with silent data divergence — strictly worse.

### CI-level prevention (ArchUnit, lint)

Once you've fixed one instance of `@Transactional` calling out to an HTTP client, prevent the next one with a build-time check:

```java
// ArchUnit rule — fails the build if a @Transactional method calls a known HTTP-client class
ArchRuleDefinition.noMethods()
    .that().areAnnotatedWith(Transactional.class)
    .should().callMethodWhere(JavaCall.Predicates.target(HasOwner.Predicates.owner(
        JavaClass.Predicates.assignableTo("org.springframework.web.client.RestTemplate")
            .or(JavaClass.Predicates.assignableTo("org.springframework.web.reactive.function.client.WebClient"))
            .or(JavaClass.Predicates.assignableTo("okhttp3.OkHttpClient"))
            .or(JavaClass.Predicates.assignableTo("com.stripe.net.HttpClient")))))
    .check(allClassesInProject);
```

For Python: a pre-commit grep that rejects `requests.` / `aiohttp.` calls inside methods that take a SQLAlchemy `Session` parameter is a crude but effective equivalent.

---

## Verification

After the fix, sample the leak rate again with the TRIAGE step 1 method (`ls /proc/1/fd | wc -l` over 5 minutes minimum). The slope should be **flat**, not just lower.

Additional checks specific to JDBC:

- Server-side: re-run the `pg_stat_activity` query. No sessions should be `idle in transaction` for longer than a few seconds.
- MBean side: `ActiveConnections` should oscillate, not pin at `maximumPoolSize`.
- `ThreadsAwaitingConnection` should be 0 most of the time.

A successful fix shows all four (FD slope flat, no idle-in-transaction, `Active` oscillating, no waiters) simultaneously. If one is still bad, the leak is partial — re-run DIAGNOSE.
