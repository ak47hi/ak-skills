# Elicitation

When to ask, what to ask, when to skip. The bar is high: connection leaks are diagnosed by running commands against the live process, not by talking — most of what would have been asked is faster to read off the triage output. Don't ask questions the prompt already pinned down.

## Three axes to pin down

A leak-hunting request is "complete" when these three are derivable:

1. **Runtime** — JVM (Java / Kotlin / Scala) or Python (asyncio or sync). Different toolchains for diagnosis (`jstack` / `jcmd` vs `py-spy`).
2. **Resource class** — JDBC / Flink lifecycle / HTTP-gRPC. TRIAGE step 2 (FD classification) discovers this if you don't already know.
3. **Live pod access** — can the user `kubectl exec` into the leaking pod? Or are they working from logs / metrics / a captured heap dump? Changes which diagnostic commands are usable.

If all three are derivable, skip ELICIT and go straight to TRIAGE.

## Decision: skip or ask

| Signal in the prompt | Action |
|---|---|
| Names a library (HikariCP, OkHttp, aiohttp, `KafkaSource`, `ManagedChannel`…) | Skip elicitation; resource class is known; go to ROUTE via that library's domain reference |
| Pastes an error message with a stack frame from a known library | Skip elicitation; same |
| Pastes `pg_stat_activity` / `SHOW PROCESSLIST` / Netty `LEAK:` log line | Skip elicitation; the artifact is the triage output |
| Says only "FDs climbing" / "Too many open files" / "leak in prod" | Skip elicitation; **start with TRIAGE** — it will classify the resource for you |
| Mentions Flink, TaskManager, JobManager, checkpoint, savepoint | Skip elicitation; runtime is JVM, route via `references/21-flink.md` |
| No runtime indicators in the prompt and no pasted artifact | Ask Q1 (runtime) only |
| Says "production" / "we can't shell in" / "I only have logs" | Ask Q2 (pod access) only — diagnostic depth changes |

**Heuristic:** if a skilled SRE reading the prompt would also need to ask, ask. If they could just start running commands, start running commands.

## The questions, when needed

Phrase as a short numbered list. One round max. If the answer is still ambiguous, make your best guess and explain in the VERIFY summary.

### Q1: Runtime (when not pinned)

```
What's the runtime?
1. JVM — Java / Kotlin / Scala. Uses jstack, jcmd, jmap, async-profiler.
2. Python — asyncio or sync. Uses py-spy, lsof, tracemalloc.
3. Both — mixed-runtime service (rare). I'll cover the dominant one first.
```

### Q2: Pod access (when only logs are available)

```
What access do you have to the leaking pod?
1. `kubectl exec` into a live pod (full diagnosis available).
2. Only logs + Prometheus metrics (we'll lean on metrics + leak-detection thresholds).
3. Only a captured heap dump from a crashed pod (we'll do post-mortem in MAT).
```

This is rarely worth asking — most users default to (1). Ask only if the prompt explicitly says "we can't shell in" or "this happened overnight, the pod is gone".

## What NOT to ask

Don't ask:

- **Which library** — TRIAGE step 2 (FD classification + remote endpoint list) identifies it.
- **Pool size / `ulimit -n`** — irrelevant to the leak itself; matters only for "should we raise it" anti-pattern conversations (decline those).
- **How many users / what's the QPS** — leak symptoms scale with traffic but the bug is the bug regardless.
- **K8s vs ECS vs bare metal** — `/proc/1/fd` exists on Linux regardless of orchestration; the commands transfer.
- **What metrics they have** — TRIAGE produces its own ground truth from `/proc`.

These are decisions or facts that don't change the diagnosis path. Asking them wastes a turn.

## Propose-and-go (alternative to questions)

For mildly ambiguous prompts, prefer **propose-and-go** over a question:

> "Treating this as a JVM service since you mentioned Spring Boot. Running the cross-cutting triage commands now; tell me if you're actually on Python and I'll switch the diagnostic toolchain."

This keeps the conversation moving — leak hunting is time-sensitive, the user usually wants commands to run, not a questionnaire.

## When the user pastes a triage artifact

If the prompt already contains:

- A `lsof` / `ss` dump showing FD types and remote endpoints
- A `jstack` output with the offending thread
- A `pg_stat_activity` row with `idle in transaction` and elapsed time
- A heap dump's instance count for `OkHttpClient` or `ManagedChannelImpl`
- A Netty `LEAK:` log block

…you're already past TRIAGE. Go straight to ROUTE using the artifact as the triage signature. Don't re-run the same commands the user already ran.
