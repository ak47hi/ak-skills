# Routing

Pick exactly one domain reference per leak hunt. If the system has two leaks at once, finish one cycle before starting the second — don't try to diagnose both in the same DIAGNOSE pass.

## Triage signature → domain decision tree

Walk top to bottom. First match wins.

```
Are sockets to DB ports (5432, 3306, 1521, 1433) the dominant FD class?
  └─ Yes → JDBC / DB pool                       (references/20-jdbc.md)

Is the pod a Flink TaskManager AND any of:
  · FD count steps up with each job restart
  · slow `cancel`, "Task did not exit gracefully"
  · climbing `flink_taskmanager_Status_JVM_Threads_Count` across restarts
  · operator-named threads alive after cancel
  ?
  └─ Yes → Flink lifecycle                      (references/21-flink.md)

Are sockets to non-DB remotes dominant, OR any of:
  · CLOSE_WAIT count climbing
  · Netty `LEAK: ByteBuf.release() was not called` in logs
  · "ManagedChannel was not shutdown properly" at process exit
  · "Unclosed client session" / "Unclosed connector" (aiohttp)
  ?
  └─ Yes → HTTP / gRPC                          (references/22-http-grpc.md)

Are FDs dominated by regular files or pipes (not sockets)?
  └─ Yes → likely Flink (RocksDB iterators, log handles) → 21-flink.md
         OR generic file-handle leak (out of scope for this skill — see standard close audit)
```

## Overlap rules

### Flink job leaking JDBC connections from a sink

Two correct fixes exist; do them in this order:

1. **Outer fix in `RichFunction.close()`** — the operator's `close()` is the right place to call `connection.close()` regardless of the inner library. Even if the JDBC code is impeccable, a missed operator `close()` defeats it.
2. **Inner fix in the per-record path** — try-with-resources / `Connection.isClosed()` checks per record.

Open `references/21-flink.md` first; it covers the operator-level lifecycle. Cross-reference `references/20-jdbc.md` for the per-record JDBC discipline.

### Flink job leaking HTTP / gRPC clients from a `RichAsyncFunction`

Same shape. Open `references/21-flink.md` for the AsyncIO lifecycle + `timeout()` override; cross-reference `references/22-http-grpc.md` for the singleton-client + shutdown patterns.

### Spring service leaking both DB and HTTP clients

Order by **slope dominance** — fix the faster-growing class first, because that's the one that will exhaust FDs first and dictate the alert. After verification on that class, re-run TRIAGE and route on the remaining slope.

### Python service with both asyncpg pool exhaustion AND aiohttp warnings

The aiohttp warning is louder but usually less urgent. Asyncpg pool exhaustion will block request processing entirely; aiohttp unclosed-session warnings just leak slowly. Fix asyncpg first via `references/20-jdbc.md`, then aiohttp via `references/22-http-grpc.md`.

## Common ambiguities and how to resolve

### "Connection pool timeout" — JDBC or HTTP?

Both pools can time out. Disambiguate by stack frame:

```sh
grep -E 'HikariPool|PgConnection|MysqlConnection|asyncpg|SQLAlchemy' stack.txt   # → JDBC
grep -E 'OkHttpClient.*ConnectionPool|PoolingHttpClient|aiohttp.*connector'      # → HTTP
```

The error message string overlaps; the stack doesn't.

### "Too many open files" with no other hints

Always run TRIAGE step 2 (FD classification). The leading class identifies the domain. Don't guess from the runtime alone — a JVM service can leak any of the three resource classes.

### gRPC leak — is it the channel or the streaming RPC?

Both possible.

- **Channel-construction leak** — `ManagedChannelImpl` instance count > number of upstream services. Per-client leak. Fix per `references/22-http-grpc.md` § "Singleton clients".
- **Streaming-RPC leak** — channel count is correct but HTTP/2 stream concurrency is exhausted. Look for abandoned `Iterator<Response>` from a server-streaming call. Fix per `references/22-http-grpc.md` § "Java — gRPC" § "Streaming RPCs".

### Flink "leak" that's actually a redesign issue

Some Flink complaints look like leaks but are operator-design problems (state explosion, fan-out without keying, broadcast races). If the leak signature doesn't fit any of the three classes and the user describes correctness or shape problems, this is the wrong skill — point at `flink-redesign` if available.

## Multi-domain output

If the leak hunt resolves both a JDBC bug and an HTTP-client bug, produce **two separate fix reports** per `references/91-output-contract.md`, not one combined one. Each report cites its triage slope before/after; combining them confuses verification.
