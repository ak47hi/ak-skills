# Mitigation — survive while you develop the fix

A real leak fix often takes hours to write, review, and deploy safely (especially anything touching transactions, lifecycle, or singletons that affect every request). Meanwhile the pod is dying. This reference is the "keep prod alive for the next 4 hours" playbook.

These are **explicit trade-offs**, not "best practices". Every mitigation here sacrifices something — performance, ergonomics, throughput, or revenue. Use them deliberately, with a written exit criterion (typically: "remove once PR <number> is merged and verified flat for 24h").

The skill is opinionated that mitigations are **not fixes**. SKILL.md § Anti-patterns explicitly refuses "just raise the pool size" as a fix. The distinction here is: raising the pool size **as a labeled, time-boxed mitigation** is acceptable; **as the answer to the leak**, it isn't. Always log the exit criterion in the same comment / config / runbook as the mitigation.

## 1. Scheduled pod restart (the bluntest tool)

Restart pods on a cron schedule shorter than the leak's exhaustion time. If the leak grows by 60 FDs / hour and your limit is 65k, you have 18 days; if it's 60 FDs / minute and your limit is 65k, you have 18 hours. Restart at half the exhaustion window.

```yaml
# Kubernetes CronJob restarting the deployment every 4 hours
apiVersion: batch/v1
kind: CronJob
metadata:
  name: my-svc-mitigation-restart
  annotations:
    mitigation/leak-ticket: "PROD-1234"
    mitigation/exit-criterion: "Remove after PROD-1234 fix verified flat for 24h"
spec:
  schedule: "0 */4 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: deployment-restarter
          restartPolicy: Never
          containers:
            - name: kubectl
              image: bitnami/kubectl:1.28
              command:
                - sh
                - -c
                - kubectl rollout restart deployment/my-svc -n prod
```

**Sacrifices:** in-flight requests during restart are interrupted (use a `preStop` hook + readiness probe with `terminationGracePeriodSeconds` ≥ max request duration to minimize this); request latency briefly spikes; deploys interleave with mitigation restarts.

**When NOT to use:** if your service has long-lived stateful connections (websockets, server-sent events, gRPC streams), restart drops them. Find a different mitigation.

## 2. Tighten leak detection so the bad code is loud

For JDBC: set `leak-detection-threshold` aggressively (e.g., 5000ms instead of 30000ms). The connection still gets reused after the timeout — Hikari just logs the stack trace of whoever held it past the threshold.

```yaml
spring.datasource.hikari.leak-detection-threshold: 5000  # was 30000 — temporary
```

**What this buys you:** every leak event logs a stack trace pointing at the offending code. Speeds up diagnosis dramatically, especially if the leak is intermittent or load-dependent.

**Sacrifices:** log volume spikes (potentially expensive on hot leaks); legitimate slow transactions also trip the warning.

**Exit:** revert to 30s once the bug is fixed.

## 3. Tighten timeouts so hung calls fail fast

If the leak's proximate cause is upstream slowness amplified by missing timeouts (see `references/95-not-a-leak.md` § 2), set aggressive timeouts immediately, before the structural fix lands:

```java
// Spring Boot application.yml — emergency timeout values
http.client.connect-timeout: 2000ms
http.client.read-timeout: 3000ms
```

**What this buys you:** sockets free quickly even if the upstream stays sick. Trades latency / partial-failure error rate for connection-pool stability.

