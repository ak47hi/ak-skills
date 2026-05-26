# Connection leak: gRPC `ManagedChannel` not shut down in `RichAsyncFunction.close()`

You've already given me the triage signature in prose — FD count steps up by ~60 per job restart on a TM, restart-correlated (not steady-state), and you've named the suspect (`RichAsyncFunction` + `ManagedChannelBuilder` in `open()`). That maps cleanly to the canonical Flink lifecycle-leak signature: `~60` is suspicious because `ManagedChannel` shutdown takes the channel + its Netty `EventLoopGroup` (boss + worker) + the gRPC name resolver + DNS executor with it; a single leaked channel routinely accounts for 40–80 FDs once you count the worker sockets, eventfd, and epoll FDs.

Walking through the phases.

---

## TRIAGE (confirm before fixing)

You've told me enough that I trust the leak is real, but capture the baseline number you'll later use to verify. Don't skip this — the verification step depends on a "before" measurement.

```sh
# 1. Identify a TM that has restarted a few times since fresh
kubectl get pod -l component=taskmanager

# 2. Sample FD count over 10 minutes — establish the steady-state slope
kubectl exec -it <tm-pod> -- sh -c 'while true; do
  echo "$(date +%s) fds=$(ls /proc/1/fd | wc -l)"
  sleep 60
done'

# 3. Classify FDs — confirm sockets are the dominant class, and they're going
#    to your gRPC service (not a Kafka broker, not the DB)
kubectl exec -it <tm-pod> -- sh -c '
  for fd in /proc/1/fd/*; do readlink "$fd"; done \
    | sort | uniq -c | sort -rn | head -20'

# 4. Resolve socket endpoints
kubectl exec -it <tm-pod> -- ss -tnp state established | awk "{print \$4, \$5}" | sort | uniq -c | sort -rn | head
```

Expected outcome here: dominant FD class is `socket:[...]`, and the top remote peer is your internal gRPC service. If anything else dominates (DB, Kafka, S3), STOP — the suspect you've identified is not the actual leak and you'll re-route after re-running step 3.

---

## ROUTE

Confirmed Flink TM lifecycle leak → `references/21-flink.md`. The "FD count steps up with restart count, baseline never returns" signature is exactly the lifecycle-cleanup-path leak.

---

## DIAGNOSE

### Source audit — what the symptom predicts

`ManagedChannelBuilder.forAddress(...).build()` in `open()` is fine. The bug is one or more of these in `close()`:

1. `close()` not overridden at all — the channel is never shut down.
2. `close()` overridden but only calls `super.close()` / does logging — channel orphaned.
3. `close()` calls `channel.shutdown()` but never `awaitTermination(...)` — `close()` returns before Netty's worker threads have actually released their sockets; Flink's task thread proceeds, the JVM keeps running (TM reused across restarts), and the half-shutdown channel keeps its FDs.
4. `close()` calls `shutdown()`, but an earlier `close()` statement threw, skipping it (the chained-close anti-pattern from the skill).
5. `RichAsyncFunction` specific: in-flight async requests holding references to the channel via futures. On `close()`, `shutdown()` waits politely; without `shutdownNow()` after a bounded `awaitTermination`, the channel never finishes terminating.

The `~60 FDs / restart` arithmetic suggests scenario 1 or 2 (channel fully orphaned) more than scenario 3 (partial cleanup). At parallelism > 1, every operator instance on the TM gets its own `open()` — so 60 FDs / (channel-FD-cost-per-instance) ≈ parallelism on that TM. Double-check by computing FD-delta divided by your operator parallelism on that TM:

```sh
# parallelism of the async operator on this TM
# (number of subtasks * approx FDs per channel ≈ 60)
```

Run this audit grep before reading code:

```sh
rg -n 'ManagedChannelBuilder|ManagedChannel\s' --type java --type kotlin
rg -n 'extends RichAsyncFunction' --type java --type kotlin -A 100 | rg -B 5 -A 5 'public void close|override fun close'
```

If `close()` doesn't appear, or appears without `channel.shutdown()` + `awaitTermination(...)` + `shutdownNow()`, that's your bug.

### Live diagnosis — prove it

Two probes, both fast, run them in parallel with the source audit:

**A. Thread leak across restarts (loudest signature).** gRPC's Netty event loops carry recognizable names — `grpc-default-worker-ELG-*`, `grpc-nio-worker-*`. Across N restarts you should see roughly N × parallelism of these threads accumulating:

```sh
kubectl exec -it <tm-pod> -- jstack 1 > /tmp/tm.stack
grep -E 'grpc-default-worker|grpc-nio-worker|grpc-default-executor' /tmp/tm.stack | wc -l
grep -E 'AsyncWaitOperator' /tmp/tm.stack -A 5
```

