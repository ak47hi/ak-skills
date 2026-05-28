# Reactor service leaking sockets — diagnosis walkthrough

You have a 12-hour FD slope (800 → 3500 = ~3.75 FDs/min, monotonic). That's a leak, not contention. Before touching code, run TRIAGE on the pod to **classify** what's leaking and **where** — "reactor service" is ambiguous (Spring WebFlux / Reactor Netty `WebClient` is the strong prior, but it could also be a JDBC pool inside a Spring Boot service, or a `ManagedChannel` constructed per request). The triage commands disambiguate in under 5 minutes.

---

## Phase 1 — TRIAGE (run these now)

### 1a. Confirm slope is still climbing and capture baseline

```sh
kubectl exec -it <pod> -- sh -c 'ls /proc/1/fd | wc -l; cat /proc/1/limits | grep "open files"'
kubectl exec -it <pod> -- sh -c 'for i in $(seq 1 10); do ls /proc/1/fd | wc -l; sleep 30; done'
```

Expect ~3500 climbing by 1-2 FDs every 30s under prod load. **Write that slope down** — it's the number you'll compare against after the fix. A fix that drops the slope from +3.75/min to +0.5/min is still a leak; only flat counts as fixed.

### 1b. Classify the FDs (this is the decisive command)

```sh
kubectl exec -it <pod> -- sh -c 'ls -l /proc/1/fd | awk "{print \$11}" | cut -d: -f1 | sort | uniq -c | sort -rn'
```

You're looking for the dominant kernel type. For a Spring Boot reactor service, the most informative outcomes:

| Dominant class | Meaning |
|---|---|
| `socket` overwhelmingly + `anon_inode` (epoll) climbing | HTTP / gRPC / WebClient leak — most likely given "reactor service" |
| `socket` to ports 5432/3306/1521/1433 | JDBC — Hikari / R2DBC pool leak; route to JDBC reference instead |
| Mixed sockets across many distinct remotes + climbing `anon_inode` | Per-client construction — each new client brings its own event loop |

### 1c. Remote endpoints — one upstream or many?

```sh
kubectl exec -it <pod> -- ss -tn state established | awk 'NR>1 {print $5}' | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -20
```

- **One remote dominates** → per-request body leak to that upstream (you're not closing the response body on some branch).
- **Many remotes, ~similar counts** → per-request **client** construction (each call site builds a new `WebClient` / `HttpClient` / `ManagedChannel`).

### 1d. CLOSE_WAIT count — the WebFlux tell

```sh
kubectl exec -it <pod> -- ss -tn state close-wait | wc -l
```

If this is large and climbing, the **remote** closed the connection but your app never called close. With Reactor Netty `WebClient` this almost always means an `exchangeToMono` branch never released the body (or `bodyToMono(Void.class)` was used on a non-empty response and the bytes never drained).

### 1e. Tool inventory

```sh
kubectl exec -it <pod> -- sh -c 'which jcmd jstack jmap; ls /tmp/async-profiler* 2>/dev/null'
```

If async-profiler isn't on the image (most JVM images don't ship it), sideload it:

```sh
kubectl cp async-profiler-3.0-linux-x64.tar.gz <pod>:/tmp/
kubectl exec -it <pod> -- tar -xzf /tmp/async-profiler-3.0-linux-x64.tar.gz -C /tmp/
```

Worst case (no `SYS_PTRACE`): heap dump and analyze offline.

```sh
kubectl exec -it <pod> -- jcmd 1 GC.heap_dump /tmp/h.hprof
kubectl cp <pod>:/tmp/h.hprof ./h.hprof
```

### What to record before moving on

```
LEAK CONFIRMED
  Slope:       ~3.75 FDs/min (800 → 3500 over 12h)
  Dominant:    <fill in from 1b — expect 'socket' + 'anon_inode'>
  Top remote:  <fill in from 1c>
  CLOSE_WAIT:  <fill in from 1d>
  Toolchain:   jcmd / jstack / jmap [+ async-profiler sideloaded]
  Route:       references/22-http-grpc.md (HTTP/WebClient) — most likely
```

