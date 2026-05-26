# aiohttp connection leak — start here

You have enough signal already to route — `Unclosed client session` plus "sockets to a bunch of different remote services" is the aiohttp `ClientSession` story almost every time. But do **not** skip triage. The exact triage numbers are what you compare against when you ship the fix; without a captured slope, "fixed" is a guess.

Run the steps below in order. Each block stands alone, paste-and-run.

---

## 1. TRIAGE — confirm the leak and pin the dominant FD class

### 1a. Slope (capture this number — you'll need it again in VERIFY)

```sh
kubectl exec -it <pod> -- sh -c 'ls /proc/1/fd | wc -l; cat /proc/1/limits | grep "open files"'
kubectl exec -it <pod> -- sh -c 'for i in $(seq 1 10); do ls /proc/1/fd | wc -l; sleep 30; done'
```

You're expecting confirmation of the ~20/min slope you cited. Write it down.

### 1b. FD type breakdown

```sh
kubectl exec -it <pod> -- sh -c 'ls -l /proc/1/fd | awk "{print \$11}" | cut -d: -f1 | sort | uniq -c | sort -rn'
```

Expected: `socket` dominant, plus `anon_inode` (epoll FDs from event loops) climbing in lockstep. The `anon_inode` climb is the tell that this is a per-client (per-`ClientSession`) leak, not a per-request response leak — each new `ClientSession` constructs its own connector and registers epoll FDs.

### 1c. Top remote endpoints

```sh
kubectl exec -it <pod> -- ss -tn state established \
  | awk 'NR>1 {print $5}' | awk -F: '{print $1}' \
  | sort | uniq -c | sort -rn | head -20
```

Since you said "a bunch of different remote services" — expect many remotes with relatively low counts each, **not** one dominant remote. That's the per-client leak signature (each request constructs its own client; sockets fan out across whatever it called).

### 1d. CLOSE_WAIT (HTTP-specific tell)

```sh
kubectl exec -it <pod> -- ss -tn state close-wait | wc -l
```

If this is also growing, you additionally have responses not being context-managed (the remote closes, but you never read the body to completion or close the response). Note the number.

---

## 2. ROUTE — HTTP/gRPC, Python, aiohttp

`Unclosed client session` is the loud warning aiohttp emits at GC time when a `ClientSession` is garbage-collected without `close()` being awaited. The fact that you see it in logs at all means sessions are being constructed and abandoned. The only question left is *where*.

---

## 3. DIAGNOSE — source audit and live diagnosis, run in parallel

### 3a. Source audit (do this in your editor while live diagnosis runs)

```sh
# Every ClientSession construction site
rg -n 'ClientSession\(' --type py

# Bare requests in async code (also leak, separate bug if present)
rg -n '\baiohttp\.request\(' --type py
```

For each hit, ask: **is this inside a request handler, or inside startup / a long-lived object?** Anything inside a per-request code path is the bug. The legitimate count is "one per upstream service, constructed at app startup."

### 3b. Live diagnosis — surface the allocation site instantly

Two options, pick one. The first is fastest if you can set env vars and bounce the pod; the second runs against the live process you already have.

**Option A — tracemalloc + escalated warnings (one log line ends the investigation):**

Set on the pod:

```
PYTHONTRACEMALLOC=10
PYTHONWARNINGS=always::ResourceWarning
```

Restart the pod. The next `Unclosed client session` warning now carries the **allocation traceback** of the unclosed session — file/line of the offending `ClientSession()` call. Don't leave this on in production once you've shipped the fix; the memory overhead is real.

**Option B — py-spy against the live pod (no restart):**

```sh
kubectl exec -it <pod> -- py-spy dump --pid 1
```

This dumps every coroutine's stack. You're looking for:

- Many coroutines parked inside `aiohttp` request methods → in-flight requests not completing (missing timeout — masquerades as a leak as the client waits forever).
- The function that's constructing the `ClientSession` will usually show up as the parent frame of the suspect coroutines.

If you want to confirm the per-request construction pattern directly, monkey-patch `__init__` for sixty seconds:

```python
import traceback, aiohttp
_orig_init = aiohttp.ClientSession.__init__
def _logged_init(self, *a, **kw):
    print("ClientSession created at:")
    traceback.print_stack()
    return _orig_init(self, *a, **kw)
aiohttp.ClientSession.__init__ = _logged_init
```

Count the printed stacks. More than your service's known startup count = per-request construction confirmed.

### 3c. Asyncio task accounting (one more sanity check)

```python
import asyncio
print(len(asyncio.all_tasks()))
```

If this is climbing in lockstep with FDs, tasks are leaking and each one is holding a connection — usually a missing timeout on `session.get()`.

---

## 4. FIX — singleton ClientSession on FastAPI's lifespan + always-close responses

Three things to land together. Don't ship one without the others — partial fixes will reduce the slope but not flatten it.

### 4a. Hoist `ClientSession` to a process singleton, owned by FastAPI's `lifespan`