**Sacrifices:** higher 5xx rate on calls to slow upstreams (which is often the right answer — fail fast and surface the upstream's problem instead of consuming all your connections waiting on it).

**Exit:** revert (or tune up) once the upstream is healthy AND your code has proper structural timeout handling.

## 4. Raise FD limit AS a time-boxed mitigation (not a fix)

This is the one the skill normally refuses — but as an explicit, ticketed, time-boxed mitigation while the actual fix is being written, it's defensible. Just be ruthless about the exit criterion.

```yaml
# K8s pod spec — temporary FD limit bump
securityContext:
  capabilities:
    add: ["SYS_RESOURCE"]
# in container command, before exec'ing the app:
command: ["sh", "-c", "ulimit -n 130000 && exec /usr/bin/myservice"]
```

**Sacrifices:** delays the failure by 2× — but does NOT fix the leak. If the leak rate stays constant, you've bought one cycle of breathing room. After that the bigger ceiling makes the eventual failure bigger.

**What to log alongside:** the leak rate and the new TTL. "Leak rate 60 FDs/min, limit 130k → exhaustion in ~36h instead of ~18h. Fix MUST land by <date>."

**Exit:** revert to 65k once the fix is verified.

## 5. Circuit breaker / load shed

If the leak is downstream-call-shaped (an external service triggers the bug), add a circuit breaker so when the leak rate accelerates, calls stop hitting the bad path:

```java
// Resilience4j circuit breaker on the leak's call site
@CircuitBreaker(name = "stripeCharge", fallbackMethod = "stripeChargeFallback")
public PaymentResult charge(ChargeRequest req) { ... }

private PaymentResult stripeChargeFallback(ChargeRequest req, Throwable t) {
    // mitigation fallback — queue for later, error to client, etc.
    enqueueForLaterProcessing(req);
    throw new ServiceTemporarilyUnavailable(t);
}
```

**Sacrifices:** part of your traffic gets degraded service (queue or error) instead of consuming a leaked connection. Often the right call — better to fail 5% loudly than 100% slowly.

**Exit:** circuit breaker often stays even after the leak fix lands — it's defense in depth.

## 6. Canary rollback (if the leak landed in a recent deploy)

If the slope started exactly when a deploy went out, the fastest mitigation is a rollback:

```sh
# K8s
kubectl rollout undo deployment/my-svc -n prod
# Argo
argo rollback <release>
```

**Sacrifices:** lose any other improvements / fixes in the rolled-back deploy.

**When this is the right move:** leak rate is severe (< 4h to exhaustion), the deploy is small / recent, and the rollback is fast (< 5 min). Cuts off the leak at the source while you investigate the diff.

**This counts as a fix-shaped action, not a mitigation, IF** the rolled-back code is then patched and re-deployed with the leak removed. Document the leak's introduction and the deploy diff in the post-mortem.

## 7. Traffic shed at the LB

If the leak rate scales with request volume, drop a fraction of traffic at the load balancer or API gateway. Buys time at the cost of error rate.

```yaml
# Envoy / Istio EnvoyFilter dropping 30% of traffic to the affected service
http_filters:
  - name: envoy.filters.http.fault
    typed_config:
      abort:
        percentage:
          numerator: 30
        http_status: 503
```

**Sacrifices:** explicit 30% error rate for affected callers. Coordinate with downstream teams before activating.

**Exit:** revert as soon as the leak rate flattens (typically once the fix is deployed, before declaring victory).

---

## Decision rule

Mitigations are a **bridge**, not a **destination**. Apply when:

- The leak rate gives you less than 24h to fix it properly.
- The structural fix needs review / testing time you don't have.
- The blast radius of a bad fix is high (e.g., transaction-scope refactor near payment code).

Don't apply mitigations to:

- A flat slope (it's not a leak — see `references/95-not-a-leak.md`).
- A slope you have a clean structural fix for that can land within hours.
- Critical-path code you can't safely roll back (if a circuit breaker would hide a payments failure mode, don't add one as mitigation).

## Always include in the mitigation's commit/config/PR

```
LEAK_MITIGATION: <one-line description>
Tracking ticket: <link>
Exit criterion: <e.g., "Remove after PR #1234 verified flat for 24h">
Date added: <YYYY-MM-DD>
Owner: <oncall handle>
```

A mitigation without an exit criterion **is** the new shape of the bug. The skill's recurring anti-pattern ("raising the pool size masks the leak") becomes accurate again the moment an unowned, undocumented mitigation outlives the leak it was meant to bridge.
