# aiohttp CLOSE_WAIT to a single remote — hung, not leaked

## TL;DR

You don't have a `ClientSession` lifecycle leak. Your singleton is correct. What you have is **~200 coroutines blocked indefinitely on an in-flight HTTP request to the recommendations service**, because your `aiohttp` calls have **no timeout**. The recommendations service half-closes the socket (TCP FIN), but your client never observes the close because it's still parked in `_request` waiting for response bytes that will never arrive. The kernel parks those sockets in CLOSE_WAIT, and the count climbs 1:1 with newly-hung coroutines.

This is a classic misdiagnosis. The triage signature *looks* like a leak (CLOSE_WAIT climbing, FD growth), but the resource is not leaked — it's **wedged inside the application**. The fix is timeouts + cancellation discipline, not closing discipline.

---

## How I diagnosed this

### TRIAGE signature

What your evidence says:

| Observation | What it rules out / in |
|---|---|
| CLOSE_WAIT growing, ESTABLISHED to a **single** remote | Not a per-client leak (`ClientSession` per request) — that would spray across many remotes |
| Singleton `ClientSession`, closed in `lifespan` | Per-client leak ruled out by inspection — only one session exists |
| `py-spy dump` shows ~200 coroutines all parked **at the same line** inside `_request` | This is the load-bearing clue. Coroutines aren't *leaked* — they're *blocked*. Each one is holding an `aiohttp` `Connection` borrowed from the connector pool, waiting on a socket read that will never complete |
| Slow steady growth (50 → 350 over 4 hours ≈ 1.25/min) | Matches request rate × failure probability for hung calls, not a per-request close leak (those usually scale faster with traffic) |

CLOSE_WAIT means the **remote called close, the local app has not**. In your case the local app *can't* close — the coroutine that owns the connection is parked inside `_request` and never reaches the `async with` exit that would release it back to the connector. From the connector's perspective the connection is "checked out, in use". From the kernel's perspective the socket is half-closed.

### ROUTE

HTTP/Python/aiohttp → `references/22-http-grpc.md`.

But within that reference, this matches the explicit "py-spy parked in aiohttp request methods" pattern: requests are in-flight and not completing, often a missing timeout, which then **masquerades as a leak** as the client waits forever. That's exactly your shape.

### Why your singleton is not the bug

Per-request `ClientSession()` construction would produce:

