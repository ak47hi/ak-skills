# Archetype: capacity planning

Forecast resource demand; allocate capacity to meet SLOs under bursts at acceptable cost.

## When it fires

Signals:

- "fleet sizing", "capacity reservations", "burst headroom"
- "rightsizing", "cluster autoscale planning"
- "cost vs SLA tradeoff for capacity"

This archetype fires when the *allocation decision* is "how much capacity to provision in advance" rather than "how to assign workloads to existing capacity" (that's `scheduler-quotas`).

## Shape

Demand forecast (CPU, memory, request rate per service or workload) → planner decides reservation quantity per resource pool over a planning horizon → cost vs SLO outcome.

## Additional elicitation

1. **Reservation commitment horizon.** Hourly autoscale? Daily? Multi-month reserved instances? Different problems entirely.
2. **Cost asymmetry.** What does over-provisioning cost (wasted spend) vs under-provisioning (SLO violation)? Almost always asymmetric.
3. **Lead time to provision.** Minutes (autoscale), days (instance ordering), weeks (DC capacity). Forecast horizon must exceed lead time.
4. **Demand shape.** Steady with bursts? Pure burst? Trending? Different forecast models.
5. **Cross-service correlation.** Is demand correlated across services (e.g., shared user load)? Aggregate vs per-service forecast tradeoff.

## Recurring failure modes

- **Point-forecast provisioning under noisy demand.** Provisioning to the mean ⇒ SLO violations 50% of the time.
- **Per-service forecast with no correlation modeling.** Under-provisions globally because per-service buffers don't compose.
- **Reservation horizon shorter than provisioning lead time.** The plan can't react in time.
- **No drift monitor.** A new feature ships, demand pattern shifts, capacity plan is wrong.

## God-tier questions

- "What quantile of demand are we provisioning to, and does that match the SLO?" — translates SLA to forecast quantile.
- "What's the cost of one minute of SLO violation vs one hour of over-provisioning?" — sets the loss asymmetry.
- "How does autoscale interact with the reservation?" — autoscale eats forecast error inside the reservation; underflow only escapes to SLO when both fail.

## Anchor numbers

| Dimension | Typical range |
|---|---|
| Services / resource pools | 10 - 10⁴ |
| Reservation horizon | Hours - quarters |
| Forecast horizon | Lead time + buffer (hours to weeks) |
| Provisioning quantile | p90 - p99 depending on SLA |
| Acceptable over-provisioning | 10% - 30% (cost gate) |

## Default recipe

1. Quantile forecast at the SLA quantile (p95/p99) per resource pool.
2. Capacity plan = max(forecast quantile across the reservation horizon) + safety margin.
3. Autoscale absorbs short-horizon error inside the reserved envelope.
4. Drift monitor on demand pattern; trigger re-plan on shift.

Smaller scale than guaranteed-ad-delivery; the design is usually simpler. The forecast quantile + autoscale combo handles most of it.
