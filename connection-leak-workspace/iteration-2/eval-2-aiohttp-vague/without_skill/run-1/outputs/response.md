# Diagnosing the aiohttp connection leak

The `Unclosed client session` warning is the smoking gun. That message is emitted by `aiohttp.ClientSession.__del__` when the GC reaps a session whose `close()` was never awaited. Every leaked session leaves behind its `TCPConnector`, which owns the underlying socket pool — those pools are what `lsof` is counting. ~20/min lining up with steady request traffic strongly suggests **one new `ClientSession` per request** that never gets closed.

Let's confirm that, then fix it the right way.

---

## Step 1 — Confirm the hypothesis (5 minutes, no code changes)

### 1a. Count sockets by remote peer

You said "a bunch of different remote services". Group the sockets so you know whether it's one bad client or many:

```bash
# Inside the pod
lsof -p $(pgrep -f uvicorn | head -1) -nP -iTCP -sTCP:ESTABLISHED \
  | awk '{print $9}' | awk -F'->' '{print $2}' | sort | uniq -c | sort -rn | head -20
```

If one upstream dominates, you've found the offender. If it's evenly spread across many upstreams, then it's a shared helper that calls all of them (e.g., a generic `http_get()` utility) that's leaking.

Also check the breakdown by state — leaked sockets often sit in `CLOSE_WAIT` (peer closed, we didn't):

```bash
ss -tan state established | wc -l
ss -tan state close-wait  | wc -l
ss -tan state time-wait   | wc -l
```

A growing `CLOSE_WAIT` count is the canonical "we forgot to close the client" signature.

### 1b. Count `ClientSession` objects with py-spy

This is the decisive test. If sessions are leaking, they accumulate on the heap:

```bash
# Dump a live snapshot of Python objects
py-spy dump --pid $(pgrep -f uvicorn | head -1) --locals > /tmp/pyspy-dump.txt
```

That gives you stacks. For object counts, the easier path is to attach with `pyrasite` or just add a one-shot debug endpoint, but you can also get a lot from py-spy's `top`:

```bash
py-spy top --pid $(pgrep -f uvicorn | head -1)
```

Look for time spent in `aiohttp/client.py`, `connector.py`, or in your own HTTP helper. If you see `ClientSession.__init__` showing up in many stacks under different request handlers, that's confirmation: a session is being constructed per call site.

If you can briefly add an endpoint (or use an existing admin one), this is gold:

```python
import gc, aiohttp
@app.get("/debug/sessions")
def debug_sessions():
    sessions = [o for o in gc.get_objects() if isinstance(o, aiohttp.ClientSession)]
    return {
        "count": len(sessions),
        "closed": sum(1 for s in sessions if s.closed),
        "open":   sum(1 for s in sessions if not s.closed),
    }
```

If `open` is in the hundreds and climbing, you've proven it. If `closed` is large and `open` is small, sessions are being closed but the connector pools are sticking around — different bug (see "Variant B" below).

### 1c. Make the warning louder, temporarily

`Unclosed client session` only fires at GC time, which can be much later than the leak. Force the issue by enabling aiohttp's resource warnings and asyncio debug mode in a canary pod:

```bash
PYTHONTRACEMALLOC=10 PYTHONASYNCIODEBUG=1 PYTHONWARNINGS=always::ResourceWarning ...
```

With `tracemalloc`, the warning now includes the **allocation traceback** of the unclosed session — pointing straight at the file/line where it was constructed. This usually ends the investigation in one log line.

---

## Step 2 — The fix

99% of the time this is one of two patterns. Find which one applies and apply the corresponding fix.

### Anti-pattern A — Session-per-request (the common one)

```python
# WRONG — one session per request, never closed
async def fetch_user(user_id: str):
    session = aiohttp.ClientSession()              # leaks
    async with session.get(f"{URL}/users/{user_id}") as r:
        return await r.json()
```

Two things are wrong: (1) a new session per call, (2) no `close()`. Even if you fix (2), (1) defeats connection pooling and you'll trade socket leaks for `TIME_WAIT` exhaustion.

**Fix: one long-lived session per upstream, owned by the app's lifespan.** FastAPI's `lifespan` is the correct place:

```python
from contextlib import asynccontextmanager
from typing import Dict
import aiohttp
from fastapi import FastAPI, Request

@asynccontextmanager
async def lifespan(app: FastAPI):
    # One session per logical upstream. Tune limits per upstream's capacity.
    timeout = aiohttp.ClientTimeout(total=10, connect=2, sock_read=8)
    app.state.http: Dict[str, aiohttp.ClientSession] = {
        "users":    aiohttp.ClientSession(
            base_url="https://users.internal",
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=50,
                                           ttl_dns_cache=300, enable_cleanup_closed=True),
        ),
        "billing":  aiohttp.ClientSession(
            base_url="https://billing.internal",
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=50, limit_per_host=25,
                                           ttl_dns_cache=300, enable_cleanup_closed=True),
        ),
    }
    try:
        yield
    finally:
        # Close every session on shutdown; gather so one failure doesn't skip the rest.
        import asyncio
        await asyncio.gather(*(s.close() for s in app.state.http.values()),
                             return_exceptions=True)

app = FastAPI(lifespan=lifespan)

# Dependency for handlers
def http(name: str):
    def _dep(request: Request) -> aiohttp.ClientSession:
        return request.app.state.http[name]
    return _dep

@app.get("/users/{user_id}")
async def get_user(user_id: str, session: aiohttp.ClientSession = Depends(http("users"))):
    async with session.get(f"/users/{user_id}") as r:
        r.raise_for_status()
        return await r.json()
```

Key points:

- **One session per upstream**, not per request, not one global.  Per-upstream lets you size the pool and timeout to that dependency's SLO.
- **`TCPConnector(limit=…, limit_per_host=…)`** bounds the socket count. Without this, the pool is effectively unbounded (limit defaults to 100 total, which sounds bounded but per-host is unlimited).
- **`enable_cleanup_closed=True`** works around a known issue with TLS sockets being kept around in `CLOSE_WAIT`.
- **Always set a timeout.** The default is 5 minutes — a slow upstream pins sockets for that long, which on its own can look like a leak.
- **Close in the lifespan's `finally`.** If shutdown is skipped (SIGKILL), the OS reclaims sockets anyway; we only need to be clean on graceful shutdown.

### Anti-pattern B — Session created but closed via GC

```python
async def call_thing():
    session = aiohttp.ClientSession()
    try:
        async with session.get(URL) as r:
            return await r.json()
    finally:
        await session.close()   # missing in the buggy version
```

If you genuinely need a short-lived session (e.g., a background job), use `async with`:

```python
async with aiohttp.ClientSession() as session:
    async with session.get(URL) as r:
        return await r.json()
```

But: for anything in the hot path, prefer pattern A. Short-lived sessions defeat HTTP keep-alive and TLS session resumption.

### Anti-pattern C — Closing the session but not the response

Less common but worth checking: if any code path does `r = await session.get(url)` without `async with` or `r.release()`, the connection is held until GC. Grep for `session.get(` / `session.post(` without an enclosing `async with` or a `.release()`/`.close()`.

```bash
rg -n 'session\.(get|post|put|patch|delete)\(' --type py | rg -v 'async with'
```

---

## Step 3 — Verification plan

Don't declare victory on "the warning is gone" — leaks can be slow. Verify on three timescales.

### 3a. Local / staging — deterministic test

Spin up the service, hit a handler in a loop, watch the socket count plateau:

```bash
# Terminal 1
uvicorn app:app

# Terminal 2 — hammer it
hey -n 10000 -c 50 http://localhost:8000/users/42

# Terminal 3 — watch
watch -n 1 'lsof -p $(pgrep -f uvicorn | head -1) -nP -iTCP | wc -l'
```

Pass criterion: socket count rises during load, then **plateaus at or below `sum(limit_per_host)` across your sessions**, and **drops back** after load stops (give it `keepalive_timeout`, default 15s).

Also assert with py-spy / the debug endpoint:

```bash
curl localhost:8000/debug/sessions
# Expect: count == number of upstreams (e.g. 2), open == same, closed == 0
```

### 3b. Canary in prod — soak test

Roll the fix to one pod. Leave it for at least **2× your previous "doubling time"** (if you were growing 20/min from baseline, give it an hour). Watch:

- `lsof | wc -l` — should be flat, not climbing.
- `ss -tan state close-wait | wc -l` — should be near zero.
- `Unclosed client session` log occurrences — should be exactly zero.
- p50/p99 latency on the affected handlers — should be **better** (connection reuse), not worse. If worse, your `limit_per_host` is too tight.

### 3c. Guardrails so this can't silently come back

1. **Promote the warning to an error in CI**: run tests with `-W error::ResourceWarning`. Any leaked session in a test fails the build.
2. **Add a metric**: export `len([o for o in gc.get_objects() if isinstance(o, aiohttp.ClientSession)])` as a gauge on a low-frequency timer (every 30s). Alert if it exceeds `len(app.state.http) + small_buffer`.
3. **Lint rule**: a simple grep in pre-commit to reject `aiohttp.ClientSession(` outside `lifespan` / test fixtures. Crude but effective.
4. **Pod-level alert**: alert on `node_sockstat_TCP_inuse{pod=...}` growth rate > N/min sustained over 10 minutes. This catches the next class of leak too, not just aiohttp.

---

## TL;DR

1. `lsof | awk` to identify which upstream(s) are leaking; `ss` to confirm `CLOSE_WAIT` growth.
2. Run with `PYTHONTRACEMALLOC=10` for one minute — the `Unclosed client session` warning will name the file/line.
3. Replace per-request `aiohttp.ClientSession()` with **one session per upstream** owned by FastAPI's `lifespan`, with `TCPConnector(limit_per_host=…)` and an explicit `ClientTimeout`.
4. Verify with a load test that socket count plateaus and drops; add a `ResourceWarning`-as-error CI check and a session-count gauge so the next leak can't hide.

The fact that you're seeing the warning at all means GC is eventually catching unclosed sessions — so this is almost certainly pattern A (session-per-request), not a `CLOSE_WAIT` bug on the OS side. The fix above will collapse the curve.