If 1b shows DB ports dominant, stop reading this response and route to JDBC instead. The rest of this assumes sockets to non-DB remotes — the reactor-service shape.

---

## Phase 2 — DIAGNOSE (source audit + live, in parallel)

Run both at the same time. Source alone gives you suspects but not the offender; live alone tells you the symptom but not the call site. The intersection is the bug.

### 2a. Source audit — three greps that catch ~all WebFlux leaks

```sh
# (1) Per-request WebClient construction. Each WebClient.create() gets its
#     own ConnectionProvider (default 500 conns). One per request = pool leak per call.
rg -n 'WebClient\.create\(' --type java --type kotlin

# (2) exchangeToMono / exchange — response body is NOT auto-released.
#     Every branch must call .releaseBody(), .body(...), or .toBodilessEntity().
rg -n '\.exchangeToMono\(|\.exchangeToFlux\(|\.exchange\(\)' --type java --type kotlin

# (3) bodyToMono(Void.class) on a non-empty response — bytes never drained,
#     connection stuck checked-out.
rg -n '\.bodyToMono\(Void\.class\)' --type java --type kotlin
```

Also worth a look:

```sh
# Per-request OkHttp / Apache HC / gRPC channel construction (anti-pattern)
rg -n 'new OkHttpClient\(\)|HttpClients\.createDefault|ManagedChannelBuilder\.forAddress' --type java
```

Any hit inside a `@Service` method body, controller, or handler — as opposed to a `@Bean` / `@PostConstruct` / constructor — is a suspect.

### 2b. Live diagnosis — which suspect is the actual offender?

**Per-client vs per-request — heap dump + MAT.** This is the decisive test for WebFlux.

```sh
kubectl exec -it <pod> -- jcmd 1 GC.heap_dump /tmp/h.hprof
kubectl cp <pod>:/tmp/h.hprof ./h.hprof
```

In Eclipse MAT, count instances of:

| Class | Expected count | What "too many" means |
|---|---|---|
| `reactor.netty.resources.PooledConnectionProvider` | 1 per upstream service (usually 1-5) | per-request `WebClient.create()` |
| `reactor.netty.http.client.HttpClient` | 1 per upstream service | per-request WebClient construction |
| `io.netty.channel.nio.NioEventLoopGroup` | exactly 1 process-wide | each WebClient brought its own event loop — almost always a bug |
| `okhttp3.OkHttpClient` | 1 (or 1 per upstream) | per-request `new OkHttpClient()` |
| `io.grpc.internal.ManagedChannelImpl` | 1 per upstream gRPC service | per-request channel |

If counts are huge → **per-client leak**; fix is hoist to singleton + add `@PreDestroy`. If counts are correct but FDs grow → **per-request body leak**; fix is close discipline on every `exchangeToMono` branch.

**Turn on Netty paranoid leak detector** to get the exact stack:

```
-Dio.netty.leakDetectionLevel=paranoid
```

(Add to JVM args, redeploy one pod, wait a few minutes under load.) You'll get log lines like:

```
LEAK: ByteBuf.release() was not called before it's garbage-collected.
Recent access records:
  #1: io.netty.handler.codec.http.DefaultHttpContent.<init>(...)
     <YOUR application stack frame here>
```

The application stack frame is the offending call site. **Disable paranoid mode after diagnosis** — the overhead matters in steady state.

**async-profiler allocation site for sockets** (if you sideloaded it):

```sh
kubectl exec -it <pod> -- /tmp/async-profiler-3.0/bin/asprof \
  -e java.net.Socket.<init>,sun.nio.ch.SocketChannelImpl.<init>,io.netty.channel.AbstractChannel.<init> \
  -d 60 -f /tmp/sockets.html 1
kubectl cp <pod>:/tmp/sockets.html ./sockets.html
```

The dominant stack in the flame graph is the call site allocating sockets faster than they're closing.

---

## Phase 3 — FIX

Pick the pattern that matches what you found in 2a+2b. The vast majority of "reactor service" socket leaks land in one of these two patterns.

### Pattern A — per-client leak (`WebClient.create()` inside a method)

