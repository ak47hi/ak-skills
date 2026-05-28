# Connection leak: Spring + OkHttp, slow FD growth to many remotes, CLOSE_WAIT flat

## Read the signature first

Your triage signature is doing most of the diagnostic work already. Let me restate it because it pins the diagnosis hard:

- **Slope:** ~2 FDs/min, ~120/hr, ~2,880/day. Slow but monotonic. That is a leak, not noise — a 2/hr or 5/hr Spring service running at modest QPS will hit the K8s default FD limit (often 65535, sometimes 1024) in days, not weeks.
- **All new sockets ESTABLISHED, many different remotes.** ESTABLISHED means the connections are live, both ends still think the socket is in use. The app is *holding* them, not failing to close after the peer hung up.
- **CLOSE_WAIT flat near zero.** This is the decisive tell. CLOSE_WAIT grows when the **remote** sent FIN and the **local app** never called `close()` on the response — the canonical per-request `Response`/`ResponseBody` leak. You don't have that.

ESTABLISHED to many remotes + flat CLOSE_WAIT + slow climb is the textbook **per-client construction leak**, not a per-request close leak. Each call site that says `new OkHttpClient()` builds its own:

- connection pool (5 idle conns per address, keepalive 5min default)
- dispatcher `ExecutorService` (cached threadpool, creates non-daemon threads)
- internal `RouteDatabase` + DNS cache

The pool keeps idle conns ESTABLISHED for ~5 minutes, then they should reap. They don't reap because the `OkHttpClient` itself is still strongly reachable (held by the caller, or never GC'd because of the dispatcher's non-daemon executor threads). The "many remotes" matches: it's not one upstream leaking, it's that *each call to a different upstream creates a fresh client* that retains a few connections.

The slow rate (~2/min) is consistent with this — only a fraction of requests construct a new client (e.g. one specific code path, one less-trafficked endpoint, or a scheduled job that fires every few seconds).

## Where to look — in this order

### 1. Find every `OkHttpClient` construction site

```sh
# in the repo
rg -n 'new OkHttpClient\(\)|OkHttpClient\.Builder\(\)\.build\(\)|new OkHttpClient\.Builder\(\)' --type java
rg -n 'OkHttpClient\(\)|OkHttpClient\.Builder\(\)' --type kotlin
```

Anything **inside a method body** (vs a `@Bean`, `static` field, or DI constructor injection) is the suspect set. Pay special attention to:

- Retrofit builders: `new Retrofit.Builder().client(new OkHttpClient())...` — the inner `new OkHttpClient()` is the leak, even though Retrofit itself is fine.
- Per-call interceptor wiring: code that calls `.newBuilder().addInterceptor(...).build()` per request *forks the client* but **does** share pool/dispatcher because of how `newBuilder()` works. That one's actually safe. Verify it's not just a `new OkHttpClient.Builder()` masquerading.
- AWS SDK / Stripe / Twilio / Datadog SDK wrappers that internally build their own OkHttp clients per service instance — if you instantiate one of *those* clients per request, you leak their OkHttp underneath.

### 2. Confirm in the live pod — heap-dump for instance counts

```sh
kubectl exec -it <pod> -- jcmd 1 GC.heap_dump /tmp/h.hprof
kubectl cp <pod>:/tmp/h.hprof ./h.hprof
```

Open in Eclipse MAT (or `jhat` / VisualVM), and run:

```
SELECT * FROM okhttp3.OkHttpClient
```

Or in MAT's Object Query Language:

```
SELECT COUNT(*) FROM okhttp3.OkHttpClient
SELECT COUNT(*) FROM okhttp3.ConnectionPool
SELECT COUNT(*) FROM okhttp3.Dispatcher
```

**Expected for a correctly-configured service:** 1 `OkHttpClient` per upstream service you intentionally talk to, usually 1–5 total in a Spring app.

**Leak shape:** hundreds or thousands, with `ConnectionPool` / `Dispatcher` counts matching.

Also count threads — OkHttp dispatcher threads are named `OkHttp <something>`:

```sh
kubectl exec -it <pod> -- jstack 1 | grep -c '"OkHttp '
```

A climbing thread count of `OkHttp Dispatcher` and `OkHttp ConnectionPool` threads confirms the per-client leak: each leaked client kept its non-daemon executor alive.

### 3. Confirm with the allocation profiler (optional but conclusive)

If async-profiler is available (or you can sideload it):

