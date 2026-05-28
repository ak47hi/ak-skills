# Archetype: scheduler with quotas

Forecast tenant resource demand; scheduler allocates compute / IO under per-tenant quotas + fairness + cluster capacity.

## When it fires

- "fair-share scheduler", "DRF (dominant resource fairness)"
- "tenant quota", "per-customer compute budget"
- "batch job placement under quotas"
- "borrowing across queues", "preemption policy"

This archetype fires when *existing* capacity is allocated across competing tenants/queues, not when new capacity is provisioned (that's `capacity-planning`).

## Shape

```
Tenant t submits job j with resource demand r_{t,j} at time τ
   ↓
Forecast(near-term tenant demand)
   ↓
Scheduler assigns: which jobs run now, which queue, which node, possibly with preemption
   ↓
Tenant utility + quota fairness + cluster utilization
```

## Additional elicitation

1. **Quota model.** Hard quotas (tenant capped) vs soft quotas (cap is a fair-share target, but tenants can borrow). DRF? Hierarchical quota tree?
2. **Job size distribution.** Big batch jobs (hours) vs small interactive jobs (seconds)? Different scheduling regimes.
3. **Preemption.** Allowed? At what tier boundary? Sets the planner's degrees of freedom.
4. **SLA per tenant tier.** Latency SLO, throughput floor, fairness guarantee.
5. **Forecast usefulness.** Is tenant demand predictable enough to anticipate? Or is it bursty-uncorrelated?

## Recurring failure modes

- **Forecasting per-job arrivals at fine grain.** Job-level arrival is usually too noisy; aggregate to per-tenant or per-pool rates.
- **Quota tree ignored in forecast.** Sum of children's forecasts doesn't match parent's quota; allocation infeasible.
- **No replan-churn control.** Re-priorities every tick; jobs starve or thrash.
- **Borrowing without payback policy.** A bursty tenant permanently consumes another tenant's share.

## God-tier questions

- "What's the demand predictability — autocorrelated, periodic, or pure burst?" — gates whether forecasting helps at all.
- "What's the cost of latency vs the cost of under-utilization?" — DRF assumes you care about both; sets the weight.
- "Are tenants known in advance, or do new tenants arrive?" — unseen-tenant generalization matters.

## Anchor numbers

| Dimension | Typical range |
|---|---|
| Tenants / queues | 10² - 10⁴ |
| Concurrent jobs | 10³ - 10⁶ |
| Forecast horizon | Minutes - hours |
| Scheduler decision cadence | ms (interactive) - seconds (batch) |

## Default recipe

1. Per-tenant aggregate demand forecast (CPU, mem, IO). Quantile loss tied to the SLA.
2. Hierarchical quota tree as a hard constraint in the planner.
3. DRF or weighted fair queueing as the per-tick allocation rule.
4. Borrow-with-payback policy: tenants can exceed quota when others are under, must yield when others arrive.
5. Sim harness with replay of historical job traces — the only credible eval for scheduler changes.

This archetype is the closest neighbor to a classical scheduler problem (Kubernetes / Borg / YARN). The forecasting layer is often optional — many production schedulers don't forecast and rely on the queue's instantaneous state. If forecast doesn't beat "react to current state," skip the forecast layer.
