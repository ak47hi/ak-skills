# Cross-cutting triage

Three steps. Always run before opening a domain reference unless the user already pasted the artifact a step would produce.

Triage answers: **Is there a leak? What kind? What tools can we use to diagnose it?**

The leak rate (FDs/min) from step 1 is the number you'll compare against in VERIFY to confirm the fix landed. Capture it before touching code.

---

## 1. Confirm the FD trend

For a JVM or Python process in a pod (Flink TaskManager containers run the JVM as PID 1; Spring services usually do too):

```sh
kubectl exec -it <pod> -- sh -c 'ls /proc/1/fd | wc -l; cat /proc/1/limits | grep "open files"'
```

Sample over several minutes:

```sh
kubectl exec -it <pod> -- sh -c 'for i in $(seq 1 10); do ls /proc/1/fd | wc -l; sleep 30; done'
```

**Interpret:**

| Pattern | Verdict |
|---|---|
| Count flat, oscillating around a steady state | **Not a leak.** User has pool contention, burst load, or sizing. Decline to apply leak fixes; recommend a sizing exercise instead. |
| Count climbs monotonically | **Leak.** Note the slope (FDs/min). That's your baseline for VERIFY. |
| Count climbs in steps tied to a recurring event (checkpoint, restart, deploy) | **Episodic leak.** Almost always a lifecycle hole (Flink `close()`, restart-not-cleaning-up). Route to `references/21-flink.md` even if the pod isn't Flink — same shape applies anywhere with a lifecycle. |

If the user can't `kubectl exec`, but has Prometheus, use:

```promql
process_open_fds{pod="<pod>"}
```

The shape is the same; the source is metrics instead of `/proc`.

---

## 2. Classify the FDs

```sh
kubectl exec -it <pod> -- sh -c 'ls -l /proc/1/fd | awk "{print \$11}" | cut -d: -f1 | sort | uniq -c | sort -rn'
```

Maps each FD to its kernel type. Interpret the dominant class:

| Dominant FD type | Likely domain |
|---|---|
| `socket` only, paired with `anon_inode` (epoll) climbing | HTTP/gRPC (Netty / event-loop) or JDBC — disambiguate by remote (step 2b) |
| `socket` mostly to DB ports (5432, 3306, 1521, 1433) | JDBC → `references/20-jdbc.md` |
| `socket` to many different non-DB remotes | HTTP/gRPC → `references/22-http-grpc.md` |
| Regular files (`/proc/.../fd/N → /var/...`) or `pipe` | Flink (RocksDB iterators, log handles) → `references/21-flink.md` |
| Mixed sockets across many remotes + `anon_inode` | Per-client leak (each new client constructs its own event loop) → `references/22-http-grpc.md` |

### 2b. Get remote endpoints

```sh
kubectl exec -it <pod> -- sh -c 'cat /proc/1/net/tcp | awk "NR>1 {print \$3}" | sort | uniq -c | sort -rn | head -20'
# remote addr is hex: 0100007F:1538 = 127.0.0.1:5432
# decode hex IP: little-endian; pairs of hex digits → decimal, reversed.
```

For human-readable form on a pod with `ss`:

```sh
kubectl exec -it <pod> -- ss -tn state established | awk 'NR>1 {print $5}' | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head
```

**Interpret:**

- One remote dominates → leak to that service. Open that service's domain ref.
- Many different remotes → per-client construction leak (covered in `22-http-grpc.md` § "Distinguishing per-request vs per-client leak").

### 2c. CLOSE_WAIT count (HTTP/gRPC-specific tell)

```sh
kubectl exec -it <pod> -- ss -tn state close-wait | wc -l
```

Growing CLOSE_WAIT count → the **remote** closed the connection but the **local app** never called close. That's a missing `Response` / `ResponseBody` / `Channel` close on the application side, almost always HTTP/gRPC.

---

## 3. Identify the runtime and toolchain

| Runtime | Tools assumed downstream |
|---|---|
| Java / Kotlin / Scala | `jcmd`, `jstack`, `jmap`, async-profiler, JFR, Eclipse MAT |
| Python (asyncio or sync) | `py-spy`, `psutil`, `lsof`, `tracemalloc` |

Quick check (what's installed in the pod):

```sh
kubectl exec -it <pod> -- sh -c 'which jcmd jstack jmap py-spy lsof; ls /tmp/async-profiler* 2>/dev/null'
```

If async-profiler isn't on the image (most JVM images don't ship it), sideload:

```sh
kubectl cp async-profiler-3.0-linux-x64.tar.gz <pod>:/tmp/
kubectl exec -it <pod> -- tar -xzf /tmp/async-profiler-3.0-linux-x64.tar.gz -C /tmp/
```

If `py-spy` isn't on the image, either:

- `pip install py-spy` inside the pod (works on most Python base images).
- `kubectl debug` with an ephemeral container that has py-spy preinstalled.

### Container caveats

`py-spy` and async-profiler need `SYS_PTRACE` capability. On hardened images, this is usually dropped. Add it via:

```yaml
securityContext:
  capabilities:
    add: ["SYS_PTRACE"]
```

…and redeploy. If redeploying is impossible (e.g. you don't own the cluster), fall back to heap-dump-only diagnosis:

```sh
kubectl exec -it <pod> -- jcmd 1 GC.heap_dump /tmp/h.hprof
kubectl cp <pod>:/tmp/h.hprof ./h.hprof
```

…and analyze in Eclipse MAT offline. Each domain reference's "Live-process diagnosis" section documents the heap-dump path as a fallback.

---

## Triage output (what to record)

Before opening a domain reference, write down:

```
LEAK CONFIRMED:
  Pod:         <pod-name>
  Process:     PID 1 (JVM | Python <version>)
  Slope:       <N> FDs/min over <T> minutes
  Dominant:    <socket | regular file | pipe | anon_inode>
  Top remote:  <ip:port> (<service-name>) — <count> FDs
  Toolchain:   <jcmd, jstack, async-profiler> | <py-spy, lsof>
  Verdict:     <route to references/2X-*.md>
```

This becomes the front-matter of the VERIFY report. Anything missing means TRIAGE isn't done.
