# Not-a-leak — false-positive catalog

Some "leak" symptoms aren't leaks. Applying leak fixes to these cases makes things worse — shrinks the pool against a sizing problem, hides a sick upstream behind a fake-leak label, adds complexity to handle an OS-level effect that resolves on its own. Read this before opening a domain reference if your TRIAGE signature is ambiguous.

The five common false positives, in order of how often they get misdiagnosed as leaks:

## 1. Flat slope, pool exhaustion at peak — sizing, not leak

**Signature:**
- `ls /proc/1/fd | wc -l` is flat (oscillates around steady state) under normal load.
- Pool exhaustion / `Connection is not available` only at predictable peaks (8am traffic, batch-job kickoff, daily cron).
- HikariCP `ActiveConnections` oscillates 0 → max → back to ~0 between peaks.
- Off-peak: zero `idle in transaction` rows in `pg_stat_activity`.

**Why it looks like a leak:** the `Connection is not available` error message is identical to the one a real leak produces. Teams reach for leak fixes (lower `maxLifetime`, tighten `leak-detection-threshold`) which don't apply.

**The actual diagnosis:** peak QPS exceeds `maxPoolSize` × (1 / mean holding time). Little's Law: required pool size ≥ peak QPS × mean transaction duration in seconds. If your peak is 50 QPS and each transaction holds for 0.5s, you need ≥25 connections, not 20.

**Fix path:**
1. Measure peak QPS and p99 holding time during the peak window.
2. Compute required `maxPoolSize` per Little's Law.
3. Check that the new size doesn't exceed your Postgres `max_connections` (with all replicas × instances accounted for; PgBouncer mode matters).
4. Raise `maxPoolSize` deliberately, with the calculation logged.

**Push back if the user wants to "just raise it to 100":** without the calculation, you may exhaust the database side. Postgres default `max_connections` is 100; if you have 4 service instances at 100 each, that's 400 — well past default.

**Out of scope for this skill.** This is pool sizing, not leak hunting. See SKILL.md § "When to push back".

## 2. CLOSE_WAIT to one remote + parked request coroutines/threads — hung requests, not leak

**Signature:**
- CLOSE_WAIT to **one** remote (your upstream), growing slowly (5–50 per hour).
- `py-spy dump` shows N coroutines all parked at the same line inside the HTTP client's request method.
- Equivalent for JVM: `jstack` shows N threads parked in `SocketInputStream.socketRead0` or `okhttp3.internal.connection.Exchange.readResponseHeaders`.
- The client itself is correctly managed (singleton, lifespan-scoped, properly closed at shutdown).
- No `Unclosed client session` / `LEAK: ByteBuf.release()` log lines.

**Why it looks like a leak:** sockets accumulate over time. CLOSE_WAIT grows monotonically. Looks identical to a per-request close miss.