- `Unclosed client session` warnings (you'd have seen these in logs)
- CLOSE_WAIT/ESTABLISHED spread across **many** remotes (the connector pool gets recreated each call, every host gets re-dialed)
- FD growth proportional to **request rate**, not failure rate

You have none of those. Your singleton lifecycle is correct.

---

## Root cause

Two interacting bugs:

1. **No total timeout on the request.** aiohttp's default `ClientTimeout(total=300)` is 5 minutes — and if you've passed `timeout=None` anywhere, or if the request is stuck before the timer arms, the request will block forever. More importantly, "5 minutes" is long enough for ~1000 concurrent calls to pile up against a slow upstream.
2. **No `TCPConnector` cleanup for sockets the peer closed.** aiohttp has a long-standing issue where TLS sockets the remote closed remain in the connector's pool until the next request to the same host. The workaround is `enable_cleanup_closed=True`. Even with timeouts, you want this on for any TLS upstream.

The recommendations service is the immediate trigger — likely it's hitting its own backend timeout, half-closing the connection, but its connection-reset / RST_STREAM isn't propagating cleanly. Common causes there: an LB (envoy/nginx) between you and the upstream killing idle connections; the upstream's keep-alive idle timeout being shorter than your reuse interval; or the upstream's worker stalling without resetting the socket.

---

## Fix

### 1. Put a hard timeout on every call

The tightest, smallest change:

```python
# session construction at startup (in lifespan)
import aiohttp

timeout = aiohttp.ClientTimeout(
    total=5,            # total budget per request — set this aggressively
    connect=2,          # TCP + TLS handshake
    sock_connect=2,     # socket-level connect
    sock_read=3,        # max wait for any one read — THE key knob for your bug
)

connector = aiohttp.TCPConnector(
    limit=100,
    limit_per_host=20,
    ttl_dns_cache=300,
    enable_cleanup_closed=True,    # critical for TLS; reaps half-closed sockets
    keepalive_timeout=15,          # shorter than typical LB idle-kill (usually 60s)
)

app.state.http = aiohttp.ClientSession(
    timeout=timeout,
    connector=connector,
)
```

`sock_read` is the one that fixes your specific symptom. `total` is the backstop. `enable_cleanup_closed` clears out the CLOSE_WAIT sockets that already accumulated, and prevents new ones from getting stuck.

### 2. Handle the timeout explicitly at the call site

Don't let `asyncio.TimeoutError` propagate as a generic 500 — it's a degraded upstream, not a bug:

```python
import asyncio
from aiohttp import ClientError

async def fetch_recommendations(user_id: str) -> Recommendations | None:
    try:
        async with app.state.http.get(
            f"{RECS_URL}/v1/recs/{user_id}",
            # per-call override if this call needs different budget:
            # timeout=aiohttp.ClientTimeout(total=2),
        ) as resp:
            resp.raise_for_status()
            return Recommendations.parse_obj(await resp.json())
    except (asyncio.TimeoutError, ClientError) as e:
        log.warning("recs upstream degraded", extra={"user_id": user_id, "err": str(e)})
        return None   # or your fallback path
```

The `async with` ensures the connection is released to the pool on **every** path — success, timeout, and `ClientError`. When `sock_read` fires, aiohttp cancels the request task; the `__aexit__` runs and the half-closed socket is closed, not parked.

### 3. (Optional but recommended) Add a circuit breaker

Once timeouts are in, a slow upstream produces a burst of `TimeoutError` instead of stuck coroutines — that's strictly better, but it still costs you latency and worker capacity. Add a breaker so when the upstream is degraded you fail fast:

```python
# using aiobreaker or similar
from aiobreaker import CircuitBreaker, CircuitBreakerError
from datetime import timedelta

recs_breaker = CircuitBreaker(
    fail_max=10,
    timeout_duration=timedelta(seconds=30),
)

@recs_breaker
async def fetch_recommendations(user_id: str): ...
```

This isn't required to fix the CLOSE_WAIT — it's a production-hygiene follow-up.

### 4. Audit the rest of the codebase for the same shape

```sh
# any aiohttp call without an explicit timeout AND not relying on a session-default
rg -n 'session\.(get|post|put|delete|patch|request)\(' --type py | rg -v 'timeout='

# explicit timeout=None — almost always a bug in a long-lived service
rg -n 'timeout\s*=\s*None' --type py

# session construction sites — confirm only one, in lifespan
rg -n 'ClientSession\(' --type py
```

The first grep is noisy if you set a session-level default (which you should), but it's worth scanning once.

---

## Verification plan

Sample these before and after the deploy, under the same load level that produced the original alert:

### 1. CLOSE_WAIT count

```sh
kubectl exec -it <pod> -- ss -tn state close-wait | wc -l
```

Run every minute for 10 minutes. **Expected after fix: oscillates near 0, does not climb.** Existing CLOSE_WAIT entries will drain once `enable_cleanup_closed=True` ticks (a few seconds to a minute).

### 2. Coroutines parked in `_request`

```sh
kubectl exec -it <pod> -- py-spy dump --pid 1 | grep -c 'aiohttp.*_request'
```

**Expected after fix: bounded by your in-flight request concurrency** (i.e. equal to the number of currently-active HTTP calls, not the accumulated total). Should never grow unboundedly. If you're handling 50 RPS with p99 200ms, you should see ~10, not 200+.

### 3. Total FD count slope

```sh
# sample every 30s for 20 minutes
while true; do
  echo "$(date +%s) $(kubectl exec <pod> -- sh -c 'ls /proc/1/fd | wc -l')"
  sleep 30
done
```

**Expected after fix: flat slope.** Not lower — flat. Your original rate was ~1.25 FDs/min; the success criterion is `dFD/dt ≈ 0` averaged over 20 minutes under load.

### 4. Timeout exception count

In your application metrics, count `asyncio.TimeoutError` on the recs path. **Expected after fix: small but non-zero.** If it's zero, your timeouts are too generous; if it's a flood, the upstream is actually broken and you should talk to its owners.

### 5. Heap-dump sanity check (optional)

You don't need this for a timeout-shaped bug, but if you want belt-and-braces:

```python
# add to /debug endpoint
import gc, aiohttp
sessions = [o for o in gc.get_objects() if isinstance(o, aiohttp.ClientSession)]
return {"client_sessions": len(sessions)}   # should be exactly 1
```

---

## What to push back on if someone suggests it

- **"Restart the pods on a schedule."** Postpones the symptom; doesn't fix the wedge. Also masks the upstream's degradation from on-call.
- **"Raise `ulimit -n`."** Same shape — buys time, hides the bug. The leak rate is constant; eventually it pages someone on a worse night.
- **"Recreate the `ClientSession` periodically."** Trades one bug class (no timeouts) for another (per-period reconstruction loses the connection pool, raises tail latency, can introduce its own race). Don't do it.
- **"Add `enable_cleanup_closed=True` and ship."** Necessary but not sufficient. It reaps the OS-level half-closed sockets, but if your coroutines are still parked indefinitely in `_request`, you'll keep producing them. Timeouts are the actual fix; cleanup is the hygiene.

---

## Summary

| | |
|---|---|
| **Resource class** | HTTP client (aiohttp) |
| **Shape** | Hung-not-leaked — coroutines blocked inside `_request`, holding connections, peer half-closed |
| **Root cause** | No `sock_read` / `total` timeout on aiohttp requests to recommendations service |
| **Call site to fix** | Wherever you construct `aiohttp.ClientSession` in your `lifespan`, plus the recommendations call site |
| **Fix** | `ClientTimeout(total=5, sock_read=3, ...)` on the session + `enable_cleanup_closed=True` on the connector + explicit `TimeoutError` handling |
| **Verification** | CLOSE_WAIT count stays near 0; parked `_request` coroutines bounded by concurrency; FD slope flat over 20 min under load |

Your singleton was a red herring — it's correct, and you should leave it alone. The bug is that aiohttp will wait forever by default, and "forever" against a slow upstream looks exactly like a leak.
