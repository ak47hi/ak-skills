# Anti-patterns

Walk this list when proposing a fix, and call out the anti-pattern explicitly if the user is asking for one. These are not refusals — they're prompts to push back before applying a "fix" that masks the real bug.

## Universal

### "Just raise the pool size" / "Just raise `ulimit -n`"

Symptom: user proposes (or has already applied) raising `maximumPoolSize`, OS FD limit, or K8s pod FD limit to suppress the alert.

Why it's bad: the slope is the leak. Raising the ceiling buys time before the next exhaustion event, but the curve still slopes up — the alert will fire again, later, bigger. Worse, the higher ceiling masks the leak in monitoring (the dashboard now looks "fine" at higher steady state) until the system actually exhausts the new limit.

When it's defensible: as a **temporary mitigation** while the fix is being developed, with an explicit ticket and a date for revisiting. Never as a final answer.

Push back with: "The FD slope is +N/min. Doubling the limit gives you 2× as long before exhaustion, not a fix. Let's find the leak; here's the triage command."

### Mocking the leak in tests

Symptom: leak verification proposed via a unit test with a mocked `HttpClient` / `ManagedChannel` / `DataSource`.

Why it's bad: leaks are dynamic; the bug shows up under load when GC isn't catching up. A mocked test confirms the close was called once on the happy path, but the leak is almost always on an exception path or under concurrent contention that the mock doesn't reproduce.

Push back with: run the fix under realistic load in a staging or canary deployment, sample the FD slope, and prove it's flat. That's the verification — not a unit test.

### Catching and swallowing `close()` exceptions

Symptom: `try { x.close(); } catch (Exception ignored) {}` on a resource that might be in a half-state.

Why it's bad: swallowing the close exception loses the signal that the resource is corrupted. The next use of the resource finds it in a broken half-state and produces a worse error (or worse, succeeds against a half-closed connection with corrupt state).

Better: log the exception with the resource identity at WARN level; for chained closes, use the suppressed-exception pattern (`first.addSuppressed(t)`) so the first failure is preserved and the rest are still recorded.

### Per-request long-lived clients

Symptom: `new OkHttpClient()`, `new HttpClient(CIO)`, `requests.Session()`, `httpx.AsyncClient()`, `ManagedChannelBuilder.forAddress(...)`, `aiohttp.ClientSession()`, `grpc.aio.insecure_channel(...)` constructed inside a request handler.

Why it's bad: each construction allocates a connection pool, a dispatcher executor, a DNS cache, and (for gRPC/Netty) an event loop group. None of these are cheap. Per-request construction leaks all of them — usually they're not closed, and even if they were, the construction cost itself is significant.

Fix: hoist to a per-process singleton (or per-upstream-service for gRPC channels). See `references/22-http-grpc.md` § "Singleton clients".

---

## JDBC-specific

### `@Transactional` on a private method or self-invocation

Symptom: a `private` or same-class method annotated with `@Transactional` does nothing — Spring's proxy interception only fires on calls **through the proxy**, which only happens on cross-object calls.

Why it's bad: connection is acquired by the underlying DAO without proxy-managed close timing. The transaction never begins; the autocommit semantics may leave statements with no explicit transaction boundary. Connection-holding becomes uncoordinated.

Fix: move the `@Transactional` method to a separate `@Service` and call it through the proxy, or use Spring's `TransactionTemplate` programmatically.

### `try { ... } finally { conn.close(); }` instead of try-with-resources

Symptom: a plain `finally` close instead of try-with-resources.

Why it's bad:

- `close()` itself can throw, masking the real exception from the try block.
- Any `Statement` / `ResultSet` declared in the try is not closed unless they also have their own nested try/finally — which nobody writes.
- The cleanup ordering is wrong: try-with-resources closes in reverse declaration order; manual finally closes in source order, which fights JDBC's required reverse-close discipline.

Fix: try-with-resources is mandatory for JDBC. There's no good reason to use plain finally.

### `Connection` stored as an instance field

Symptom: `private Connection conn;` on a service class.

Why it's bad: the connection's lifecycle is now tied to the service object's lifecycle, not to the unit of work. Connection escapes the transaction scope, gets shared across threads (data race), and isn't released back to the pool until the service is GC'd.

Fix: store the `DataSource` as a field; obtain a `Connection` per unit of work via try-with-resources.

### Holding a connection across an outbound HTTP call

Symptom: code that loads data via JDBC, calls an external service, then writes back via JDBC, all inside one `try (Connection c = ...)`.

Why it's bad: the connection is held during network I/O of unknown duration. The DB sees a long-running idle-in-transaction; the pool depletes; other workers block on `getConnection()`.