```sh
kubectl exec -it <pod> -- /tmp/async-profiler/bin/asprof \
  -e okhttp3.OkHttpClient.<init> \
  -d 120 -f /tmp/okhttp-alloc.html 1
kubectl cp <pod>:/tmp/okhttp-alloc.html ./okhttp-alloc.html
```

The dominant flame stack is the construction call site. If it's a `@Bean` or `@PostConstruct` and only fires once at startup — different problem. If it's a request handler, scheduled task, or feign/retrofit factory method — that's your leak.

If async-profiler isn't available, fall back to socket-allocation profiling:

```sh
asprof -e java.net.Socket.<init>,sun.nio.ch.SocketChannelImpl.<init> -d 60 -f /tmp/sockets.html 1
```

Stack should pass through `okhttp3.internal.connection.RealConnection` and back to the construction site.

## Fix

### Pattern — singleton `OkHttpClient` as a Spring bean

```java
@Configuration
public class HttpClientConfig {

    @Bean(destroyMethod = "")  // see note below — we handle shutdown manually
    public OkHttpClient okHttpClient() {
        Dispatcher dispatcher = new Dispatcher();
        dispatcher.setMaxRequests(200);
        dispatcher.setMaxRequestsPerHost(50);

        ConnectionPool pool = new ConnectionPool(
            /* maxIdleConnections */ 50,
            /* keepAliveDuration */ 5, TimeUnit.MINUTES);

        return new OkHttpClient.Builder()
            .dispatcher(dispatcher)
            .connectionPool(pool)
            .connectTimeout(Duration.ofSeconds(2))
            .readTimeout(Duration.ofSeconds(5))
            .callTimeout(Duration.ofSeconds(10))   // hard ceiling — important
            .retryOnConnectionFailure(true)
            .build();
    }
}
```

Inject it everywhere it's used:

```java
@Service
public class EnrichmentClient {
    private final OkHttpClient http;

    public EnrichmentClient(OkHttpClient http) {  // constructor injection
        this.http = http;
    }

    public String fetch(String id) throws IOException {
        Request req = new Request.Builder()
            .url("https://enrichment.internal/v1/users/" + id)
            .build();
        try (Response r = http.newCall(req).execute()) {   // try-with-resources
            if (!r.isSuccessful()) throw new IOException("status " + r.code());
            return r.body().string();
        }
    }
}
```

If you talk to multiple upstreams with different timeout/interceptor profiles, **use `.newBuilder()`** — it shares the pool and dispatcher across all forks, which is what you want:

```java
@Bean
public OkHttpClient slowUpstreamClient(OkHttpClient base) {
    return base.newBuilder()
        .readTimeout(Duration.ofSeconds(30))
        .addInterceptor(new SlowUpstreamAuthInterceptor())
        .build();
}
```

`newBuilder()` is the right way to "fork" a client for one upstream's needs without leaking a new pool.

### Shutdown hook

OkHttp's dispatcher threads are **non-daemon**. Without a teardown the JVM may stick around at process exit or fail health checks during pod termination. Add a `@PreDestroy`:

```java
@Component
public class OkHttpLifecycle {

    private final OkHttpClient http;

    public OkHttpLifecycle(OkHttpClient http) { this.http = http; }

    @PreDestroy
    public void shutdown() {
        http.dispatcher().executorService().shutdown();
        http.connectionPool().evictAll();
        try {
            http.cache().close();   // only if you configured a cache
        } catch (Exception ignored) {}
    }
}
```