**The actual diagnosis:** the upstream is slow or half-dead. Your client has no read timeout (or it's too long), so request coroutines/threads are parked indefinitely. The remote eventually closes its half of the connection (TCP keep-alive timeout, ALB idle timeout) — your client never notices because it's still waiting for a read that will never complete. Socket sits in CLOSE_WAIT, the connection slot stays checked out of the connector.

**Fix path:**
1. Set explicit, **short** timeouts on every HTTP call. Total < your service's SLO. Connect < 2s. Read < your upstream's p99 + headroom.

   ```python
   # aiohttp
   aiohttp.ClientTimeout(total=5, connect=2, sock_read=3)
   ```
   ```java
   // OkHttp
   client.newBuilder().callTimeout(5, SECONDS).readTimeout(3, SECONDS).build();
   ```
   ```java
   // Spring WebFlux WebClient
   HttpClient.create().responseTimeout(Duration.ofSeconds(5))
   ```
2. Add a circuit breaker on the upstream call (Resilience4j, hystrix-like) so a sick upstream stops sinking the whole service.
3. Surface a `TimeoutError` rate metric — non-zero is now an early warning that the upstream is degrading.

**Verification:** CLOSE_WAIT count drops to ~0; coroutine/thread park count bounded by in-flight concurrency (not accumulating); upstream timeout count > 0 (the metric is **healthier** when non-zero — it means timeouts are doing their job).

**This is not a leak.** Apply the leak skill's "shrink scope" or "singleton client" fixes and you'll do nothing — the bug is in the request lifecycle's *upper bound*, not in close discipline.

## 3. CLOSE_WAIT during deploy — k8s deregistration timing, not leak

**Signature:**
- CLOSE_WAIT spikes during rolling deploy, then drains within 30–120s of the deploy completing.
- Slope flat outside deploy windows.
- Affects the K8s service's ALB / NLB ingress, not application sockets.

**Why it looks like a leak:** CLOSE_WAIT spikes are alarming. Teams add a leak monitor that fires on every deploy.

**The actual diagnosis:** the load balancer keeps sending requests for a few seconds after the pod's readiness probe goes false. Those connections hit a pod that's `SIGTERM`-ed; the pod's HTTP server stops accepting; the LB closes its half → CLOSE_WAIT on the pod side until the OS reaps the socket.

**Fix path (if you really care):**
1. Add a `preStop` lifecycle hook with `sleep 15` (or your service's drain period). Pod stays alive past `terminationGracePeriodSeconds` while the LB notices the readiness change.
2. Set `terminationGracePeriodSeconds: 30` (or more — > preStop + max-request-duration).
3. For Spring Boot: `server.shutdown=graceful` + `spring.lifecycle.timeout-per-shutdown-phase=20s`.

**This is expected behavior, not a leak.** Treat alerts that fire only during deploys as a deploy hygiene issue.

## 4. Small CLOSE_WAIT count, stable — normal, not leak

**Signature:**
- CLOSE_WAIT count between 1 and ~50, stable, doesn't climb.
- No correlated user-visible symptom.
- No `LEAK:` log lines.

**Why it looks like a leak:** "non-zero CLOSE_WAIT is bad" is a common myth, especially in monitoring dashboards.

**The actual diagnosis:** TCP is a stateful protocol; CLOSE_WAIT briefly exists as the local side acknowledges the remote's FIN before issuing its own. Steady-state small counts are healthy.

**Threshold heuristic:** alert on CLOSE_WAIT > 100 sustained for >5 minutes, OR a slope ≥ 5 per minute, NOT on any non-zero value.

**Don't fix this.** Adjust the alert.

## 5. Burst FD growth correlated with a specific request type — not a leak, traffic shape

**Signature:**
- FDs jump by hundreds within seconds, then plateau or recover slowly.
- The spike correlates with a specific endpoint, feature flag rollout, or scheduled job (analytics export, big report).
- No long-term unbounded growth.

**Why it looks like a leak:** any rapid FD increase trips leak alerts.

**The actual diagnosis:** a fan-out request kicks off many parallel outbound calls (e.g., a `/admin/report` endpoint that hits 200 microservices). Each is correctly closed eventually; the burst just exceeds the connection pool's idle eviction rate.

**Fix path (if it's actually a problem):**
1. Cap parallelism per request (`Semaphore`, `parallelStream` with a custom `ForkJoinPool`).
2. Add a circuit breaker so a slow downstream doesn't amplify the burst.
3. Raise `keepalive_timeout` so the pool doesn't churn under bursty load.

**This is a load-shape issue, not a leak.** Connections eventually return. If they don't (slope rises across multiple bursts), then it's a real leak — back to the full workflow.

## 6. Bonus — slowloris / SYN flood looks like a leak (rare but real)

**Signature:**
- FDs climbing on the **inbound** side (your service is the server).
- `ss -tn state established` shows many connections from few source IPs, with very low transfer.
- The pattern correlates with a public endpoint going viral or a security incident.

**Not a leak you can fix in app code.** This is an external attack (slowloris) or a misbehaving client (mobile app stuck in a retry loop). Escalate to your edge / WAF / DDoS protection layer; don't apply leak fixes to your application.

---

## Decision rule

If your TRIAGE signature matches any of sections 1–6, **do not open a domain reference**. The leak fix patterns will not help and may make things worse. Address per the matching section above, or escalate out of this skill's scope (sizing, ops, security).

If your signature is **mostly** like one of these but with an additional rising trend that doesn't recover — you may have **both** a non-leak issue AND a leak. Treat as multi-domain per `references/01-routing.md` § Overlap rules: fix the dominant slope first, re-route on the residual.