```python
# app/clients.py
from contextlib import asynccontextmanager
import aiohttp
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    connector = aiohttp.TCPConnector(
        limit=100,               # total open connections across the process
        limit_per_host=20,       # per upstream host
        ttl_dns_cache=300,
        enable_cleanup_closed=True,  # works around TLS sockets stuck in CLOSE_WAIT
    )
    app.state.http = aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=10),  # MUST have a total timeout
    )
    try:
        yield
    finally:
        await app.state.http.close()
        await connector.close()

app = FastAPI(lifespan=lifespan)
```

`enable_cleanup_closed=True` is load-bearing if you hit any HTTPS upstream. Without it, peer-closed TLS sockets sit in the connector's pool until the next request to the same host, and you see CLOSE_WAIT climb even with a perfectly-managed session.

The total timeout is also load-bearing. Without one, a hung upstream parks a coroutine forever; each parked coroutine holds an FD; the symptom looks identical to a connection leak.

### 4b. Use the singleton from request handlers

```python
# app/routes/things.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/things/{tid}")
async def get_thing(tid: str, request: Request):
    session = request.app.state.http
    async with session.get(f"https://upstream/api/things/{tid}") as resp:
        resp.raise_for_status()
        return await resp.json()
```

Two things to enforce on every call site:

1. **`async with session.get(...)`** — never bare `await session.get(...)` without the context manager. The bare form returns a response object whose socket goes back to the pool only on GC.
2. **Reuse `request.app.state.http`** — never construct a new `ClientSession` inside a handler.

### 4c. Delete every per-request `ClientSession`

For each call site `rg` flagged in §3a that's inside a request handler, replace the construction with the singleton lookup above. This is the actual fix; the rest is plumbing.

### 4d. Catch the next regression in CI

```sh
pytest -W error::ResourceWarning
```

Any test that leaves a `ClientSession` unclosed now fails the build, with the allocation stack if `tracemalloc` is enabled. Cheap, and the only way to keep the leak from coming back the next time someone adds a new outbound call.

---

## 5. VERIFY — slope must be **flat**, not just lower

A reduced slope is still a leak — it just pages someone on a different night.

### 5a. Re-sample FDs under the same load that produced the alert

```sh
kubectl exec -it <pod> -- sh -c 'for i in $(seq 1 20); do ls /proc/1/fd | wc -l; sleep 30; done'
```

Pass criterion: oscillating around a steady state, not climbing monotonically. Ten minutes minimum, ideally an hour at production load.

### 5b. Confirm singleton count

```python
# add a debug endpoint or run from py-spy / a REPL attached to the process
import gc, aiohttp
sessions = [o for o in gc.get_objects() if isinstance(o, aiohttp.ClientSession)]
print(len(sessions))
```

Pass criterion: matches the number of intentional sessions (usually 1, or 1 per upstream service if you sharded the singleton). Before the fix this is hundreds-to-thousands.

### 5c. CLOSE_WAIT must drop to ~0

```sh
kubectl exec -it <pod> -- ss -tn state close-wait | wc -l
```

A residual non-zero count after the fix means there's still a missing close somewhere — usually a `session.get(...)` not wrapped in `async with`, or a response body not being read to completion on the error path. Re-run §3a's grep with the `enable_cleanup_closed` fix already in place to isolate.

### 5d. Final report (for the on-call rotation)

```
RESOURCE:    aiohttp ClientSession (per-process singleton)
LIBRARY:     aiohttp <version>
PATTERN:     per-client leak (ClientSession constructed per request)
CALL SITE:   <file>:<line> from §3a grep
SLOPE BEFORE: +20 FDs/min over 5 min (3000 FDs observed)
SLOPE AFTER:  flat at <N> FDs over 30 min, same load
CLOSE_WAIT:   was <N>, now 0
SINGLETON COUNT: 1 (was several hundred)
WATCH:       process_open_fds for 24h; alert if slope > 5 FDs/min sustained
```

---

## Where to start, concretely

If I had your shell right now, in this order, no waiting:

1. `kubectl exec` and run the §1 triage commands to capture the baseline slope and confirm the FD class is socket + anon_inode.
2. While that's sampling, in another tab: `rg -n 'ClientSession\(' --type py` and skim the hits — the bug is usually obvious from the grep alone.
3. `kubectl exec ... py-spy dump --pid 1` to confirm the suspect handlers are the ones with parked coroutines.
4. Land the §4 fix (singleton + lifespan + `async with` + `enable_cleanup_closed` + total timeout).
5. Re-run §1's sampler under the same load. The slope is your verification artifact.

Two things to push back on if anyone suggests them:

- **"Just raise the FD limit."** Unbounded growth is the leak; the limit is a circuit breaker. Raising it postpones the page and lets the leak compound.
- **"Just raise `limit` on `TCPConnector`."** Same masking. The connector limit is appropriate at ~100 for a busy service; the bug is not the cap, it's that each request builds its own connector.
