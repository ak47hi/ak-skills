---
name: connection-leak
description: Diagnose and fix connection leaks in JVM (Java/Kotlin) and Python services across three resource classes — JDBC/DB pools, Apache Flink 1.18 operator lifecycle, and HTTP/gRPC clients (OkHttp, Apache HC, Netty, gRPC ManagedChannel, Reactor Netty WebClient, ktor, aiohttp, httpx, requests). Trigger on "Too many open files", FD count climbing, HikariCP `getConnection` timeouts, Netty `LEAK: ByteBuf.release()`, "ManagedChannel was not shutdown properly", `pg_stat_activity` idle-in-transaction climbing, sockets in CLOSE_WAIT, asyncpg/SQLAlchemy pool exhaustion, slow Flink `cancel`, climbing TaskManager thread counts, RocksDB iterator counts climbing, "Unclosed client session", or casual phrasing ("leak", "leaking", "fd count climbing", "pool exhausted"). Cross-cutting triage (FD trend, FD classification, runtime ID) runs before routing to the matching domain reference. Do NOT use for memory leaks unrelated to connections, GC tuning, generic OOM, OS-level FD-limit sizing, or non-JVM/Python runtimes (Go, Node, .NET).
---

# Connection Leak skill

Diagnose and fix connection leaks across JDBC/DB pools, Flink connector lifecycle, and HTTP/gRPC clients in JVM and Python services. Opinionated about three things:

1. **Classify the resource before fixing.** "Too many open files" comes from JDBC, Flink, or HTTP/gRPC — diagnosis paths differ. TRIAGE before DIAGNOSE.
2. **Leaks are bugs, not sizing problems.** Raising `maximumPoolSize`, `ulimit -n`, or the K8s FD limit "fixes" the alert while the leak compounds. Verify the slope, not just the symptom.
3. **Source audit and live diagnosis run in parallel.** Source finds the bug; live process confirms which suspect is the actual offender. Either alone is unreliable.

This skill replaces an earlier multi-skill family (`connection-leak-hunt` + three siblings). Everything is now in one place, routed by `references/01-routing.md`.

---

## Six phases

```
ELICIT    →  Ask only when runtime or pod access is unclear.            references/00-elicitation.md
TRIAGE    →  Confirm leak rate, classify FDs, identify runtime.         references/10-triage.md
ROUTE     →  Triage signature → one domain reference.                   references/01-routing.md
DIAGNOSE  →  Source-code audit + live-process probes, in parallel.      references/20-jdbc.md | 21-flink.md | 22-http-grpc.md
FIX       →  Apply the domain's fix patterns.                           (domain references)
VERIFY    →  Re-sample TRIAGE — slope should be flat.                   references/91-output-contract.md
```

Run in order, once per leak hunt. If the leak is multi-cause (e.g. both a JDBC and an HTTP-gRPC leak on the same pod), finish one cycle end-to-end, then re-enter from ROUTE for the second class. Don't try to handle both classes in one DIAGNOSE pass — the diagnostic commands overlap and the output gets unreadable.

### Fast path (when the pod is on fire RIGHT NOW)

For incident response where the user can't wait for the full workflow, jump to `references/02-fast-path.md` — four commands, a signature → fix-pattern table, and explicit "stop here if your case matches" rules. The fast path is the speed-run, not a shortcut around discipline: it still captures the slope baseline VERIFY needs. Fall back to the full six-phase workflow if your signature doesn't match cleanly.

### Before opening a domain reference — is this even a leak?

Some "leak" symptoms aren't leaks. If TRIAGE shows a flat slope, or CLOSE_WAIT growing only to one slow upstream, or FD spikes that recover on their own — open `references/95-not-a-leak.md` first. Five common false positives (sizing-not-leak, hung-requests-not-leak, deploy-CLOSE_WAIT, normal-small-CLOSE_WAIT, burst-traffic) and a sixth bonus (slowloris / SYN flood). Applying leak fixes to these makes things worse.

### Survive while you fix it

A leak fix often takes hours; the pod is dying now. `references/96-mitigation.md` covers the keep-prod-alive playbook — scheduled restart, leak-detection tightening, aggressive timeouts, time-boxed FD-limit bump, circuit breaker, canary rollback, traffic shed at the LB. Each mitigation requires an explicit exit criterion. Without one, the mitigation **becomes** the new bug.

---

## ELICIT

Read `references/00-elicitation.md`. It defines:
- When the prompt is **complete enough to skip** (resource class + runtime + pod access all derivable from what the user said).
- The **two questions** worth asking when it isn't: runtime (JVM vs Python) and pod access (live `kubectl exec` vs heap-dump-only).
- When to **skip elicitation and start at TRIAGE** — the triage commands themselves disambiguate resource class, so a vague "FDs are climbing" prompt doesn't need a question; it needs the FD-classification command.

