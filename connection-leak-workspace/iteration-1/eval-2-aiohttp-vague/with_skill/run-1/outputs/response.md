# Connection leak: aiohttp `ClientSession` not closed / likely constructed per request

You have enough signal to skip ahead: Python + FastAPI + `Unclosed client session` + ~20 FDs/min growth + py-spy in the pod. That's an aiohttp leak — most often per-request `ClientSession` construction, occasionally a missing `async with` on the response. The diagnostic path below will tell you which of the two in under five minutes.

---

## Where to start — TRIAGE (run this first, capture the slope)

You need a baseline slope number before touching code, so VERIFY has something to compare against.

```sh
# 1. confirm and quantify the slope
kubectl exec -it <pod> -- sh -c 'for i in $(seq 1 10); do ls /proc/1/fd | wc -l; sleep 30; done'

# 2. classify FDs — should be dominated by `socket`
kubectl exec -it <pod> -- sh -c 'ls -l /proc/1/fd | awk "{print \$11}" | cut -d: -f1 | sort | uniq -c | sort -rn'

# 3. break down remotes — one dominant remote vs many
kubectl exec -it <pod> -- ss -tn state established \
  | awk 'NR>1 {print $5}' | awk -F: '{print $1}' \
  | sort | uniq -c | sort -rn | head -20

# 4. CLOSE_WAIT count — non-zero and climbing means missing close on the response/session
kubectl exec -it <pod> -- ss -tn state close-wait | wc -l
```

Record the slope (FDs/min) — that's your VERIFY target.

---

## Disambiguate: per-request `ClientSession` vs per-request `response`

Both produce "Unclosed client session" warnings; the fixes differ. Two probes:

### Probe A — count ClientSession constructions live

`py-spy` is in the pod. Patch `ClientSession.__init__` to print a stack on every construction; run for 60 seconds under steady traffic.

```python
# attach via a debug endpoint, an exec'd python -c, or pre-load on startup
import traceback, aiohttp
_orig = aiohttp.ClientSession.__init__
def _logged(self, *a, **kw):
    print("ClientSession created at:")
    traceback.print_stack()
    return _orig(self, *a, **kw)
aiohttp.ClientSession.__init__ = _logged
```

- If you see **more than a handful** of stacks in 60s (one or two per upstream service is normal at startup) → **per-client leak** (constructing a session per request). This is the dominant aiohttp leak in production code.
- If you see **only the startup constructions** but FDs still climb → **per-request leak** on the response side (missing `async with session.get(...)`).

### Probe B — `py-spy dump` for parked coroutines

```sh
kubectl exec -it <pod> -- py-spy dump --pid 1
```

Look for many coroutines parked inside aiohttp `_request` / `_create_connection` / `request_lock`. Symptoms:

- Lots of coroutines parked with no timeout → outbound calls hanging forever, masquerading as a leak (each holds an open socket). Fix is `ClientTimeout`, not just session lifecycle.
- Coroutines all rooted at distinct call sites that each look like `async with aiohttp.ClientSession()` → confirms per-request construction.

### Probe C — confirm one remote vs many

From TRIAGE step 3:

- One remote dominates → per-request leak on responses to that service.
- Many different remotes → per-client construction leak (each call to a new upstream constructs its own session, each session brings its own connector + DNS resolver + sockets).

`~3000 sockets` and `+20/min` with a mix of remotes is the classic per-request `ClientSession` signature. That's where I'd put my prior.

---

## The fix — singleton `ClientSession` on the FastAPI lifespan

This is the right fix in 90% of FastAPI + aiohttp services. Build the session once at app startup, store it on `app.state`, close it at shutdown. Pin a timeout while you're there — missing timeouts amplify any leak.

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
import aiohttp


@asynccontextmanager
async def lifespan(app: FastAPI):
    # one connector, one session, one DNS cache, one TCP pool — shared by all requests
    connector = aiohttp.TCPConnector(
        limit=100,            # total open connections
        limit_per_host=20,    # per upstream host
        ttl_dns_cache=300,
    )
    timeout = aiohttp.ClientTimeout(total=10, connect=2)
    app.state.http = aiohttp.ClientSession(connector=connector, timeout=timeout)
    try:
        yield
    finally:
        await app.state.http.close()


app = FastAPI(lifespan=lifespan)


# dependency for handlers
def http_session(request: Request) -> aiohttp.ClientSession:
    return request.app.state.http


# example handler — note: NO `async with ClientSession()` here
@app.get("/proxy")
async def proxy(url: str, session: aiohttp.ClientSession = Depends(http_session)):
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.json()
```

The two non-negotiable rules:

1. **One `ClientSession` per process** (or per distinct upstream if you really need different connectors / auth). Construct it in `lifespan`, close it in the `finally`.
2. **Every `session.get` / `session.post` is wrapped in `async with`** — even if you just call `await resp.text()` immediately. The `async with` is what guarantees the response is released back to the pool on the exception path.

If you have multiple upstreams that need different timeouts or auth headers, attach **one session per upstream** to `app.state` (e.g. `app.state.upstream_a`, `app.state.upstream_b`). Don't create them per request.

### Bonus: handle background tasks

If the service spawns background tasks (`asyncio.create_task(...)`) that make outbound calls, they must use the same singleton session — not construct their own. Otherwise the background path leaks even after you fix the request path.

---

## Verification plan

Re-run the same TRIAGE samples after deploying the fix. The slope is the metric that matters, not the absolute count.

```sh
# 1. re-sample FD count over 5+ minutes under the same load that produced the alert
kubectl exec -it <pod> -- sh -c 'for i in $(seq 1 10); do ls /proc/1/fd | wc -l; sleep 30; done'

# 2. CLOSE_WAIT should drop to zero (or near it)
kubectl exec -it <pod> -- ss -tn state close-wait | wc -l

# 3. confirm singleton — re-run Probe A for 60s. Should print exactly one stack at startup, zero during steady-state traffic.

# 4. confirm warnings are gone
kubectl logs <pod> --since=10m | grep -E 'Unclosed (client session|connector)' | wc -l   # must be 0
```

Pass criteria (all four must hold):

- **FD slope is flat**, not just lower. A reduced slope is still a leak — it just pages someone on a different night.
- **CLOSE_WAIT count ≈ 0**.
- **`ClientSession.__init__` fires once** at startup, not per request.
- **Zero `Unclosed client session` warnings** in the 10 minutes after deploy.

Watch `process_open_fds{pod="..."}` in Prometheus for a full traffic cycle (24h, or one peak). If the slope is back, re-run TRIAGE — the dominant leak may have shifted (e.g. there's also an asyncpg / SQLAlchemy leak hiding behind the aiohttp one).

---

## Anti-patterns to avoid while fixing this

- **Do not raise the pod's `ulimit -n` or `LimitNOFILE`** to make the alert quieter. The leak is unbounded; the limit is a circuit breaker. Raising it postpones the page without fixing anything.
- **Do not wrap `ClientSession()` in a `try/except` that swallows close errors.** If `close()` raises, you want to know.
- **Do not "fix" this by setting `connector.limit`.** Limits cap concurrent in-flight connections; they don't stop session-construction leaks. Sockets will still pile up via the per-session connectors.
- **Do not use `requests` inside async handlers as a "quick fix".** Blocks the event loop, doesn't solve the leak, makes things worse.
