# Flink 1.18 TM FD Leak — gRPC `ManagedChannel` in `RichAsyncFunction.open()`

You've already given me enough signal to name the bug with high confidence, but I'll walk the diagnosis the way I'd actually run it in production so the reasoning (and the evidence) is reproducible.

---

## 1. What the numbers tell us before we touch the cluster

> **+60 FDs per restart, 3 restarts/day, 65k cap, OOM-kill ~day 5.**

That's `~180 FD/day` → ~900 FDs by day 5 from this leak alone. That doesn't on its own explain hitting 65k; what it tells me is **the leak is per-restart, not per-record**. That's the single most diagnostic detail in the report.

- A per-record leak would scale with throughput and would have killed you in hours, not days.
- A per-checkpoint leak would correlate with checkpoint interval.
- A per-restart leak means: **something allocated at operator initialization is not being released at operator teardown.**

The number 60 is also meaningful. Netty's default `EventLoopGroup` uses `2 * NCPU` threads, and each `NioEventLoop` holds an epoll FD plus a wakeup eventfd, plus the channel sockets, plus the name resolver, plus the LB policy's subchannels. On a typical 8-vCore TM that adds up to roughly the right order of magnitude for one orphaned `ManagedChannel` per parallel subtask instance. If you have parallelism ~4-8 on this operator per TM, "~60 FDs" is exactly what one leaked `ManagedChannel` per subtask looks like.

So the working hypothesis before I even open a shell:

**The `ManagedChannel` created in `RichAsyncFunction.open()` is never `shutdown()`-ed in `close()`. On every job restart, Flink calls `open()` again on the new operator instance, but the JVM (and TM process) survives the restart, so the old channel — and its Netty threads, epoll FDs, sockets, and DNS resolver — leaks into the surviving TM process.**

That is the bug. Now let me prove it.

---

## 2. Diagnosis — confirm, don't assume

### 2.1 Confirm the FDs are sockets, not files or pipes

On a TM pod just before it gets close to the limit:

```bash
kubectl exec -it <tm-pod> -- bash -c '
  PID=$(pgrep -f TaskManagerRunner)
  echo "Total FDs: $(ls /proc/$PID/fd | wc -l)"
  ls -l /proc/$PID/fd | awk "{print \$NF}" | sed "s/\[.*\]//" | sort | uniq -c | sort -rn | head
'
```

What I expect to see:

- A large bucket of `socket:[...]` entries (the leaked gRPC sockets + half-open connections).
- A growing bucket of `anon_inode:[eventpoll]` and `anon_inode:[eventfd]` (Netty `NioEventLoop` instances — one epoll + one wakeup eventfd per event-loop thread).

If `eventpoll`/`eventfd` count grew by ~16-32 per restart and `socket:` grew by ~30, that's a Netty `EventLoopGroup` leak, which is exactly what an unclosed `ManagedChannel` produces.

If instead you see `pipe:` dominating, suspect a different leak (process forking, file handle from logging). The report says gRPC client, so I expect the socket+eventpoll pattern.

### 2.2 Confirm it's tied to restarts, not steady-state

Pull the FD count over time and overlay restart events:

```bash
# In TM pod, run this in a sidecar or via exec
while true; do
  echo "$(date -Iseconds) $(ls /proc/$(pgrep -f TaskManagerRunner)/fd | wc -l)"
  sleep 30
done
```

Plot that against `kubectl get events` and the JobManager log lines for `Restoring job` / `Job ... switched from state RESTARTING to RUNNING`. You should see **flat plateaus broken by ~60-FD step-ups exactly at restart timestamps**. That kills any hypothesis of a per-record or per-checkpoint leak.

### 2.3 Confirm with a JVM-level view

`lsof` and `/proc/<pid>/fd` are kernel-side. To prove which Java object is holding them, take a heap histogram on a leaky TM:

```bash
kubectl exec -it <tm-pod> -- bash -c '
  PID=$(pgrep -f TaskManagerRunner)
  jcmd $PID GC.class_histogram | head -40
'
```

Smoking guns to look for, **with counts > parallelism-per-TM**:

- `io.grpc.netty.shaded.io.grpc.netty.NettyChannelBuilder$NettyChannelTransportFactory`
- `io.grpc.internal.ManagedChannelImpl`
- `io.grpc.internal.ManagedChannelImpl$LbHelperImpl`
- `io.grpc.netty.shaded.io.netty.channel.nio.NioEventLoop`
- `io.grpc.netty.shaded.io.netty.util.concurrent.DefaultThreadFactory`

If `ManagedChannelImpl` instance count is, say, 16 when you have one operator subtask per TM and have restarted 16 times — you have a strict per-restart leak. Game over, that's your bug.

For extra confidence, a thread dump:

```bash
kubectl exec -it <tm-pod> -- jstack $(pgrep -f TaskManagerRunner) | grep -c "grpc-default-worker"
```

