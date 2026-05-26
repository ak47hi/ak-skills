# Flink 1.18 lifecycle leaks

Apache Flink 1.18 on the Kubernetes Flink Operator. Java + Kotlin user functions; PyFlink covered briefly at the end. Assumes TRIAGE is done — leak is confirmed on a TaskManager (TM), not the JobManager.

Flink leaks are almost always **lifecycle bugs in operator code**: a resource opened in `open()` (or lazily on first record) and not released in `close()`.

The Flink runtime calls `close()` on graceful shutdown but **does not** call it on `cancel`, on TM kill, or on uncaught exceptions during checkpoint. Leaked resources from prior job attempts pile up across restarts on the same TM JVM when the TM is reused — that's the canonical "FDs step up with restart count" signature.

---

## Source-code audit

### `RichFunction.open` / `close` symmetry

Audit every subclass of `RichFunction`, `RichMapFunction`, `RichFlatMapFunction`, `KeyedProcessFunction`, `ProcessFunction`, `RichSinkFunction`, `RichAsyncFunction`, etc.

```sh
# List every Flink user function
rg -l 'extends Rich(Map|FlatMap|Filter|Sink|Source|Async)?Function|extends KeyedProcessFunction|extends ProcessFunction' --type java --type kotlin

# Functions that override open() but not close()
rg -l 'override fun open|public void open' --type java --type kotlin > /tmp/has_open.txt
rg -l 'override fun close|public void close' --type java --type kotlin > /tmp/has_close.txt
comm -23 <(sort /tmp/has_open.txt) <(sort /tmp/has_close.txt)
```

Any file that opens but does not close is a strong candidate.

For files with both, verify `close()` actually releases everything `open()` allocated. The pattern that bites:

```java
// LEAK - second resource leaks if first close() throws
@Override
public void close() throws Exception {
    httpClient.close();      // throws
    kafkaProducer.close();   // never runs
    super.close();
}

// CORRECT - chain via suppressed exceptions
@Override
public void close() throws Exception {
    Throwable first = null;
    try { httpClient.close(); } catch (Throwable t) { first = t; }
    try { kafkaProducer.close(); } catch (Throwable t) {
        if (first == null) first = t; else first.addSuppressed(t);
    }
    try { super.close(); } catch (Throwable t) {
        if (first == null) first = t; else first.addSuppressed(t);
    }
    if (first != null) throw new Exception(first);
}
```

For Kotlin, `runCatching` chained with `getOrElse` works equivalently, but the explicit pattern is clearer in operator code.

### Idempotency of `close()`

Flink can call `close()` multiple times in some failure paths. Make it safe:

```java
private volatile boolean closed = false;

@Override
public void close() throws Exception {
    if (closed) return;
    closed = true;
    // release...
}
```

Without this, the second call hits a half-disposed object and throws — which the caller treats as the resource failing to close, not as already-closed.

### Lazy initialization gotcha

Resources lazily initialized inside `processElement` and not in `open()` are easy to forget about in `close()`:

```sh
# fields assigned inside processElement are suspicious
rg -n 'this\.\w+\s*=' --type java -g '*RichFunction*' -g '*ProcessFunction*' | rg -v '@Override.*open'
```

If the field is assigned outside `open()`, search for it in `close()`.

### `RichAsyncFunction` and AsyncIO

`RichAsyncFunction` clients leak more often than synchronous ones because:

- The async client's lifecycle outlives a single `asyncInvoke` call by design.
- Failures from the async callback don't propagate through `close()` — exceptions in `ResultFuture.completeExceptionally` happen on a different thread.
- `AsyncDataStream.unorderedWait(... timeout, ...)` timeouts can leave in-flight requests dangling; their underlying connections may not return to the pool.

Audit:

- Client initialized in `open()`, closed in `close()`.
- **Timeout handler explicitly cancels the in-flight resource.** Override `timeout()`:

```java
@Override
public void timeout(IN input, ResultFuture<OUT> resultFuture) throws Exception {
    // cancel the underlying request — without this, the client may hold the socket
    // until its own timeout, far beyond the Flink timeout
    pendingRequests.get(input)?.cancel(true);
    resultFuture.complete(Collections.emptyList());
}
```

### Kafka producer / consumer lifecycle

Legacy `FlinkKafkaProducer` / `FlinkKafkaConsumer` are deprecated; `KafkaSink` and `KafkaSource` (1.14+) handle lifecycle for you. If the codebase still uses the legacy ones:

- Custom serializers/partitioners must not capture extra producers.
- `FlinkKafkaProducer` in `EXACTLY_ONCE` mode opens a transactional producer per checkpoint; aborted checkpoints can leave orphan producer IDs visible to the Kafka cluster (not the TM, but worth flagging — they consume `transactional.id` slots).

For new connectors:

- **Custom `KafkaRecordSerializationSchema` that wraps a `Producer`** (extra producer outside the connector) is a common leak source — that producer has no managed lifecycle. The connector doesn't know about it.

### JDBC sink (`JdbcSink`)

Built-in `JdbcSink.sink(...)` manages the connection. Custom `RichSinkFunction` writing to JDBC commonly leaks because:

- `Connection` opened in `open()`, used per-record, closed in `close()` — fine.
- `Connection` opened **per record** to handle reconnect — leaks if not closed on every error path.
- Connection pinned across job restarts because `close()` was missed during cancel.

Prefer `JdbcSink.exactlyOnceSink(...)` or wrap your own carefully:

```java
@Override
public void invoke(Row value, Context ctx) throws Exception {
    if (connection == null || connection.isClosed()) {
        connection = ds.getConnection();
        statement = connection.prepareStatement(SQL);
    }
    bind(statement, value);
    statement.executeUpdate();
}
```

The `executeUpdate` failure path **must not leave `connection` non-null and closed** — that creates a half-state where subsequent records think the connection exists. Set both to null in the catch.

Cross-reference: per-record JDBC discipline lives in `references/20-jdbc.md`.

### RocksDB iterators

Not network connections, but they consume FDs and pin RocksDB snapshots. RocksDB iterators are returned by Flink state APIs and **must be closed**.

```sh
rg -n '\.iterator\(\)' --type java --type kotlin -g '*ProcessFunction*' -g '*Operator*'
```

For state-backed iterators (`MapState.iterator()`, queryable state iterators), wrap in try-with-resources or `.use {}`. A long-lived iterator that survives a checkpoint has its underlying RocksDB snapshot pinned, blocking compaction — that shows up downstream as growing state size, not just FD count.

### PyFlink note

PyFlink user functions follow the same lifecycle (`open` / `close` on `MapFunction`, etc.). Audit Python code with the same open-without-close grep:

```sh
rg -n 'def open\(self' --type py -g '*flink*' -A 30 | rg -B 30 'def close\(self' | rg 'def open\(self' | wc -l
```

---

## Live diagnosis

### TaskManager metrics

If Prometheus is wired up, watch these per-TM:

| Metric | Leak signature |
|---|---|
| `flink_taskmanager_Status_JVM_Threads_Count` | rises across restarts |
| `flink_taskmanager_Status_JVM_Memory_Direct_Count` | rises with sockets (Netty) |
| `taskmanager_job_task_operator_currentOutputWatermark` | freezes mid-run |
| `flink_taskmanager_job_lastCheckpointDuration` | climbs steadily |
| `numRecordsOutPerSecond` | drops while inputs steady |

Climbing `Threads_Count` across job restarts on the same TM JVM = thread pool inside an operator never being shut down. This is the loudest signature for "the operator's `close()` doesn't release its `ExecutorService`."

### In-pod `jstack`

```sh
kubectl exec -it <tm-pod> -- jstack 1 > /tmp/tm.stack
```

Look for:

```sh
# operator threads still alive after job cancel
grep -E 'AsyncWaitOperator|StreamSink|Kafka.*Producer|HttpClient.*Pool' /tmp/tm.stack -A 5

# connection-pool threads — if a job is cancelled but these remain, the operator never closed its client
grep -E 'OkHttp ConnectionPool|HikariCP housekeeper|reactor-http-' /tmp/tm.stack
```

After running `cancel`, wait 30s, jstack again. Threads named after a connector or HTTP client that persist across the cancel are leaked from prior attempts.

### `/proc/1/fd` correlation with restart count

```sh
# track FD count alongside restart count over time
kubectl exec -it <tm-pod> -- sh -c 'while true; do
  echo "$(date +%s) fds=$(ls /proc/1/fd | wc -l)"
  sleep 60
done'
```

If FD count steps up with each job restart (visible from JobManager logs or `flink list`), the leak is in the cleanup path, not the steady-state path. This is the classic Flink lifecycle leak signature.

### async-profiler for allocation-site identification