Fix: split into two short transactions, with the HTTP call in between. See `references/20-jdbc.md` § "Shrink the connection scope".

---

## Flink-specific

### `open()` without symmetric `close()`

Symptom: a `RichFunction` overrides `open()` and allocates resources but doesn't override `close()`.

Why it's bad: Flink calls `close()` on graceful shutdown. Without it, every job restart on the same TM JVM leaks the resources from the previous attempt.

Fix: every `open()` needs a matching `close()` that releases everything `open()` allocated, in reverse order, with suppressed-exception chaining.

### Sharing operator state via a `static` field

Symptom: operator instances communicate via a `static` field or a `static` singleton.

Why it's bad: violates Flink's operator-lifecycle contract. If the operator is removed from a savepoint restore, the static reference still holds it, leaking the entire object graph. Also breaks parallelism — operator instances share state they shouldn't.

Fix: use Flink state (`ValueState`, `MapState`, broadcast state). If shared cross-instance state is genuinely required, document the trade-off and the manual cleanup path.

### Hand-rolled `RichSinkFunction` instead of a built-in connector

Symptom: a hand-rolled `RichSinkFunction<Row>` writing to Postgres / Kafka / Elasticsearch.

Why it's bad: built-in connectors handle lifecycle, exactly-once semantics, and savepoint compatibility. Hand-rolled sinks are a leak source until proven otherwise — and they're almost never proven otherwise in code review.

Fix: prefer `JdbcSink.sink(...)`, `KafkaSink`, `Elasticsearch7SinkBuilder`, etc. Only roll your own if a built-in doesn't exist for your sink.

---

## HTTP / gRPC-specific

### Per-request `ManagedChannel` / `OkHttpClient`

Symptom: a `new ManagedChannelBuilder.forAddress(...).build()` inside a request handler or a `new OkHttpClient()` per call.

Why it's bad: each `ManagedChannel` has its own event-loop group (Netty), its own DNS resolution, its own LB policy state, its own subchannel pool. Each `OkHttpClient` has its own connection pool, dispatcher executor (with its own threads), and cache. Per-request construction leaks all of this on every call.

Fix: one `ManagedChannel` per upstream service, scoped to the process. One `OkHttpClient` per process, optionally per-upstream via `client.newBuilder().build()`.

### Abandoning a gRPC server-streaming call without cancel

Symptom: `Iterator<Response> it = stub.streamThings(req);` followed by an early return without draining or cancelling.

Why it's bad: the underlying HTTP/2 stream stays open until the server times out. Each channel has a finite stream concurrency limit (default 100); enough leaked streams and new RPCs block waiting for a slot.

Fix: use `Context.CancellableContext` and call `ctx.cancel(null)` in finally. See `references/22-http-grpc.md` § "Streaming RPCs".

### Reading `response.body().string()` and forgetting the response

Symptom: `String body = client.newCall(req).execute().body().string();` with no try-with-resources.

Why it's bad: on success, the body string is returned but the `Response` is held until GC. On any failure inside `.string()` (read error, encoding error), the `Response` is leaked.

Fix: always wrap the `Response` in try-with-resources, then call `.body().string()` inside.

### Bare `requests.get()` in a long-lived Python service

Symptom: `requests.get(url)` (no `Session`) called from inside a web handler or worker.

Why it's bad: each `requests.get` constructs a temporary `Session` with its own urllib3 connection pool. At process scale, the per-call pool construction leaks (it's released only on GC, which is non-deterministic under load).

Fix: a per-service `requests.Session()` held for the lifetime of the worker process.

### `grpc.insecure_channel(...)` relying on `__del__`

Symptom: per-request `grpc.insecure_channel(target)` without explicit `close()`.

Why it's bad: the sync gRPC API closes the channel only when `__del__` runs, which is non-deterministic under load. Under burst traffic, channels accumulate before GC catches up; FD count climbs.

Fix: explicit `channel.close()` in a try/finally, or hoist to a per-service singleton.

---

## Verification anti-patterns

### Declaring victory on a reduced slope

Symptom: "FD growth went from +50/min to +5/min — fixed."

Why it's bad: +5/min is still a leak. It just exhausts FDs after 8 hours instead of 1. The alert will return.

Push back with: the slope must be **flat** (within startup-churn noise), not just lower. If +5/min is the residual, there's still a leak — re-run DIAGNOSE and find the remaining offender.

### Verifying in a different environment than where the leak was reported

Symptom: leak reported in prod; fix verified in dev with no load.

Why it's bad: dev doesn't reproduce the leak in the first place (no sustained traffic) so "no leak observed" is meaningless. The slope is meaningful only under the same load profile that surfaced the original alert.

Fix: verify in canary or staging under realistic load, or in prod behind a flag.