That count should equal `(restarts + 1) * default_worker_threads_per_channel`. If it does — it's leak-by-restart, not leak-by-anything-else.

### 2.4 Why `RichAsyncFunction` specifically

This is where the Flink-side mental model matters:

- `open(Configuration)` is called once **per operator subtask instance**, every time the operator is initialized — including after every restart.
- `close()` is called when the subtask is torn down. Flink **does** call `close()` on failure/restart in 1.18 (with caveats — `close()` on the *previous* operator instance runs as part of the cancellation/teardown path), but only if your code is in `close()`.
- If your `RichAsyncFunction` has no `close()` override, or has one that doesn't call `channel.shutdown()` + `channel.awaitTermination(...)`, the `ManagedChannel` becomes unreachable from your code but **its Netty event loop threads are non-daemon and keep the channel — and all its FDs — alive for the lifetime of the JVM.**

That's the killer. gRPC's shaded Netty threads are non-daemon, so GC will never collect the channel. Only `shutdown()`/`shutdownNow()` releases them.

There's a second, subtler variant of the same bug worth ruling out:

- Even with a correct `close()`, if `open()` does `ManagedChannelBuilder.forAddress(...).build()` and the channel build itself fails partway (DNS, TLS handshake init), you can leak the partially-constructed channel. Less likely here given the symptom is clean per-restart, but flag it.

### 2.5 Rule out the "wrong but innocent" candidates

Before declaring victory, exclude:

- **Logback / log4j rolling appender FDs.** Stable count, not per-restart. Discount.
- **RocksDB SST FDs.** Grows with state, not with restart count, and you'd see `.sst` paths in `/proc/<pid>/fd`. Discount.
- **Kafka client / FileSystem connectors.** Same — these usually leak per-checkpoint or per-task, not per full job restart, and Flink's own connectors clean up.
- **Metric reporters (Prometheus pushgateway, etc.).** Possible but rarely ~60 FDs.

The gRPC `ManagedChannel` is overwhelmingly the most likely culprit, and 2.3's heap histogram will confirm in one command.

---

## 3. The fix

Two things have to change. The first is mandatory; the second is a strong defense-in-depth.

### 3.1 Mandatory: close the channel in `close()`

```java
public class MyGrpcAsyncFunction extends RichAsyncFunction<In, Out> {

    // Marked transient: not part of operator state, recreated per open().
    private transient ManagedChannel channel;
    private transient MyServiceGrpc.MyServiceFutureStub stub;

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);

        this.channel = ManagedChannelBuilder
            .forAddress(host, port)
            .usePlaintext()                              // or TLS as appropriate
            .keepAliveTime(30, TimeUnit.SECONDS)
            .keepAliveTimeout(10, TimeUnit.SECONDS)
            .keepAliveWithoutCalls(true)
            // Bound the executor — do NOT let gRPC default to a cached
            // thread pool that grows unbounded under bursty async load.
            .executor(MoreExecutors.directExecutor())
            .build();

        this.stub = MyServiceGrpc.newFutureStub(channel);
    }

    @Override
    public void asyncInvoke(In input, ResultFuture<Out> resultFuture) {
        ListenableFuture<Reply> reply = stub
            .withDeadlineAfter(timeoutMs, TimeUnit.MILLISECONDS)
            .call(toRequest(input));

        Futures.addCallback(reply, new FutureCallback<Reply>() {
            @Override public void onSuccess(Reply r) {
                resultFuture.complete(Collections.singleton(toOut(r)));
            }
            @Override public void onFailure(Throwable t) {
                resultFuture.completeExceptionally(t);
            }
        }, MoreExecutors.directExecutor());
    }

    @Override
    public void close() throws Exception {
        try {
            if (channel != null) {
                channel.shutdown();
                if (!channel.awaitTermination(5, TimeUnit.SECONDS)) {
                    channel.shutdownNow();
                    channel.awaitTermination(2, TimeUnit.SECONDS);
                }
            }
        } finally {
            channel = null;
            stub = null;
            super.close();
        }
    }
}
```

Key points, beyond the obvious `shutdown()`:

- `shutdown()` is graceful (lets in-flight RPCs finish). `shutdownNow()` cancels them. You want graceful first, with a bounded wait, then forced. Don't block close() forever — Flink will hang the cancellation path and you'll get killed by the task cancellation watchdog (`task.cancellation.timeout`, default 3 minutes), which then masks the underlying bug in logs.
- `close()` should be **idempotent and exception-safe**. If `awaitTermination` throws `InterruptedException`, re-interrupt and continue to `shutdownNow()`. Never let `close()` throw past the `super.close()` for an unrelated reason — that'll suppress real errors.
- Channel reference set to `null` after close. Belt-and-braces against accidental reuse if anything in your code path re-enters.

### 3.2 Strongly recommended: one channel per TM, not per subtask

