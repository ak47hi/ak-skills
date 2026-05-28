# Code review: `EnrichmentAsyncFn` — yes, this has leak risk. Do not merge as-is.

This is the canonical `RichAsyncFunction` + gRPC `ManagedChannel` shape that leaks on TM job restarts. The leak is in the lifecycle, not the happy path — under steady load you won't see it; under repeated job cancel/restart on the same TaskManager JVM you will see FDs and threads step up linearly with restart count.

Five concrete defects, ordered by severity.

---

## Bugs

### 1. `close()` does not wait for shutdown — channel and its EventLoopGroup leak across restarts  (BLOCKER)

`close()` line ~22:

```java
if (channel != null) channel.shutdown();
super.close();
```

`ManagedChannel.shutdown()` is **non-blocking**. It only signals the channel to stop accepting new RPCs and begin draining. The Netty `EventLoopGroup`, `NameResolver`, `LoadBalancer`, and HTTP/2 transport sockets are released asynchronously by the channel's own executor — which is itself owned by the channel.

When Flink calls `close()` on cancel, control returns immediately. Flink then tears the task down. The channel's internal executor may or may not have finished shutting down by the time the next job attempt calls `open()` and constructs a fresh channel on the same TM JVM. The leaked channel's Netty workers continue running until eventual GC — which under load may never happen.

Result: every job restart on the same TM adds one `ManagedChannelImpl`, one `NioEventLoopGroup`, and ~N sockets to the heap. Classic "FDs step up with restart count" signature.

You also need `shutdownNow()` as a fallback — `shutdown()` waits for in-flight RPCs to drain, which can hang indefinitely if the upstream is sick. That's exactly the moment the operator is being cancelled.

**Fix:** await termination with a bounded timeout, then force.

```java
if (!channel.shutdown().awaitTermination(5, TimeUnit.SECONDS)) {
    channel.shutdownNow();
    channel.awaitTermination(5, TimeUnit.SECONDS);
}
```

### 2. `close()` is not idempotent and not exception-safe  (HIGH)

Flink can call `close()` more than once on some failure paths (notably when `open()` itself throws partway, or on certain checkpoint-failure → restart sequences). Two issues:

- If a prior call already shut the channel down, a second call to `channel.shutdown()` is fine — but `awaitTermination` on an already-terminated channel is also fine, so the real bug is the missing `null`-out plus the missing try/finally around `super.close()`.
- `channel.shutdown()` itself is unlikely to throw, but if `awaitTermination` is interrupted, the exception propagates and `super.close()` never runs. Same shape as the `httpClient.close(); kafkaProducer.close();` anti-pattern: first resource's failure prevents second resource's cleanup.

**Fix:** guard with a `closed` flag, run `super.close()` in a `finally`, swallow `InterruptedException` after re-asserting the interrupt flag.

### 3. No `timeout()` override — in-flight RPCs and their HTTP/2 streams leak on Flink timeout  (HIGH)

`asyncInvoke()` line ~13 fires the gRPC call and registers a callback, but `EnrichmentAsyncFn` doesn't override `RichAsyncFunction.timeout()`. If `AsyncDataStream.unorderedWait(..., timeout, ...)` is configured upstream — and it should be, otherwise a slow upstream stalls the whole operator — then when Flink fires the timeout for a record:

- Flink calls the default `timeout()`, which throws and fails the job. Bad enough on its own.
- More importantly: the underlying `ListenableFuture` is **not cancelled**. The gRPC client still holds the HTTP/2 stream open against the upstream, waiting for its own (much longer, often default 20-second) deadline. Under load that's how you get hundreds of in-flight streams piled up on a healthy-looking channel — they each consume a stream slot in `maxConcurrentStreams`, not a separate socket, but exhaustion shows up as new RPCs blocking with no clear cause.

**Fix:** track in-flight futures keyed by input, override `timeout()` to cancel the future and complete the `ResultFuture` with an empty result (or error, your call), and remove the entry from the map in the callback.