(The `destroyMethod = ""` on the `@Bean` is because Spring's auto-detection of a `close` method on `OkHttpClient` is unreliable across versions; do the teardown explicitly.)

### Anti-patterns to grep for and remove

```java
// LEAK — new client per call
public String fetch(String url) {
    OkHttpClient client = new OkHttpClient();   // <-- this is the bug
    Request req = new Request.Builder().url(url).build();
    try (Response r = client.newCall(req).execute()) {
        return r.body().string();
    }
}

// LEAK — Retrofit factory called per call
public ThingApi thingApi() {
    return new Retrofit.Builder()
        .client(new OkHttpClient())             // <-- still the bug
        .baseUrl(...)
        .build()
        .create(ThingApi.class);
}

// LEAK — builder reconstructed for "customization" without newBuilder()
public OkHttpClient withInterceptor(Interceptor i) {
    return new OkHttpClient.Builder()           // <-- fresh client, fresh pool
        .addInterceptor(i)
        .build();
}
// FIX: base.newBuilder().addInterceptor(i).build()
```

### Don't do these

- **Don't raise the FD `ulimit`.** It hides the slope, doesn't fix it. At 2 FDs/min, raising the limit from 65535 to 1M just postpones the page by ~9 months — the leaked clients still pin non-daemon threads and the JVM will OOM (thread metaspace) before then.
- **Don't shrink OkHttp's idle pool to "expire faster".** It can mask the slope into noise but the clients are still pinned by their dispatcher threads.
- **Don't add a custom `Interceptor` that calls `response.close()`** — the response is already closed by your try-with-resources. Doing both can corrupt connection state on the retry path.

## Verification plan

Run *under the same load profile that produced the 2 FDs/min original slope*. Not a unit test, not a synthetic burst — the real production traffic mix (or as close as you can get in staging).

### 1. FD slope (same command as triage)

```sh
kubectl exec -it <pod> -- sh -c 'for i in $(seq 1 24); do echo "$(date +%s) $(ls /proc/1/fd | wc -l)"; sleep 300; done'
```

Run for 2 hours minimum, same as your original sample. **Pass criterion: slope flat, oscillating in a band, not climbing monotonically.** A slope of ~0 FDs/min is a fix. A slope of 0.5 FDs/min is still a leak — find the next caller.

### 2. Client instance count (the decisive check)

```sh
kubectl exec -it <pod> -- jcmd 1 GC.heap_dump /tmp/after.hprof
kubectl cp <pod>:/tmp/after.hprof ./after.hprof
```

In MAT:

```
SELECT COUNT(*) FROM okhttp3.OkHttpClient
SELECT COUNT(*) FROM okhttp3.ConnectionPool
SELECT COUNT(*) FROM okhttp3.Dispatcher
```

**Pass criterion:** counts match the number of intentional clients (usually 1, sometimes a small number if you `.newBuilder()` for different upstream profiles). If `ConnectionPool` count > `OkHttpClient` count, something is constructing pools directly — investigate.

### 3. Thread count for OkHttp executor threads

```sh
kubectl exec -it <pod> -- jstack 1 | grep -E '"OkHttp (Dispatcher|ConnectionPool)' | wc -l
```

**Pass criterion:** stays bounded under steady load. With one singleton client, you'll see at most `Dispatcher.maxRequests` (200 in the example above) active dispatcher threads under saturation, dropping to ~0 idle. Not "the count grows for 2 hours".

### 4. Socket count by remote

```sh
kubectl exec -it <pod> -- ss -tn state established | awk 'NR>1 {print $5}' | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -20
```

**Pass criterion:** the per-remote ESTABLISHED count stabilizes at ≤ `ConnectionPool.maxIdleConnections + concurrent in-flight to that remote`. If the count to any single remote is still climbing, you have a secondary leak — could be a separate client construction site, or a per-request `Response`-not-closed bug on top of the singleton fix.

### 5. CLOSE_WAIT (should remain ~0)

```sh
kubectl exec -it <pod> -- ss -tn state close-wait | wc -l
```

It was 0 before, should stay 0. A new CLOSE_WAIT count after the fix would indicate a fresh per-request close bug introduced by the refactor (e.g. you converted to a shared client but a code path now reads `response.body().string()` outside the try-with-resources).

## Watch list (post-deploy)

| Metric | Window | Alert |
|---|---|---|
| `process_open_fds{pod=~"<service>.*"}` | 7 days post-deploy | Page if slope > 0.5/min over 1h window |
| OkHttp `okhttp3.OkHttpClient` MAT count | One-time at 24h via on-demand heap dump | Investigate if > 2× expected client count |
| `jvm_threads_live{pod=...}` filtered to `OkHttp*` names | 7 days | Page if exceeds `maxRequests` for sustained 10m |
| CLOSE_WAIT count to known upstreams | 24h | Page if non-zero for 5m — would indicate a regression to a per-request leak |

## Summary

- **Diagnosis:** per-client `OkHttpClient` construction leak. Signature is unambiguous (ESTABLISHED to many remotes + flat CLOSE_WAIT + slow climb).
- **Fix:** singleton `OkHttpClient` as a Spring `@Bean`, injected by constructor; use `.newBuilder()` for per-upstream variants; `@PreDestroy` tears down the dispatcher executor and connection pool.
- **Proof:** MAT instance count drops from many to 1 (or the small expected number); FD slope goes flat; OkHttp thread count stabilizes.
- **Look first at:** every `new OkHttpClient(` and `new OkHttpClient.Builder(` in the codebase, plus any factory method that returns a Retrofit/Feign-style client. The slow rate suggests a less-trafficked code path — check scheduled jobs, admin endpoints, and SDK wrappers before assuming the hot path is the culprit.
