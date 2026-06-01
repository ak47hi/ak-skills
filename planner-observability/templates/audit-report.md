# Dashboard audit: <surface name>

Reviewer: <name>
Date: YYYY-MM-DD
Surface reviewed: <link / screenshots / description>
Persona it claims to serve: <e.g. pacing on-call> — decision: <…>

---

## Verdict

<One paragraph: does this surface let its persona reach the right decision fast? The single biggest thing helping or hurting.>

## Findings

Ordered by decision-impact (not ease of fix). Each cites the anti-pattern id from `references/93-anti-patterns.md`.

| # | Panel / area | Anti-pattern | Why it harms the decision | Fix | Severity |
|---|---|---|---|---|---|
| 1 | <Channel breakdown pie> | CH1 | 7 near-equal slices — can't tell which channel is underdelivering | Sorted horizontal bar | High |
| 2 | <"Total impressions" hero> | SD1/EXEC2 | A number with no target — leadership can't tell good from bad | Stat + commitment target + wk/wk delta | High |
| 3 | <Forecast line> | EX1/EX2 | No band → planner mis-hedges; reader can't see risk | Add calibrated p10–p90 band + coverage note | High |
| 4 | <Latency panel> | OB1/OB2 | Mean hides the p99 timeouts; no SLA line | p50/p95/p99 + SLA markLine | Med |
| 5 | <Anomaly tab> | OB3/EX3 | Anomalies divorced from metrics; no attribution | Overlay on the metric + attach cohort/input | Med |
| 6 | <Cohort table> | IM2 | 80k rows rendered → tab freezes | Virtualize; server-side past ~100k | Med |
| 7 | <Status colors> | AC1 | Red/green only → fails for colorblind on-call | Add shape + label | Low |

## Prioritized remediation

1. **<High-impact fix>** — <one line>. Unblocks <which decision>.
2. **<next>** …
3. **<next>** …

(Order by how much each accelerates a correct decision. The misleading headline chart outranks the contrast nit.)

## What to keep

<The parts that work — name them. The audit's credibility comes from precision about what's already good, not from blanket condemnation.>
- <e.g. the delivery-curve + pacing-trace pairing is exactly right — symptom over mechanism.>
- <e.g. the time-range filter persists across tabs — good shared-state discipline.>

---

## Anti-pattern coverage checked

Walked the full `references/93-anti-patterns.md` catalog; categories not listed in Findings were checked and passed: <e.g. CH2 dual-axis, IN1 cross-filtering, IM4 state separation>.