### 4. No deadline on the RPC itself  (HIGH — correctness adjacent, but it's the mechanism that turns this into a leak under upstream slowness)

`stub.enrich(toRequest(in))` line ~14 — no `withDeadline` / `withDeadlineAfter`. A gRPC call without a deadline waits forever. Combined with bug #3, a slow or hung upstream pins streams indefinitely. The Flink operator's async timeout will fire (and break the job if `timeout()` isn't overridden), but the gRPC stream stays open.

**Fix:**

```java
stub.withDeadlineAfter(2, TimeUnit.SECONDS).enrich(toRequest(in));
```

Set the deadline tighter than the Flink async timeout (e.g. gRPC deadline 2s, Flink async timeout 3s) so gRPC kills the stream before Flink gives up on the record.

### 5. `MoreExecutors.directExecutor()` runs `rf.complete` on the gRPC event-loop thread  (MEDIUM — not strictly a leak, but it interacts with the others)

Line ~17 — the callback runs inline on whichever thread completed the future, which for Netty-backed gRPC is the event-loop thread. If `fromReply(r)` or anything in the success path blocks (logging, metrics emission, a downstream `ResultFuture` queue contention), you block a Netty I/O thread. Under load this manifests as channels getting stuck, RPC latencies skyrocketing, and — relevant to this review — `close()` taking longer than 5s because the event-loop threads can't drain.

For this operator, prefer a dedicated executor or at least the AsyncIO operator's own executor. If you keep `directExecutor()`, every line inside `onSuccess`/`onFailure` must be non-blocking.

---

## What's actually correct

- Fields declared `transient` — yes, required for Flink operator serialization.
- Channel built in `open()`, not as an instance initializer — yes, required so each subtask gets its own channel.
- Stub derived from channel — cheap, correct.

The shape is right. The lifecycle and async-cancellation are wrong.

---

## Corrected version

```java
public class EnrichmentAsyncFn extends RichAsyncFunction<Event, Enriched> {
    private static final Duration RPC_DEADLINE = Duration.ofSeconds(2);
    private static final Duration SHUTDOWN_GRACE = Duration.ofSeconds(5);

    private transient ManagedChannel channel;
    private transient EnrichServiceGrpc.EnrichServiceFutureStub stub;
    private transient ConcurrentMap<Event, ListenableFuture<EnrichReply>> inFlight;
    private volatile boolean closed = false;

    @Override
    public void open(Configuration parameters) {
        channel = ManagedChannelBuilder.forAddress("enrich-svc", 50051)
            .usePlaintext()
            .build();
        stub = EnrichServiceGrpc.newFutureStub(channel);
        inFlight = new ConcurrentHashMap<>();
    }

    @Override
    public void asyncInvoke(Event in, ResultFuture<Enriched> rf) {
        ListenableFuture<EnrichReply> reply =
            stub.withDeadlineAfter(RPC_DEADLINE.toMillis(), TimeUnit.MILLISECONDS)
                .enrich(toRequest(in));
        inFlight.put(in, reply);

        Futures.addCallback(reply, new FutureCallback<EnrichReply>() {
            @Override public void onSuccess(EnrichReply r) {
                inFlight.remove(in);
                rf.complete(List.of(fromReply(r)));
            }
            @Override public void onFailure(Throwable t) {
                inFlight.remove(in);
                rf.completeExceptionally(t);
            }
        }, MoreExecutors.directExecutor());
    }

    @Override
    public void timeout(Event in, ResultFuture<Enriched> rf) {
        ListenableFuture<EnrichReply> pending = inFlight.remove(in);
        if (pending != null) {
            pending.cancel(true);   // also cancels the underlying gRPC stream
        }
        rf.complete(Collections.emptyList());
        // alternative: rf.completeExceptionally(new TimeoutException("enrich timeout"));
        // depends on whether AsyncDataStream is configured with a side-output for timeouts
    }

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
        } catch (Throwable t) {
            first = t;
        }
        try {
            if (channel != null) {
                if (!channel.shutdown().awaitTermination(
                        SHUTDOWN_GRACE.toMillis(), TimeUnit.MILLISECONDS)) {
                    channel.shutdownNow();
                    channel.awaitTermination(
                        SHUTDOWN_GRACE.toMillis(), TimeUnit.MILLISECONDS);
                }
            }
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            if (channel != null) channel.shutdownNow();
            if (first == null) first = ie; else first.addSuppressed(ie);
        } catch (Throwable t) {
            if (first == null) first = t; else first.addSuppressed(t);
        }
        try {
            super.close();
        } catch (Throwable t) {
            if (first == null) first = t; else first.addSuppressed(t);
        }
        if (first != null) throw new Exception(first);
    }
}
```