To find what's allocating sockets:

```sh
kubectl exec -it <tm-pod> -- /tmp/async-profiler-3.0/bin/asprof \
  -e java.net.Socket.<init> -d 60 -f /tmp/sockets.html 1
kubectl cp <tm-pod>:/tmp/sockets.html ./sockets.html
```

Open the flame graph; the dominant stack is your culprit. For Netty leaks, profile `io.netty.channel.AbstractChannel.<init>` instead.

### Netty `ResourceLeakDetector`

Flink uses Netty internally and most HTTP clients in Flink jobs do too. Crank the detector to PARANOID temporarily:

```yaml
# flink-conf.yaml or env
env.java.opts.taskmanager: "-Dio.netty.leakDetectionLevel=paranoid"
```

PARANOID samples 100% of allocations and prints stack traces of leaked buffers. **Remove after diagnosis** — the overhead is significant in steady-state.

### Heap dump path

```sh
kubectl exec -it <tm-pod> -- jcmd 1 GC.heap_dump /tmp/tm.hprof
kubectl cp <tm-pod>:/tmp/tm.hprof ./tm.hprof
```

In MAT, run the leak suspects report. Then:

- **For HTTP/gRPC inside an operator:** search `OkHttpClient`, `HttpAsyncClient`, `ManagedChannelImpl`, `EventLoopGroup` instance counts. Counts greater than the number of currently running operator instances == leaked clients across restarts.
- **For RocksDB iterators:** search `RocksIterator`. If counts climb across checkpoints, you have an iterator leak — find the `MapState.iterator()` call site without a close.

---

## Fix patterns

### Lifecycle template (`RichAsyncFunction` with HTTP)

The canonical correct shape — covers open + idempotent close + timeout cancellation + thread-pool shutdown:

```java
public class MyEnrichmentFn extends RichAsyncFunction<In, Out> {
    private transient HttpClient client;
    private transient ConcurrentMap<In, CompletableFuture<?>> inFlight;
    private volatile boolean closed = false;

    @Override
    public void open(Configuration parameters) {
        client = HttpClient.newBuilder()
            .executor(Executors.newFixedThreadPool(8))
            .connectTimeout(Duration.ofSeconds(2))
            .build();
        inFlight = new ConcurrentHashMap<>();
    }

    @Override
    public void asyncInvoke(In in, ResultFuture<Out> rf) {
        CompletableFuture<Out> f = doRequest(in);
        inFlight.put(in, f);
        f.whenComplete((r, t) -> {
            inFlight.remove(in);
            if (t != null) rf.completeExceptionally(t);
            else rf.complete(List.of(r));
        });
    }

    @Override
    public void timeout(In in, ResultFuture<Out> rf) {
        CompletableFuture<?> f = inFlight.remove(in);
        if (f != null) f.cancel(true);
        rf.complete(List.of());
    }

    @Override
    public void close() throws Exception {
        if (closed) return;
        closed = true;
        try {
            inFlight.values().forEach(f -> f.cancel(true));
        } finally {
            // HttpClient in JDK 11+ has no close(); cast and shutdown executor instead
            if (client.executor().orElse(null) instanceof ExecutorService es) {
                es.shutdownNow();
                es.awaitTermination(5, TimeUnit.SECONDS);
            }
            super.close();
        }
    }
}
```

### Singleton clients across operator instances (caveat)

For operators running with parallelism > 1, each operator instance gets its own `open()` call and its own client. That's correct — one client per operator instance, not one per JVM. Sharing a client across operator instances via a `static` field works but breaks the operator-lifecycle contract; if the operator is removed from a savepoint restore, the static reference still holds it.

If memory pressure makes per-instance clients infeasible, document the trade-off; don't silently share state.

### Ref-counted channel registry per TM (sophistication option)

When the leaked resource is expensive (gRPC `ManagedChannel`, large HTTP connection pool, DB pool with warm connections), the "one per operator instance" rule multiplies cost by parallelism. A 16-parallel operator on a TM ends up with 16 `ManagedChannel`s, 16 sets of Netty workers, 16 DNS resolvers — wasteful and amplifies the blast radius of any leak.

Ref-counted singleton scoped to the TM JVM, keyed by endpoint:

```java
public final class GrpcChannelRegistry {
    private static final Map<String, Entry> CHANNELS = new HashMap<>();

    private static class Entry {
        final ManagedChannel channel;
        int refCount;
        Entry(ManagedChannel c) { this.channel = c; this.refCount = 0; }
    }

    public static synchronized ManagedChannel acquire(String key, Supplier<ManagedChannel> factory) {
        Entry e = CHANNELS.computeIfAbsent(key, k -> new Entry(factory.get()));
        e.refCount++;
        return e.channel;
    }

    public static synchronized void release(String key) throws InterruptedException {
        Entry e = CHANNELS.get(key);
        if (e == null) return;
        if (--e.refCount == 0) {
            CHANNELS.remove(key);
            e.channel.shutdown();
            if (!e.channel.awaitTermination(5, TimeUnit.SECONDS)) {
                e.channel.shutdownNow();
            }
        }
    }
}
```

`open()` does `acquire(endpoint, () -> ManagedChannelBuilder…build())`; `close()` does `release(endpoint)`. The last release shuts down the channel. Lifetime is bounded by live subtasks on the TM, not by JVM lifetime — so a missed `close()` in one subtask still gets cleaned up when the other subtasks release.

**Trade-off:** static state outlives the operator. If the operator is removed from a savepoint restore mid-flight, the registry still holds the entry — a tiny residual reference until the JVM exits. Acceptable for high-cost resources; overkill for cheap ones.

### Connector choice

Prefer first-class Flink connectors over hand-rolled `RichSinkFunction` writing to a database / HTTP service:

| What | Built-in connector |
|---|---|
| Kafka | `KafkaSink`, `KafkaSource` (1.14+) |
| JDBC | `JdbcSink.sink(...)`, `JdbcSink.exactlyOnceSink(...)` |
| Filesystem / S3 | `FileSink` |
| Cassandra | `CassandraSink` |
| Elasticsearch | `Elasticsearch7SinkBuilder` |

Built-in connectors handle the lifecycle. Hand-rolled sinks are a leak source until proven otherwise.

---

## Verification

After the fix:

1. **Restart the job 5 times in rapid succession on the same TM pod** (via `flink cancel` + redeploy, or by killing the JobManager).
2. Sample `/proc/1/fd | wc -l` between each restart.
3. The FD count should return to baseline after each cancel — **not step up**.

Sample verification capture:

```
Restart 1: pre=480, post-cancel=482, post-start=487
Restart 2: pre=487, post-cancel=487, post-start=490   ← baseline holding (3 FDs/restart is normal startup churn)
Restart 3: pre=490, post-cancel=489, post-start=491
Restart 4: pre=491, post-cancel=490, post-start=492
Restart 5: pre=492, post-cancel=491, post-start=493
```

vs. before the fix:

```
Restart 1: pre=480, post-cancel=520, post-start=540    ← +60 not released on cancel
Restart 2: pre=540, post-cancel=580, post-start=605
Restart 3: pre=605, ...  ← stepping up
```

The "baseline holding" vs "stepping up" distinction is the verification. A pre→post-cancel delta of < 10 FDs is acceptable startup churn; > 30 means the leak isn't fully fixed.

### Harness-level FD-delta regression test (CI catch)

The 5-restart loop is the production verification. The CI equivalent is a unit / harness test that loops `open()` → `processElement()` → `close()` 50 times and asserts the FD count returned to baseline. Catches the bug at PR-review time, forever:

```java
@Test
void operator_close_releases_all_fds() throws Exception {
    assumeTrue(Files.exists(Paths.get("/proc/self/fd")), "Linux-only: requires /proc");

    MyEnrichmentFn fn = new MyEnrichmentFn();
    int beforeFds = countOpenFds();

    for (int i = 0; i < 50; i++) {
        fn.open(new Configuration());
        // optional: drive a few asyncInvoke calls
        fn.close();
    }
    Thread.sleep(2000);  // let Netty's awaitTermination drain non-daemon workers

    int afterFds = countOpenFds();
    // Generous slack for JVM-side churn (JIT, GC, metric sampling).
    // 50 leaked channels would show as ~3000 FDs; the assertion only needs to catch order-of-magnitude.
    assertThat(afterFds - beforeFds).isLessThan(20);
}

private static int countOpenFds() throws IOException {
    try (Stream<Path> s = Files.list(Paths.get("/proc/self/fd"))) {
        return (int) s.count();
    }
}
```

Gate it with `assumeTrue` on `/proc` existence so macOS / Windows CI agents skip cleanly instead of failing. The test is fast (<5s); add it to every operator that allocates a connection in `open()`.