The bar to ask is high. If the user pasted a library name (HikariCP, OkHttp, aiohttp, KafkaSource…), an error message with a framework stack frame, or a `pg_stat_activity` dump — you already have enough. Go.

---

## TRIAGE

Read `references/10-triage.md`. Always run TRIAGE before DIAGNOSE unless the user already pasted the artifact triage would produce (top FD-class breakdown, top-N remote endpoints, a `jstack` with an offending thread frame, a Netty LEAK log line).

Triage answers three questions:

1. **Is there actually a leak?** — sample FD count for several minutes. Flat = not a leak; the user has pool contention, burst load, or sizing, and the fix patterns in this skill don't apply.
2. **What resource is leaking?** — classify `/proc/1/fd` entries by type (socket / pipe / file / anon_inode) and remote endpoint. This maps directly to one of the three domain references.
3. **What tools does the runtime support?** — JVM gets `jcmd` / `jstack` / `jmap` / async-profiler / JFR. Python gets `py-spy` / `lsof` / `tracemalloc`.

The leak rate (FDs/min) from question 1 is the number you'll compare against in VERIFY to confirm the fix landed. Capture it before touching anything.

---

## ROUTE

Read `references/01-routing.md`. The triage signature maps to exactly one domain reference:

| Dominant FD / symptom signature | Domain | Reference |
|---|---|---|
| Sockets to DB ports (5432, 3306, 1521, 1433); HikariCP / asyncpg / SQLAlchemy frames in stack | JDBC / DB pool | `references/20-jdbc.md` |
| FD count climbs in lockstep with checkpoint count or job-restart count on a TaskManager pod; slow `cancel`; "Task did not exit gracefully" | Flink lifecycle | `references/21-flink.md` |
| Sockets to non-DB remotes (often many remotes), CLOSE_WAIT growing, Netty `LEAK:` lines, "ManagedChannel was not shutdown properly" | HTTP / gRPC | `references/22-http-grpc.md` |

If signatures overlap (e.g. a Flink job leaking JDBC connections from a sink, or a Spring service leaking both HTTP clients and DB connections), start with the **outer** lifecycle. For Flink, that's `21-flink.md` — the operator's `close()` is the right place to release the connector regardless of whether the leaked resource is JDBC or HTTP. For Spring, start with the resource class that's growing faster; once the dominant leak is fixed, re-route on the remaining slope.

---

## DIAGNOSE

Open the routed domain reference. Each one runs two parallel investigations and ends with fix patterns + a verification protocol specific to that resource class:

- **Source-code audit** — language-aware grep for missing-close patterns in the libraries in scope. Output: a shortlist of suspect call sites.
- **Live-process diagnosis** — connect to the running pod (or read its heap dump) and confirm which suspect is the actual offender. Output: a thread / coroutine name or a heap-dump path that holds the leaked resource.

Both run in parallel because either alone is unreliable. Source-only finds *candidates*; live-only sees *symptoms* but not *call sites*. The intersection is the bug.

---

## FIX

Each domain reference ends with a "Fix patterns" section tuned to that resource class. The four cross-cutting patterns underneath the domain specifics:

1. **Close the resource on every path.** Try-with-resources / `Closeable.use {}` / `async with` / `with`. The exception path is where almost every leak lives.
2. **Shrink the connection scope.** Don't hold a DB connection across an outbound HTTP call. Two short transactions beat one long one. The most common JDBC "leak" is a transaction held across slow I/O.
3. **Singleton long-lived clients.** `OkHttpClient`, `ManagedChannel`, `HttpClient` (Apache HC), `aiohttp.ClientSession`, `httpx.AsyncClient`, `requests.Session`, ktor `HttpClient`, `grpc.aio.Channel` are per-process (or per-upstream-service). Constructing per request leaks the connection pool, dispatcher executor, and DNS cache on every call.
4. **Shutdown hook tied to the process lifecycle.** `@PreDestroy` (Spring), `@Observes ShutdownEvent` (Quarkus), `Runtime.getRuntime().addShutdownHook` (plain JVM), `RichFunction.close()` (Flink), FastAPI `lifespan`, asyncio outermost-task `finally`.

The domain reference says which of these apply and shows the exact pattern in the libraries the user is actually touching.

---

## VERIFY

After applying the fix:

1. **Re-sample FD count** using the same TRIAGE command (`ls /proc/1/fd | wc -l` over 5 minutes minimum, ideally under the same load that produced the original alert).
2. **The slope must be flat, not just lower.** A reduced slope is still a leak; it just runs out of FDs more slowly and pages someone on a different night.
3. **For per-client leaks (HTTP/gRPC singleton fix)** — heap-dump and confirm client instance counts match the number of intentional clients (usually one per upstream service).
4. **For Flink** — restart the job 5× in a row on the same TM pod. FD count must return to baseline between restarts, not step up. See `references/21-flink.md` § "Verification".

