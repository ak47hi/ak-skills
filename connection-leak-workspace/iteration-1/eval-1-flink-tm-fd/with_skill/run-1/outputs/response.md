# Connection leak: TaskManager FDs step +60 per job restart from RichAsyncFunction gRPC channel

This is the canonical Flink lifecycle leak signature crossed with a gRPC `ManagedChannel` per-client leak. The step-up of ~60 FDs *per restart* (not per record, not per checkpoint) tells you exactly where to look: the `open()` allocates a channel, the TM JVM is reused across job restarts, and `close()` either isn't releasing the channel or isn't being called on the cancel path. Walking through it end-to-end.

---

## Phase 1 — TRIAGE (skip ahead since you already have the slope)

You already gave us the leak rate (~60 FDs/restart, ~180 FDs/day, 65k cap in ~5d). That matches the math, so the leak is real and we don't need a multi-minute sample to confirm. Two things still worth capturing **before you touch the code** so you have a before/after comparison:

```sh
# 1. Per-TM FD count at a known restart count
kubectl exec -it <tm-pod> -- sh -c 'echo "fds=$(ls /proc/1/fd | wc -l) restarts=$(cat /proc/1/status | grep -i threads)"'

# 2. Classify the FDs - confirm sockets dominate (vs. files / pipes)
kubectl exec -it <tm-pod> -- sh -c '
  ls -l /proc/1/fd | awk "{print \$NF}" | sed -E "s/\[.*\]//" |
  awk -F"->" "{print \$2}" | awk "{print \$1}" |
  sort | uniq -c | sort -rn | head
'

# 3. Confirm the sockets are pointing at the gRPC service, not Kafka/JM/checkpoint store
kubectl exec -it <tm-pod> -- ss -tn state established \
  | awk 'NR>1 {print $5}' | awk -F: '{print $1":"$2}' \
  | sort | uniq -c | sort -rn | head -20
```

Expected: many ESTABLISHED sockets to your internal gRPC service's port, plus a fan of `anon_inode` entries (epoll fds from leaked Netty `EventLoopGroup`s — each `ManagedChannel` brings one). The 60-FD step matches roughly: ~8 worker threads × (1 epoll + 1 wakeup pipe + sockets) + a handful of HTTP/2 sockets ≈ 50–70.

## Phase 2 — ROUTE

Two domains overlap here. Per the routing rules, **start with the outer lifecycle** — `references/21-flink.md` — because the operator's `close()` is the right place to release the channel regardless of what's wrong inside gRPC. Cross-reference the gRPC singleton/shutdown patterns from `references/22-http-grpc.md`.

## Phase 3 — DIAGNOSE

Run the source audit and live probes in parallel — either alone is unreliable. Source finds *candidates*, live confirms *the offender*.

### Source audit — what to grep

```sh
# 1. Every RichAsyncFunction in the repo
rg -l 'extends RichAsyncFunction' --type java --type kotlin

# 2. Functions that override open() but not close() — the smoking gun
rg -l 'public void open|override fun open'  --type java --type kotlin | sort > /tmp/has_open.txt
rg -l 'public void close|override fun close' --type java --type kotlin | sort > /tmp/has_close.txt
comm -23 /tmp/has_open.txt /tmp/has_close.txt

# 3. Every gRPC channel construction site
rg -n 'ManagedChannelBuilder\.forAddress|NettyChannelBuilder\.forAddress' --type java --type kotlin

# 4. Channel shutdown sites — there should be one per construction site
rg -n '\.shutdown\(\)|\.shutdownNow\(\)' --type java --type kotlin | rg -i 'channel'
```

In your case the audit will almost certainly show one of these three shapes:

1. `close()` is missing entirely — the channel is opened in `open()` and never released.
2. `close()` exists but doesn't call `channel.shutdown()`, or calls `shutdown()` without `awaitTermination()` so the Netty `EventLoopGroup` keeps running.
3. `close()` calls `shutdown()` but a prior line throws (e.g. cancelling in-flight futures threw), so `shutdown()` is skipped — the "second-resource-leaks-when-first-close-throws" pattern.

The 60-FD step is too large for #3 alone (you'd expect ~5–10 FDs from a single leaked channel's executor). 60 strongly suggests **the whole channel + its Netty worker group is being leaked**, which is #1 or #2.

### Live probe — confirm which suspect

While the audit runs, get a heap dump from a live TM that's been through a few restarts and count channel instances:

```sh
kubectl exec -it <tm-pod> -- jcmd 1 GC.heap_dump /tmp/tm.hprof
kubectl cp <tm-pod>:/tmp/tm.hprof ./tm.hprof
# In MAT, OQL:
#   SELECT * FROM io.grpc.internal.ManagedChannelImpl
# Count > (operator parallelism on this TM) == leaked channels from prior job attempts.
```

Also grab a `jstack` and look for orphan Netty threads from prior attempts:

```sh
kubectl exec -it <tm-pod> -- jstack 1 > /tmp/tm.stack
grep -E 'grpc-default-worker-ELG|grpc-nio-worker' /tmp/tm.stack | wc -l
# Should equal (channels × workerCount). If it's N × (channels × workerCount), N-1 channels are leaked.
```

Final confirmation — add the JVM flag temporarily so the runtime warns you about un-shutdown channels at exit:

```yaml
# flink-conf.yaml
env.java.opts.taskmanager: "-Dio.grpc.netty.shaded.io.netty.leakDetectionLevel=paranoid"
```

You'll see `*~*~*~ Channel ManagedChannelImpl{...} was not shutdown properly!!! ~*~*~*` in the TM log on every job cancel. That string is dispositive.

---

## The fix

Apply both layers — the **outer** Flink lifecycle correctness and the **inner** gRPC shutdown discipline. Both are needed; either alone leaves a residual leak.

```java
public class EnrichmentAsyncFn extends RichAsyncFunction<In, Out> {

    // transient: serializer doesn't see them; reconstructed on each TM open()
    private transient ManagedChannel channel;
    private transient MyServiceGrpc.MyServiceFutureStub stub;
    private transient ConcurrentMap<In, ListenableFuture<Response>> inFlight;
    private volatile boolean closed = false;

    @Override
    public void open(Configuration parameters) {
        // one channel per operator instance is correct; do NOT share static across instances
        channel = ManagedChannelBuilder.forAddress(host, port)
            .usePlaintext()                      // or .useTransportSecurity()
            .keepAliveTime(30, TimeUnit.SECONDS) // detect dead peers
            .keepAliveTimeout(5, TimeUnit.SECONDS)
            .build();
        stub = MyServiceGrpc.newFutureStub(channel);
        inFlight = new ConcurrentHashMap<>();
    }

    @Override
    public void asyncInvoke(In in, ResultFuture<Out> rf) {
        ListenableFuture<Response> f = stub
            .withDeadlineAfter(800, TimeUnit.MILLISECONDS)   // tighter than Flink timeout
            .lookup(toRequest(in));
        inFlight.put(in, f);
        Futures.addCallback(f, new FutureCallback<>() {
            @Override public void onSuccess(Response r) {
                inFlight.remove(in);
                rf.complete(List.of(fromResponse(r)));
            }
            @Override public void onFailure(Throwable t) {
                inFlight.remove(in);
                rf.completeExceptionally(t);
            }
        }, MoreExecutors.directExecutor());
    }

    // CRITICAL — without this, Flink's AsyncIO timeout fires but the gRPC call keeps
    // the HTTP/2 stream + socket alive until the server-side deadline expires.
    @Override
    public void timeout(In in, ResultFuture<Out> rf) {
        ListenableFuture<Response> f = inFlight.remove(in);
        if (f != null) f.cancel(true);   // sends RST_STREAM, releases the stream slot
        rf.complete(List.of());
    }

    // Idempotent + suppressed-exception chaining so one failure doesn't skip the rest.
    @Override
    public void close() throws Exception {
        if (closed) return;
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
                    channel.shutdownNow();                       // forces EventLoopGroup down
                    channel.awaitTermination(5, TimeUnit.SECONDS);
                }
            }
        } catch (Throwable t) {
            if (first == null) first = t; else first.addSuppressed(t);
        }

        try { super.close(); }
        catch (Throwable t) {
            if (first == null) first = t; else first.addSuppressed(t);
        }

        if (first != null) throw new Exception(first);
    }
}
```

### Why each piece matters (and what breaks if you skip one)

