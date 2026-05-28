# Fast path — 60-second triage for incident response

For when the pod is on fire RIGHT NOW and you don't have time to read 8 reference files. Run these four commands, match the signature, jump to the matching fix pattern. **Skip the full workflow only when your case fits one of the five clean signatures below**; ambiguity means open the full SKILL.md workflow.

This is the speed-run, not a shortcut around discipline. The slope capture is non-negotiable — it's what VERIFY compares against.

## The four commands

```sh
# 1. Slope — capture this number; you'll compare against it after the fix.
kubectl exec -it <pod> -- sh -c 'for i in $(seq 1 5); do ls /proc/1/fd | wc -l; sleep 30; done'

# 2. FD class breakdown — what's dominant.
kubectl exec -it <pod> -- sh -c 'ls -l /proc/1/fd | awk "{print \$11}" | cut -d: -f1 | sort | uniq -c | sort -rn'

# 3. Top remotes — one service vs many.
kubectl exec -it <pod> -- ss -tn state established | awk 'NR>1 {print $5}' | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -10

# 4. CLOSE_WAIT count — present (per-request leak) or absent (per-client leak / not a leak).
kubectl exec -it <pod> -- ss -tn state close-wait | wc -l
```

## Signature → action table

Match the four outputs against this table. **First match wins.** If no row fits, your case is ambiguous — fall back to the full workflow (SKILL.md § Six phases).

| Slope | FD class | Top remotes | CLOSE_WAIT | Verdict | Go to |
|---|---|---|---|---|---|
| Flat | any | any | any (small) | **Not a leak.** Pool contention, burst load, or sizing. | `references/95-not-a-leak.md` § "Flat slope, pool exhaustion at peak" |
| Rising | `socket` | DB ports (5432, 3306, 1521, 1433) dominate | irrelevant | **JDBC leak.** | `references/20-jdbc.md` |
| Rising | `socket` | **One** non-DB remote | high & climbing | **Per-request HTTP/gRPC body leak.** Missing close on response/`ResponseBody`/`ClientResponse`. | `references/22-http-grpc.md` § "Source-code audit" |
| Rising | `socket` | **Many** non-DB remotes | ~0 | **Per-client HTTP/gRPC leak.** New `OkHttpClient` / `ManagedChannel` / `WebClient.create()` / `ClientSession` per request. | `references/22-http-grpc.md` § "Singleton clients" |
| Rising in lockstep with restart count, on a TM pod | `socket` + `anon_inode` | any | irrelevant | **Flink operator lifecycle leak.** Missing or partial `close()`. | `references/21-flink.md` |
| Rising | `socket` to **one** remote, growing slowly | one remote | climbing but slow | **Hung requests, not a leak.** Missing timeout + slow upstream. | `references/95-not-a-leak.md` § "CLOSE_WAIT to one remote, coroutines/threads parked in request method" |

## Two-line interpretation cheat-sheet

- **Slope is the leak.** Magnitude is just time elapsed. +2 FDs/min unbounded == +200 FDs/min unbounded; both will exhaust eventually.
- **CLOSE_WAIT presence/absence is diagnostic, not just severity.** Present + climbing = something local isn't closing; absent + climbing = something local is constructing pools per request (each new pool's connections all stay ESTABLISHED).

## When to abandon the fast path

Open SKILL.md and run the full six-phase workflow if:

- The signature doesn't match any table row cleanly.
- Two leaks coexist (slope rising AND CLOSE_WAIT to a separate remote climbing → multi-domain; see `references/01-routing.md` § Overlap rules).
- You can't `kubectl exec` (only logs / metrics / heap dump available — switch to forensic mode).
- The user is not in an active incident (pre-merge review, capacity planning, post-mortem). Fast path is incident-shaped.
- The slope is rising but the symptom doesn't fit (e.g., growth correlates with a specific feature flag, not load).

The full workflow is slower because it's correct under ambiguity. The fast path is faster because it commits to a signature. Don't commit to a signature you can't see.

## After the fix

Re-run command 1 only — that's the dispositive check. If the slope is flat, you're done. If it dropped but isn't flat, you have a second leak or a partial fix — re-enter from SIGNATURE (re-run all four commands).
