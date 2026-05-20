# Capacity worksheet: <system name>

Author: <name>
Date: YYYY-MM-DD
Status: Draft | Reviewed
Reviewed: <date last refreshed>

> The numbers below are starting points. Validate against actual workload
> measurements before committing capacity. Treat as one significant
> digit of precision.

## Inputs (assumptions flagged as [A])

- **Current scale**: <N> DAU, <N> actions/user/day [A or measured]
- **12-month projection**: <N> DAU, growth rate <X%>/month [A]
- **Peak factor**: peak ≈ <N>× average for human-traffic systems [A unless measured]
- **Average payload size**: <N> bytes inbound / <M> bytes outbound [measured / A]
- **Read : write ratio**: <N>:<M> [measured / A]
- **Working set**: <description of actively-read data scope>
- **Retention**: <N> days/months/years
- **Replication factor**: <N>
- **Index overhead**: <X>× table size [A unless measured]

## Derived numbers

### Peak QPS

```
peak_QPS = (DAU × actions_per_user_per_day × peak_factor) / 86,400
        = (<N> × <N> × <N>) / 86,400
        = <result> QPS
```

Read QPS: <result> × <read_ratio>
Write QPS: <result> × <write_ratio>

### Storage per year

```
storage_per_year = events_per_day × 365 × avg_bytes × (1 + index_overhead) × replication
                = <N> × 365 × <N> × <N> × <N>
                = <result>
```

12-month storage: <result>
3-year storage (if retention is longer): <result>

### Bandwidth at peak

```
peak_bandwidth_in  = peak_QPS × avg_inbound_bytes  = <result>
peak_bandwidth_out = peak_QPS × avg_outbound_bytes = <result>
```

### Working set

```
working_set ≈ active_entities × bytes_per_entity
           = <N> × <N>
           = <result>
```

Does this fit in RAM (cache or DB buffer pool)? [Yes / No / Need <N> GB]

### Concurrency (Little's Law)

```
L = λ × W
  = <peak_QPS> × <avg_latency>
  = <result> concurrent requests
```

Required worker pool size (with <X>× headroom): <result>

## Single-machine baseline check

Compare derived numbers against `references/benchmarks.md` ceilings for
the relevant component:

| Resource | Estimate | Single-instance ceiling | Headroom |
|---|---|---|---|
| Read QPS | <N> | <N> (from benchmarks.md) | <%> |
| Write QPS | <N> | <N> | <%> |
| Storage | <N> | <N> | <%> |
| Bandwidth | <N> | <N> | <%> |
| Working set | <N> | <N> | <%> |

**Verdict**: <fits one box with headroom | needs vertical scaling |
needs distribution justified by HA / geo / blast-radius | exceeds
single-instance limits, distribution required>

## Sources

- `references/estimation.md` (formulas)
- `references/benchmarks.md` (component ceilings, last reviewed YYYY-MM)
- <internal benchmark data, if any>

## Revisit triggers

- When actual production QPS reaches <N>% of peak estimate.
- When projection model materially changes.
- When a new component is added to the critical path.
- At annual capacity review.
