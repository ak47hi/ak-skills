# Output contract

The final fix report. Same shape regardless of which domain reference was used. The user (or their on-call rotation) should be able to read this and answer three questions: what was leaking, how do we know it's fixed, and what should we look out for next.

## Required sections

```markdown
# Connection leak: <one-line subject>

## What was leaking

- **Resource:** <DB connection | HTTP socket | gRPC stream | RocksDB iterator | Netty ByteBuf>
- **Library:** <HikariCP | OkHttp | ManagedChannel | aiohttp | …>
- **Call site:** `<file>:<line>` — <one-line description of the offending code>
- **Pattern:** <per-request leak | per-client leak | lifecycle leak | scope-too-wide>

## Triage signature (before fix)

- **Slope:** <N> FDs/min over <T> minutes
- **Dominant FD class:** <socket to db:5432 | many remotes | regular files | …>
- **Confirming artifact:** <jstack frame | pg_stat_activity row | MAT instance count | Netty LEAK log line>

## Fix

<paragraph or diff describing the code change>

If applicable, the four cross-cutting patterns this touched:
- [ ] Close-on-every-path discipline (try-with-resources / .use {} / async with)
- [ ] Connection scope shrunk
- [ ] Singleton client hoisted
- [ ] Shutdown hook added

## Verification (after fix)

- **Slope:** flat at <N> FDs (was +<M>/min)
- **Re-run of confirming artifact:** <no idle-in-transaction sessions | OkHttpClient count = 1 | CLOSE_WAIT = 0 | …>
- **Load profile:** <same as original alert | canary at <X>% | staging under synthetic load>

## Watch list

What to watch for after deploying the fix, and for how long:
- Metric: `<process_open_fds | flink_taskmanager_Status_JVM_Threads_Count | HikariCP ActiveConnections>`
- Watch window: <24h | one full traffic cycle>
- Alert: <re-fire if slope > <threshold>>
```

## When to truncate

For obvious / one-line fixes, the "Triage signature" and "Watch list" sections can be one line each. Don't pad. The required structure is there so on-call has a consistent place to look — not so every leak report is a wall of text.

For multi-domain fixes (e.g. one report per leak when two coexisted), produce **one report per resource class**, each with its own triage signature and verification. Combining them confuses verification because the slope from one fix doesn't isolate the contribution of the other.

## What NOT to include

- Generic explanations of connection pools, FDs, or the libraries — the on-call reader knows.
- Speculation about other potential leaks not investigated — file those as follow-up tickets.
- Step-by-step walkthrough of how you arrived at the diagnosis — the verification artifact is what matters; the path doesn't.
- Apologies, hedges, or "we should also consider…" caveats. State what was found and what was fixed.

## Style

Match the rest of the skill: imperative, terse, command-block heavy where evidence is being shown. The report is for an SRE rotation, not a postmortem audience.