**Symptom:** MAT shows hundreds/thousands of `PooledConnectionProvider`. CLOSE_WAIT is moderate. Sockets span many remotes.

```java
// BEFORE — leak. Each call constructs a new WebClient + ConnectionProvider + EventLoopGroup.
@Service
public class EnrichmentClient {
    public Mono<Enrichment> fetch(String id) {
        WebClient client = WebClient.create("https://enrichment.internal");
        return client.get().uri("/v1/users/{id}", id)
            .retrieve()
            .bodyToMono(Enrichment.class);
    }
}
```

```java
// AFTER — singleton WebClient injected from the auto-configured Builder,
// with bounded pool + observable acquire timeout.
@Service
public class EnrichmentClient {
    private final WebClient client;

    public EnrichmentClient(WebClient.Builder builder) {
        ConnectionProvider pool = ConnectionProvider.builder("enrichment")
            .maxConnections(100)
            .pendingAcquireMaxCount(500)
            .pendingAcquireTimeout(Duration.ofSeconds(2))
            .maxIdleTime(Duration.ofSeconds(30))   // must be < upstream idle killer
            .build();

        this.client = builder
            .baseUrl("https://enrichment.internal")
            .clientConnector(new ReactorClientHttpConnector(
                HttpClient.create(pool)
                    .responseTimeout(Duration.ofSeconds(5))))
            .build();
    }

    public Mono<Enrichment> fetch(String id) {
        return client.get()
            .uri("/v1/users/{id}", id)
            .retrieve()                                  // auto-releases on terminal signal
            .bodyToMono(Enrichment.class);
    }
}
```

`maxConnections` + `pendingAcquireTimeout` is the load-bearing pair: a slow upstream now produces `PoolAcquirePendingLimitException` you can alert on, instead of a creeping leak.

### Pattern B — per-request body leak (`exchangeToMono` branch doesn't release)

**Symptom:** MAT shows correct singleton counts. CLOSE_WAIT climbs in lockstep with request volume. Sockets concentrated on a single remote.

```java
// BEFORE — happy path consumes body; error branch never releases.
client.get().uri(uri)
    .exchangeToMono(resp -> {
        if (resp.statusCode().is2xxSuccessful()) {
            return resp.bodyToMono(Enrichment.class);
        }
        return Mono.error(new EnrichmentException(resp.statusCode()));  // body leaked
    });
```

```java
// AFTER — releaseBody() drains and releases on every non-consuming branch.
client.get().uri(uri)
    .exchangeToMono(resp -> {
        if (resp.statusCode().is2xxSuccessful()) {
            return resp.bodyToMono(Enrichment.class);
        }
        return resp.releaseBody()
            .then(Mono.error(new EnrichmentException(resp.statusCode())));
    });
```

**Better, when you don't need conditional body handling — use `.retrieve()`** (auto-releases on terminal signal, including cancel):

```java
client.get().uri(uri)
    .retrieve()
    .onStatus(HttpStatusCode::isError, r -> Mono.error(new EnrichmentException(r.statusCode())))
    .bodyToMono(Enrichment.class);
```

For "I only need the status, not the body":

```java
client.head().uri(uri)
    .retrieve()
    .toBodilessEntity()        // explicitly drains + releases
    .map(ResponseEntity::getStatusCode);
```

### Pattern C — `bodyToMono(Void.class)` on a non-empty response

```java
// BEFORE — Reactor Netty can't return the connection to the pool until
// response bytes are drained. Void.class skips reading them.
client.post().uri(uri).bodyValue(payload)
    .retrieve()
    .bodyToMono(Void.class);

// AFTER — toBodilessEntity drains the response stream then releases.
client.post().uri(uri).bodyValue(payload)
    .retrieve()
    .toBodilessEntity()
    .then();
```

### Pattern D — `.subscribe()` with no error handler on a `.retrieve()` chain

If the subscription is cancelled before a terminal signal arrives, the connection state can stay ambiguous. Always provide both consumer and error handlers, or use `Mono.fromFuture` / `subscribeOn`/`subscribe(...)` with explicit error handling. Better: don't bury a `.subscribe()` inside request flow — return the `Mono` to the framework.

