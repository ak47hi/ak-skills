# Executive reporting

Load when the prompt touches exec, KPI, weekly review, risk summary, leadership, one-pager. The exec surface is defined as much by what it **excludes** as what it shows. Its failure mode is not "too sparse" — it's leaking operational detail that the exec can't act on and doesn't want.

## The discipline: curation, not aggregation

An exec view is not the operational dashboard with smaller charts. It answers exactly three questions:

1. **Are we on track?** (delivery vs commitment, this period)
2. **What's the risk?** (forecasted underdelivery, pacing instability, forecast-quality degradation)
3. **Where should I spend attention?** (the one or two things trending wrong)

Every panel earns its place by serving one of those. If a panel answers "what is p99 planner latency on cohort tier 3," it belongs in Tier 2, not here. **Operational detail in an exec view is the defining anti-pattern of this category** — it's the reason leadership calls the dashboard "noisy."

## The exec KPI set

Six to nine KPIs, each a stat-with-target-and-trend, not a raw number:

| KPI | What it answers | Target form |
|---|---|---|
| **Delivery success** | Are commitments being met (on-time, on-budget)? | % of commitments met; target ≥ X% |
| **Underdelivery risk** | Forecasted/real-time risk of missing? | $ or % at risk; target ≤ X% |
| **Pacing stability** | Is delivery smooth or oscillating? | variance / oscillation index vs ceiling |
| **Forecast quality** | Can we trust the forecast driving it all? | calibration / accuracy vs baseline |
| **Inventory utilization** | Are we wasting supply? | utilized / available; target band |
| **Revenue impact** | What's the $ outcome / opportunity cost? | $ delivered + $ at risk |

Each KPI **carries its target/threshold** and is colored (with shape/label, not color alone) by status. A KPI with no target is a vanity metric — "we delivered 4.2M impressions" tells leadership nothing without "against a 4.0M commitment." The delta vs target *is* the decision content.

## Form

- **Trend, not just level.** Each KPI gets a sparkline; "92% delivery, down from 97% last week" is a decision, "92%" is a number.
- **Risk over status.** Lead with what's *going* wrong (forecasted underdelivery) over what *is* (current delivery). Execs steer; they want the leading indicator.
- **One drill, then stop.** An exec KPI deep-links into the Tier-2 health view (same time range, same filter) for the one person who wants to dig — but the exec surface itself stays at six KPIs. The drill is the escape hatch, not the default content.
- **Periodic, often static.** A weekly review can be a generated snapshot (no live refresh); the data freshness is "as of Monday 9am," stated explicitly.

## Anti-patterns this reference exists to prevent

- Operational detail (per-cohort latency, solve times, individual replans) on the exec surface.
- KPI with no target/threshold (a vanity metric).
- Level with no trend (a number, not a decision).
- Status without risk (current delivery shown, forecasted underdelivery omitted).
- Forecast quality / pacing stability omitted because "leadership only cares about delivery" — they care until the forecast silently breaks and delivery follows.