Report per `references/91-output-contract.md`:

- The resource that was leaking, the call site (with `file:line`), and the fix applied.
- The before/after slope numbers from triage.
- (Optional) a `jstack` / heap-dump / `py-spy dump` excerpt that proves the suspect is gone.

---

## Anti-patterns (call these out before recommending them)

Read `references/90-anti-patterns.md`. The recurring ones:

- **"Just raise the pool size."** Masks the leak; alert fires later but bigger. Pool size > `(cores * 2) + spindle_count` rarely helps and often hides a bug. HikariCP, asyncpg, SQLAlchemy `QueuePool` all suffer from this.
- **"Just raise `ulimit -n`."** Same shape at the OS level. Unbounded growth is the leak; the limit is a circuit breaker. Raising it without fixing the bug just postpones the page.
- **Catching and swallowing `close()` exceptions.** Looks defensive, actually corrupts the half-open state — a subsequent operation thinks the resource is alive.
- **`@Transactional` on a private method or self-invocation.** Spring proxy interception doesn't trigger; the connection is acquired without managed close timing.
- **Per-request `OkHttpClient` / `ManagedChannel` / `requests.Session` / `aiohttp.ClientSession`.** Leaks the connection pool, dispatcher executor, and DNS cache on every call.
- **Mocking the leak in tests.** Leaks are dynamic; only steady-state load exposes them. Verify in a real environment, not a mocked unit test.

---

## When to push back

- **User asks you to apply a fix without TRIAGE confirming a leak.** Decline; run triage first. If the FD count is flat, they have pool contention or sizing, not a leak, and applying a leak fix can make things worse (e.g. shrinking pool size will surface the contention as user-visible timeouts).
- **User reports a leak and wants the pool size raised.** Decline; explain the masking effect; propose `leak-detection-threshold` (HikariCP) + a 30-day FD-slope trend instead. Pool sizing is a separate conversation from leak hunting.
- **User asks for help on a runtime this skill doesn't cover** (Go, Node, .NET). Decline; the triage commands transfer (they're OS-level), but the source-audit greps and library fix patterns don't.
- **User asks for help on a Flink upgrade rather than a leak.** Route to `flink-redesign` or `flink-dev` siblings if this repo has them, or decline.

These are judgment calls. Comply if the user insists with a reason — but say what's being given up.

---

## Iteration

If the user comes back saying "the slope is still climbing":

1. Re-run TRIAGE. The dominant FD class may have shifted (you fixed leak A, leak B is now dominant).
2. If the same class still dominates, re-enter DIAGNOSE on the same domain reference but escalate the diagnostic depth (heap dump → MAT path-to-GC-roots; async-profiler at allocation site; Netty `paranoid` leak detector).
3. If the slope is flat but pool exhaustion still occurs, the issue is contention/sizing — this is out of scope; recommend a pool-sizing exercise instead.

---

## References at a glance

| File | What it carries |
|---|---|
| `references/00-elicitation.md` | When to ask, what to ask, when to skip into TRIAGE |
| `references/01-routing.md` | Triage signature → domain decision tree; overlap rules |
| `references/02-fast-path.md` | 60-second cheatsheet — 4 commands + signature → fix-pattern table for incidents |
| `references/10-triage.md` | Cross-cutting commands: FD trend, FD classification, runtime/tool inventory |
| `references/20-jdbc.md` | JDBC / DB pool leaks (HikariCP, asyncpg, SQLAlchemy, psycopg) — Java, Kotlin, Python |
| `references/21-flink.md` | Flink 1.18 lifecycle leaks — `RichFunction.close`, AsyncIO timeout, RocksDB iterators, Kafka/JDBC sinks |
| `references/22-http-grpc.md` | HTTP / gRPC leaks (OkHttp, Apache HC, Netty, gRPC, Reactor Netty WebClient, ktor, aiohttp, httpx, requests) — Java, Kotlin, Python |
| `references/90-anti-patterns.md` | Universal: masking with sizing, swallowing close errors, per-request client construction |
| `references/91-output-contract.md` | Final report format — what the fix summary must include |
| `references/95-not-a-leak.md` | False-positive catalog — when the symptom isn't a leak (sizing, hung requests, deploy CLOSE_WAIT, normal small CLOSE_WAIT, burst traffic, slowloris) |
| `references/96-mitigation.md` | Keep-prod-alive playbook while developing the structural fix — every mitigation requires an explicit exit criterion |

---

## Style

Imperative, command-block heavy. Show the audit command, show the fix, move on. Skip primer-style explanations of what a connection pool is — assume the reader knows the runtime they're operating. Comments inside code blocks should be load-bearing — no decorative narration. The original family this skill replaces was deliberately terse; preserve that.