| Piece | What it fixes | What breaks without it |
|---|---|---|
| `channel.shutdown()` + `awaitTermination()` | Releases Netty `EventLoopGroup` (8 worker threads, 8 selectors, ~16 FDs) | Channel reference is dropped but worker group keeps running. Pure FD leak. |
| `shutdownNow()` fallback | Forces termination if in-flight calls won't drain in 5s | `close()` returns "successfully" but worker group still running. Same leak, harder to see. |
| Idempotent `closed` flag | Second `close()` call on the failure path doesn't NPE on a half-disposed channel | Caller treats second-call exception as "didn't close", logs spam, often hides the real leak. |
| Suppressed-exception chaining | First failure doesn't skip subsequent cleanup | Classic "second resource leaks because first close threw" — your 60-FD step probably has this hidden in it. |
| `timeout()` override that cancels the future | Releases HTTP/2 stream + socket on Flink AsyncIO timeout | Sockets stay alive until server-side deadline. Under timeout pressure this dominates the leak. |
| `withDeadlineAfter` < Flink AsyncIO timeout | Deadline propagates to server; server-side work is cancelled | Without it, the server keeps computing after the client gave up — wasted work AND the channel keeps the stream. |
| Channel is `transient` and per-`open()` | One channel per operator instance, restored cleanly on savepoint | Static-singleton channels survive operator removal during savepoint restore and become unreachable, unclosable leaks. |

### Cross-cutting patterns (per output contract)

- [x] **Close-on-every-path discipline** — suppressed-exception chaining in `close()`.
- [x] **Connection scope shrunk** — Flink AsyncIO deadline < network-side deadline; in-flight futures cancelled on `timeout()` instead of being orphaned.
- [x] **Singleton client hoisted** — one `ManagedChannel` per operator instance, opened in `open()`, not per record.
- [x] **Shutdown hook added** — `close()` is the Flink-operator equivalent of `@PreDestroy`.

---

## Verification

The verification bar for Flink lifecycle leaks is specific: **restart the job 5 times in a row on the same TM pod, and confirm the FD count returns to baseline between restarts — not just that it grows slower.**

```sh
# Pin the TM pod, then loop:
TM=<tm-pod>
for i in 1 2 3 4 5; do
  echo "=== Iteration $i ==="
  PRE=$(kubectl exec $TM -- ls /proc/1/fd | wc -l)
  flink cancel <job-id>
  sleep 30                                     # give Netty its 5s to drain
  POST_CANCEL=$(kubectl exec $TM -- ls /proc/1/fd | wc -l)
  # redeploy
  POST_START=$(kubectl exec $TM -- ls /proc/1/fd | wc -l)
  echo "pre=$PRE  post-cancel=$POST_CANCEL  post-start=$POST_START  delta=$((POST_START-PRE))"
done
```

**Pass:**
```
pre=480  post-cancel=482  post-start=487  delta=+7
pre=487  post-cancel=487  post-start=490  delta=+3
pre=490  post-cancel=489  post-start=491  delta=+1
pre=491  post-cancel=490  post-start=492  delta=+1
pre=492  post-cancel=491  post-start=493  delta=+1
```
A delta of < 10 FDs per restart is normal startup churn (JIT class loading, metrics scrapes, JMX). Anything > 30 means the leak isn't fully fixed — re-run DIAGNOSE.

**Fail (what you had before):**
```
pre=480  post-cancel=520  post-start=540   delta=+60
pre=540  post-cancel=580  post-start=605   delta=+65
```

Also confirm in MAT:

```
Before: 17 ManagedChannelImpl instances on TM after 5 restarts
After:   N ManagedChannelImpl instances, where N == # of operator subtasks on this TM
```

And in the TM log:

```
# Before: appears on every cancel
*~*~*~ Channel ManagedChannelImpl{...} was not shutdown properly!!! ~*~*~*

# After: silent on cancel
```

Remove `-Dio.grpc.netty.shaded.io.netty.leakDetectionLevel=paranoid` once you've confirmed clean shutdown — it's expensive in steady-state.

---

## Watch list (post-deploy)

- **Metric:** `process_open_fds` per TM pod (or `ls /proc/1/fd | wc -l` if Prometheus isn't wired).
- **Watch window:** one full week, since your original failure mode took 5 days. Cancel+redeploy at least 15 times in that week (your normal 3x/day cadence).
- **Alert threshold:** re-fire if FD count grows by more than 50 FDs over any 24-hour window not attributable to parallelism change.
- **Bonus metric to add:** `flink_taskmanager_Status_JVM_Threads_Count` — it leaks in lockstep with `ManagedChannel`s (each leaked channel = ~8 leaked Netty worker threads). Trending this gives you earlier warning than FDs.
- **Followup ticket:** audit every other `RichAsyncFunction` and `RichSinkFunction` in the repo with the `comm -23` open-vs-close grep above. If you have one of these bugs, you probably have others — same author, same template.