A `ManagedChannel` is **thread-safe and designed to be long-lived and shared**. If your operator has parallelism 8 on a TM, today you have 8 channels per TM — 8 sets of event loops, 8 DNS resolvers, 8 LB policies. That's wasteful and amplifies the leak's blast radius.

Share one channel per TM JVM via a reference-counted singleton:

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

Then `open()` does `acquire(endpoint, () -> ManagedChannelBuilder...build())` and `close()` does `release(endpoint)`. Now even if a single subtask's `close()` misfires, the channel survives only as long as some other subtask still holds it; the last release shuts it down. Lifetime is bounded by the number of live subtasks on the TM, not by JVM lifetime.

This is also better for your downstream service (fewer connections, fewer DNS lookups, better HTTP/2 stream multiplexing).

### 3.3 Hard cap on FDs as a safety net, not a fix

In your TM K8s spec:

```yaml
spec:
  template:
    spec:
      containers:
        - name: flink-main-container
          resources:
            limits:
              memory: ...
          # ulimit nofile via securityContext or initContainer
```

Don't raise the FD limit to mask this. **Lower** an alert on it. A FD alarm at e.g. 30k for a TM is a much better signal than discovering it at 65k via OOM-kill. Use `node_exporter` / `process_open_fds` from JVM Prometheus exporter to alert on slope, not just absolute value.

---

## 4. Verification plan

This is the part most engineers skip and then ship the same leak again six months later. Three layers:

### 4.1 Unit / harness test for the lifecycle

Use Flink's `OneInputStreamOperatorTestHarness` or for an async function, drive `open()` → process some elements → `close()` directly, in a loop:

```java
@Test
void channel_is_closed_when_operator_closes() throws Exception {
    MyGrpcAsyncFunction fn = new MyGrpcAsyncFunction(host, port);

    int beforeFds = currentProcessFdCount();
    for (int i = 0; i < 50; i++) {
        fn.open(new Configuration());
        // optional: fn.asyncInvoke(...) a couple of times
        fn.close();
    }
    // Allow Netty threads to actually exit
    Thread.sleep(2000);
    int afterFds = currentProcessFdCount();

    // Allow a small slack for JVM-side noise, but not 50 * 60.
    assertThat(afterFds - beforeFds).isLessThan(20);
}

private static int currentProcessFdCount() throws IOException {
    long pid = ProcessHandle.current().pid();
    try (Stream<Path> s = Files.list(Paths.get("/proc/" + pid + "/fd"))) {
        return (int) s.count();
    }
}
```

This catches the bug at PR-review time forever. It's Linux-only — gate it with `assumeTrue(Files.exists(Paths.get("/proc")))`.

### 4.2 Staging soak

Deploy the fix to staging. Drive 20 forced restarts in a row (`kubectl delete pod` the TM, or trigger a savepoint-restore cycle). Watch:

- FD count on the surviving TM (if you only restart the job): **flat across restarts** ± a small constant from JVM internals. That's the pass criterion. Anything > 5 FDs/restart is still leaking.
- `grpc-default-worker-*` thread count from `jstack`: should be **constant**, not growing.
- Heap histogram count of `ManagedChannelImpl`: should equal current subtasks-per-TM, not subtasks-per-TM × restarts.

### 4.3 Production canary + alerting

- Roll to one TM first (or one job). Watch FD slope for 24h. The pre-fix slope was ~180 FD/day from this leak; post-fix should be statistical noise.
- Add a Prometheus alert: `rate(process_open_fds[1h]) > 5` per TM, sustained for 6h. That's the long-term seatbelt — it'll catch the *next* version of this bug (Kafka admin client, HTTP client, JDBC pool, whatever) before it eats you again.
- Add a runbook entry pointing at this diagnosis sequence. The pattern (resource allocated in `open()`, not freed in `close()`) recurs in Flink for HTTP clients, Redis pools, file handles, DB connections. Same diagnosis, same fix shape.

---

## 5. Summary

- **Root cause:** `ManagedChannel` created in `RichAsyncFunction.open()` is never `shutdown()` in `close()`. Netty's non-daemon worker threads keep the channel, its sockets, and its epoll/eventfd FDs alive for the JVM's lifetime. Job restart re-runs `open()` on the *new* operator instance inside the *same surviving* TM JVM, so each restart strands one channel's worth of FDs (~60).
- **Fix:** add a `close()` that calls `channel.shutdown()` → `awaitTermination(5s)` → `shutdownNow()` as fallback. Strongly consider a per-TM ref-counted channel registry so you have one channel per JVM rather than one per subtask.
- **Verification:** harness-level repeated open/close loop with an FD-delta assertion; staging soak with 20 forced restarts; production canary with FD-slope alerting.
- **The detail that nailed the diagnosis:** "+60 FDs per restart" (not per record, not per checkpoint). That's the fingerprint of a per-operator-instance resource leak, and `ManagedChannel`'s shaded Netty pool fits the magnitude exactly.