Cancel the job. Wait 30s. `jstack` again. If `grpc-*` thread count doesn't drop, the channel isn't shutting down.

Cross-check the metric: `flink_taskmanager_Status_JVM_Threads_Count` climbs across restarts, doesn't drop on cancel.

**B. Heap-dump confirmation (definitive).**

```sh
kubectl exec -it <tm-pod> -- jcmd 1 GC.heap_dump /tmp/tm.hprof
kubectl cp <tm-pod>:/tmp/tm.hprof ./tm.hprof
```

Open in MAT, search `io.grpc.internal.ManagedChannelImpl`. Instance count should equal (parallelism on this TM × number of distinct gRPC endpoints). If it's higher — that delta is the leak. Path-to-GC-roots on a leaked instance will show it's not held by your operator (which has been closed), but by the Netty `EventLoopGroup` it created in `open()`. That confirms the diagnosis: shutdown was never initiated.

You don't strictly need both probes — A is fast and conclusive enough to commit to the fix. B is for the verification record.

---

## FIX

The lifecycle template adapted to your case. Replace whatever `close()` (or absence of `close()`) you currently have with this:

```java
public class GrpcEnrichmentFn extends RichAsyncFunction<In, Out> {
    private static final Logger LOG = LoggerFactory.getLogger(GrpcEnrichmentFn.class);

    private final String target;
    private transient ManagedChannel channel;
    private transient MyServiceGrpc.MyServiceFutureStub stub;
    private transient ConcurrentMap<In, ListenableFuture<?>> inFlight;
    private volatile boolean closed = false;

    public GrpcEnrichmentFn(String target) { this.target = target; }

    @Override
    public void open(Configuration parameters) {
        channel = ManagedChannelBuilder.forAddress(host, port)
            .usePlaintext()              // or .useTransportSecurity()
            .keepAliveTime(30, TimeUnit.SECONDS)
            .keepAliveTimeout(10, TimeUnit.SECONDS)
            .build();
        stub = MyServiceGrpc.newFutureStub(channel);
        inFlight = new ConcurrentHashMap<>();
    }

    @Override
    public void asyncInvoke(In in, ResultFuture<Out> rf) {
        ListenableFuture<Response> f = stub
            .withDeadlineAfter(2, TimeUnit.SECONDS)
            .doLookup(toRequest(in));
        inFlight.put(in, f);
        Futures.addCallback(f, new FutureCallback<>() {
            @Override public void onSuccess(Response r) {
                inFlight.remove(in);
                rf.complete(List.of(toOut(r)));
            }
            @Override public void onFailure(Throwable t) {
                inFlight.remove(in);
                rf.completeExceptionally(t);
            }
        }, MoreExecutors.directExecutor());
    }

    @Override
    public void timeout(In in, ResultFuture<Out> rf) {
        // Critical: cancel the in-flight RPC so the socket returns to the channel pool.
        // Without this, the gRPC client keeps the call alive until its own deadline,
        // long past the Flink timeout — sockets accumulate.
        ListenableFuture<?> f = inFlight.remove(in);
        if (f != null) f.cancel(true);
        rf.complete(List.of());
    }

    @Override
    public void close() throws Exception {
        if (closed) return;       // idempotent — Flink may call close() twice on some failure paths
        closed = true;
        Throwable first = null;
        try {
            if (inFlight != null) {
                inFlight.values().forEach(f -> f.cancel(true));
                inFlight.clear();
            }
        } catch (Throwable t) { first = t; }
        try {
            if (channel != null) {
                channel.shutdown();
                if (!channel.awaitTermination(5, TimeUnit.SECONDS)) {
                    LOG.warn("gRPC channel did not terminate in 5s, forcing");
                    channel.shutdownNow();
                    channel.awaitTermination(2, TimeUnit.SECONDS);
                }
            }
        } catch (Throwable t) {
            if (first == null) first = t; else first.addSuppressed(t);
        }
        try { super.close(); } catch (Throwable t) {
            if (first == null) first = t; else first.addSuppressed(t);
        }
        if (first != null) throw new Exception(first);
    }
}
```

Four things this is doing that your current code almost certainly isn't:

1. **`shutdown()` + bounded `awaitTermination()` + `shutdownNow()` fallback.** `shutdown()` alone is non-blocking; `close()` returns and Flink moves on while Netty workers still hold sockets. The bounded wait + force-kill is what actually releases FDs synchronously.
2. **`closed` guard for idempotency.** Flink calls `close()` twice in some failure-during-cancel paths; the second call must be a no-op, not throw.
3. **`timeout()` cancels the in-flight `ListenableFuture`.** Without this, an Async timeout silently leaves the gRPC call running until its own deadline — the underlying HTTP/2 stream and its socket don't return to the pool.
4. **Suppressed-exception chaining.** If `inFlight.cancel` somehow throws (it shouldn't, but be safe), we still attempt `channel.shutdown()` and `super.close()` — and we surface all failures, not just the first.

### If parallelism × channels-per-TM is wasteful

Your problem is a leak, not a sizing concern, so fix the leak first. But once it's fixed, if you observe (via the heap dump) that you have parallelism=16 × 16 `ManagedChannel` instances on a TM — that's 16× the Netty workers and DNS resolvers, all warmed up to the same endpoint. The ref-counted channel registry pattern in `references/21-flink.md` § "Ref-counted channel registry per TM" consolidates to one channel per (TM, endpoint), with last-`release()` triggering shutdown. Trade-off: static state outlives the operator. Apply only if you measure the duplication actually mattering.

---

## VERIFY

Don't ship to prod until you've done the 5-restart loop on a staging TM. This is the only test that catches lifecycle leaks; unit tests won't.

### Production-shape verification

```sh
TM_POD=<your-tm-pod>

for i in 1 2 3 4 5; do
  echo "=== restart $i ==="
  PRE=$(kubectl exec $TM_POD -- ls /proc/1/fd | wc -l)
  flink cancel <job-id>
  sleep 30
  POST_CANCEL=$(kubectl exec $TM_POD -- ls /proc/1/fd | wc -l)
  flink run <jar> ...
  sleep 60
  POST_START=$(kubectl exec $TM_POD -- ls /proc/1/fd | wc -l)
  echo "pre=$PRE  post-cancel=$POST_CANCEL  post-start=$POST_START  delta=$((POST_START-PRE))"
done
```

Pass criteria:
- `post-cancel` returns to within ~10 FDs of `pre` on every iteration (some startup churn from JIT, logging, metric reporters is normal).
- `post-start - pre` is roughly constant across iterations 2–5 (not stepping up).
- Total drift across 5 restarts: less than 30 FDs.

Fail criteria (leak not fully fixed):
- `post-cancel > pre + 30` on any iteration → channel still not shutting down on cancel.
- Drift across 5 restarts > 50 FDs → there's a *second* leak; re-run TRIAGE and re-classify FDs.

### CI regression test (so this doesn't come back)

Add a harness-level test that loops `open()` / `close()` 50 times and asserts FDs returned to baseline. The math is forgiving — 50 leaked channels would show as ~3000 FDs; the assertion only needs to catch order-of-magnitude:

```java
@Test
void operator_close_releases_grpc_channel_fds() throws Exception {
    assumeTrue(Files.exists(Paths.get("/proc/self/fd")), "Linux-only: requires /proc");

    GrpcEnrichmentFn fn = new GrpcEnrichmentFn("localhost:" + fakeGrpcServer.getPort());
    int beforeFds = countOpenFds();

    for (int i = 0; i < 50; i++) {
        fn.open(new Configuration());
        fn.close();
    }
    Thread.sleep(2000);  // let Netty's awaitTermination drain non-daemon workers

    int afterFds = countOpenFds();
    assertThat(afterFds - beforeFds).isLessThan(20);
}

private static int countOpenFds() throws IOException {
    try (Stream<Path> s = Files.list(Paths.get("/proc/self/fd"))) {
        return (int) s.count();
    }
}
```

Gate with `assumeTrue` so non-Linux CI agents skip cleanly. Add this test for every operator that allocates a connection in `open()` — not just this one.

### Watch list (post-deploy)

- **Metric:** `process_open_fds` on each TM, alongside `flink_taskmanager_Status_JVM_Threads_Count`.
- **Window:** one full traffic-cycle + 3 redeploys (≈ 24h given your ~3 redeploys/day cadence).
- **Alert:** if FD slope > 1 FD/min sustained over 30 min, re-fire. The pre-fix slope was effectively `+60 FDs / 8h ≈ 0.12/min` averaged, but step-shaped — alert on slope, not just absolute value.
- **Anti-mitigation to refuse:** if FDs creep again, don't raise the 65k limit. Re-run TRIAGE; the dominant FD class may have shifted, meaning there's a *second* leak (sometimes a JDBC sink, sometimes a Kafka producer in a custom serializer) that was previously dwarfed by the gRPC one.

---

## One-liner summary for the on-call doc

> `GrpcEnrichmentFn extends RichAsyncFunction` allocated a `ManagedChannel` in `open()` but never called `shutdown()` + `awaitTermination()` in `close()`. Every job restart on a reused TM JVM orphaned ~60 FDs (the channel's Netty `EventLoopGroup` workers and HTTP/2 sockets per operator instance). Fix: implement idempotent `close()` with bounded shutdown + `shutdownNow()` fallback + cancel in-flight futures + cancel on `timeout()`. Verify: 5× restart loop on a TM pod with `ls /proc/1/fd | wc -l` showing flat baseline.