Notes on the diff vs. the original:

- `ManagedChannelBuilder.forAddress("enrich-svc:50051", 50051)` in the original passes the port-suffixed string as host. Fix that — the form is `forAddress(host, port)`, host without port. (Half-bug, half-typo; harmless functionally because the colon-split happens internally for some resolvers, but it confuses NameResolver and shows up in logs.)
- `withDeadlineAfter` on every call.
- `inFlight` map keyed by input event lets `timeout()` cancel the right future.
- `close()` is idempotent, blocks on termination with grace + force-fallback, handles `InterruptedException` correctly, and runs `super.close()` in the equivalent of a finally.

---

## What to verify before merging

1. **CI harness regression test.** Add a test that loops `open()` → drive a handful of `asyncInvoke` calls (with a mock stub) → `close()` 50 times and asserts FD delta < 20. Template is in `references/21-flink.md` § "Harness-level FD-delta regression test". Gate with `assumeTrue(Files.exists(Paths.get("/proc/self/fd")))` so macOS/Windows agents skip cleanly. This is the bug catch you want forever — every Flink operator that calls `open()` should have one.

2. **5-restart loop on a staging TM pod.**
   ```sh
   for i in 1 2 3 4 5; do
     kubectl exec <tm-pod> -- sh -c 'ls /proc/1/fd | wc -l'
     flink cancel <jobid> && flink run ...
     sleep 30
     kubectl exec <tm-pod> -- sh -c 'ls /proc/1/fd | wc -l'
   done
   ```
   FD count must return to baseline after each cancel — not step up. Acceptable per-restart drift is < 10 FDs (startup churn); > 30 means the channel teardown still isn't completing.

3. **Heap dump after 5 restarts** — confirm `io.grpc.internal.ManagedChannelImpl` instance count equals the operator parallelism on that TM, not (parallelism × restart count). If you see 5× or more, `awaitTermination` is timing out and `shutdownNow()` isn't finishing the job either — escalate to async-profiler on `java.net.Socket.<init>`.

4. **Threads count metric**, if Prometheus is wired: `flink_taskmanager_Status_JVM_Threads_Count` should be flat across restarts. Climbing thread count is the loudest signature for "the operator's `close()` didn't release its executor" — applies here because the channel owns its Netty workers.

5. **Configure `AsyncDataStream.unorderedWait` (or `orderedWait`) with a timeout** at the call site that wires this operator into the job graph. Without an upstream timeout, the `timeout()` override never fires and the in-flight map grows unbounded. Set Flink async timeout slightly longer than the gRPC deadline (e.g. 3s Flink vs 2s gRPC) so gRPC kills the stream first.

6. **Confirm capacity is bounded.** `unorderedWait(... , capacity)` should be set explicitly. With the deadline + timeout above, capacity bounds peak in-flight, which bounds peak open HTTP/2 streams against the upstream. Without it, a slow upstream can pin thousands of streams and you'll hit gRPC's `maxConcurrentStreams` before you hit Flink's backpressure.

---

## Verdict

Request changes. The fix is mechanical — apply the corrected version above, add the harness test, and run the 5-restart verification before merging. The original has the right shape but three independent failure modes (non-blocking shutdown, no timeout cancellation, no deadline) that compound under exactly the conditions Flink operators hit in production: job cancel/restart cycles and upstream slowness.