### Shutdown hook (if you built any client manually)

```java
@PreDestroy
public void shutdown() {
    // For WebClient backed by HttpClient with a custom ConnectionProvider:
    pool.dispose();
}
```

The injected `WebClient.Builder` from Spring Boot is auto-disposed at context shutdown, but custom-built `ConnectionProvider`s are not — dispose them yourself.

---

## Phase 4 — VERIFY

Deploy to a single canary pod or staging under the same load profile that produced the original alert.

### 4a. FD slope must be flat, not just lower

```sh
kubectl exec -it <canary-pod> -- sh -c 'for i in $(seq 1 20); do ls /proc/1/fd | wc -l; sleep 30; done'
```

Compare against the original 3.75 FD/min. Slope must oscillate around a steady state, not climb. A reduced slope is still a leak — it just runs out of FDs more slowly and pages someone on a different night.

### 4b. CLOSE_WAIT should drop to ~0

```sh
kubectl exec -it <canary-pod> -- ss -tn state close-wait | wc -l
```

Residual CLOSE_WAIT after the fix means there's still a missing close somewhere. Re-enter DIAGNOSE.

### 4c. Heap dump — singleton counts (only if you applied Pattern A)

```sh
kubectl exec -it <canary-pod> -- jcmd 1 GC.heap_dump /tmp/after.hprof
kubectl cp <canary-pod>:/tmp/after.hprof ./after.hprof
```

In MAT:

```
reactor.netty.resources.PooledConnectionProvider:  <should equal N upstream services, usually 1-5>
reactor.netty.http.client.HttpClient:              <same>
io.netty.channel.nio.NioEventLoopGroup:            1
```

Record the delta in the fix report — e.g. "Before: 1,247 `PooledConnectionProvider`; After: 1." That delta is what proves the per-client construction has stopped.

### 4d. Watch list (for on-call after deploy)

| Metric | Watch window | Re-fire alert if |
|---|---|---|
| `process_open_fds{pod=~"reactor-service-.*"}` | 24h | slope > +1 FD/min sustained over 1h |
| `reactor_netty_connection_provider_active_connections` | 24h | active count == `maxConnections` for >5 min (= pool exhaustion, separate issue) |
| `reactor_netty_connection_provider_pending_acquire` | 24h | non-zero pending sustained — backpressure / slow upstream |
| `ss -tn state close-wait` (or `node_netstat_Tcp_*`) | 24h | sustained > 50 |

---

## What NOT to do

- **Don't raise `ulimit -n` / the K8s FD limit "to buy time."** That masks the leak; alert fires later but bigger. The limit is a circuit breaker, not a fix.
- **Don't raise the WebClient `ConnectionProvider.maxConnections` to "give it more headroom."** Unbounded growth is the leak; the pool size is irrelevant.
- **Don't restart the pod on a cron as a workaround.** It hides the slope from monitoring and the next on-call person inherits an undocumented bug.
- **Don't trust a fix verified only in unit tests.** Leaks are dynamic; only steady-state load exposes them. Verify on a canary under real traffic.
- **Don't catch and swallow `dispose()` / `close()` exceptions.** Looks defensive, actually leaves the resource in a half-open state.

---

## TL;DR for the runbook

1. `ls /proc/1/fd | wc -l` over 5 minutes — confirm slope is still ~3.75/min.
2. `ls -l /proc/1/fd | awk '{print $11}' | cut -d: -f1 | sort | uniq -c` — confirm sockets dominate.
3. `ss -tn state close-wait | wc -l` — if growing, it's a body-release leak (Pattern B). If flat but sockets span many remotes, it's per-client construction (Pattern A).
4. `rg -n 'WebClient\.create\(|\.exchangeToMono\(|\.bodyToMono\(Void\.class\)'` — find suspect call sites.
5. Heap dump + MAT — count `PooledConnectionProvider`. Anything > N upstream services means Pattern A.
6. Apply the matching fix. Singleton via `WebClient.Builder` or `releaseBody()` on every exchange branch.
7. Canary deploy. Re-sample slope for 30+ min under prod load. Flat = fixed. Lower-but-climbing = not fixed.
