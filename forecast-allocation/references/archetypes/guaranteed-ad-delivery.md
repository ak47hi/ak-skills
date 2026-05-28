# Archetype: guaranteed ad delivery

The canonical instance of constrained forecasting + allocation, and where the most domain-specific concerns live.

## When it fires

Signals in the prompt:

- "guaranteed delivery", "GD", "reservation campaigns", "direct-sold inventory"
- "ad-group", "campaign", "line item", "advertiser", "impressions"
- "pacing for delivery", "underdelivery rate", "ad-group eligibility"
- "demand-side platform", "supply-side platform" combined with a delivery commitment
- "cohort = ad-groups eligible for impression X" or "ad-group set"

This archetype almost always fires when the user has *signed contracts* for impression delivery (vs. auction-time bidding). If the system is purely auction (RTB), this archetype does not fire — point to a bidding-strategy resource instead.

## The shape

```
Bid request arrives
   ↓ defines (market, locale, device, placement, audience, frequency-cap state)
Eligibility lookup → set of ad-groups eligible to serve = "cohort"
   ↓
Allocation decision: which ad-group (if any) wins this impression
   ↓
Delivery recorded, pacing state updated
```

Cohorts are *sets* of ad-groups — combinatorial growth. A bid request's cohort is determined by the intersection of all ad-group eligibility filters that match.

## Additional elicitation (beyond the universal seven)

1. **Inventory commitment shape.** Per-line-item daily delivery target? Weekly? Total? Smoothness contractually required?
2. **Eligibility dimensions.** How many filter attributes define an ad-group's eligibility? (Market, locale, device, placement, OS, browser, audience segment, frequency cap, …) The product cardinality bounds cohort cardinality.
3. **Concurrent campaigns at peak.** 10³? 10⁵? Sets the planner's commitment count.
4. **Frequency caps and recency rules.** These create state — an ad-group's eligibility for a user depends on what the user has seen recently. Increases cohort cardinality and complicates replay.
5. **Auction interaction.** Is this GD-only, or does it coexist with auction inventory? Hybrid systems have a fairness boundary (GD takes first, auction takes remainder, or proportional share).
6. **Forecast horizon vs commitment horizon.** A campaign committed across a 14-day flight needs 14-day-out forecasts.
7. **Bidding-side vs supply-side.** Are we the publisher (allocating *our* supply) or the buyer (committing to deliver impressions)? Different objective formulations.

## Recurring failure modes

- **Cohort ID memorization.** Treating the cohort identifier as a categorical feature. Generalizes to nothing. See `12-cohort.md` A2.
- **One-model-per-cohort at 10⁵+ cohorts.** Sparsity kills classical methods. Factorize. See `12-cohort.md`.
- **Forecast-proportional pacing under noisy forecasts.** Oscillation, replan churn, frustrated advertisers seeing wildly different daily curves.
- **No fallback when forecast is stale.** A retraining failure silently breaks delivery; advertisers underdeliver before anyone notices.
- **Frequency-cap state ignored in forecast.** Cohort size shrinks as caps fire; static forecasts miss this entirely.
- **Auction-GD interaction modeled as independent.** GD takes the high-value impressions; auction sees a distorted distribution. Auction revenue forecast is wrong.
- **Per-campaign optimization without dual-priced fairness.** Greedy campaigns starve later-arriving ones.

## What god-tier designers always ask

- "What's the factor structure? What attributes generate eligibility?" — to factorize the forecast.
- "What does the planner's loss look like — symmetric or asymmetric under/over-delivery?" — to pick the forecast quantile.
- "Is delivery a hard contract or a soft target?" — hard contracts justify robust optimization; soft targets don't.
- "What's the replan-churn cost per cohort per day, in advertiser-experience terms?" — to calibrate the smoothness penalty.
- "What's the relationship between forecast freshness and underdelivery rate in production today?" — confirms the forecast actually matters; sometimes the pacer is the binding piece.

## Anchor numbers

| Dimension | Typical range |
|---|---|
| Concurrent line items | 10³ - 10⁶ |
| Ad-group eligibility dimensions | 10 - 30 |
| Cohort cardinality (eligibility intersections) | 10⁴ - 10⁷ |
| Factorized forecast dimensionality | 10³ - 10⁵ |
| Pacing replan cadence | Per-minute (real-time) to hourly (batched) |
| Forecast horizon | Hours (intra-day) to 14+ days (flight) |
| Acceptable underdelivery | < 2% per campaign (contractual) |
| Replan churn ceiling | ≤ 3-5 replans per cohort per day |

## Load-bearing recipe (the default design)

1. **Factorize the forecast** into per-(market, locale, device, placement, time) buckets. Forecast that tensor; aggregate to cohort supply at query time.
2. **Quantile loss (pinball) on the forecast** at a quantile chosen to match underdelivery asymmetry (e.g., q=0.8 for "bias high" because under-delivery costs more).
3. **Dual-decomposed online pacer.** Per arriving impression, allocate to `argmax_i (priority_i × λ_i)` over eligible commitments. Subgradient updates on `λ` from observed delivery drift.
4. **Replan-churn control** via dual-variable smoothing (low-pass `λ` updates) or trust-region replan.
5. **Sim harness** for counterfactual planner replacement (fixed traffic, swap pacer) and Monte Carlo over forecast error.
6. **Drift monitoring** on the factor forecast (PSI on input distributions, performance on planner metrics).

This is the production default; deviations need explicit justification per `90-tradeoffs.md`.

## When the user is doing something exotic

- **Header bidding / private marketplace exchanges.** Adds auction-GD interaction complexity; the eligibility set per impression becomes time-varying. Forecast must condition on auction dynamics; planner becomes multi-stage.
- **Brand safety / contextual eligibility.** Adds attribute dimensions to eligibility — same archetype, larger cohort cardinality.
- **Cookieless / privacy-constrained.** Reduces feature dimensionality; cohorts coarsen. Often pushes toward more factor-based forecasting (fewer attributes to factorize, each more important).
- **Self-serve advertiser-set goals.** Adds soft constraints on top of delivery (CPM/CPC/CPA targets); planner becomes multi-objective. May tip into the auction-strategy domain.

If the system has moved that far from contracted impression delivery, consider whether this archetype still fits or whether the request is actually auction strategy (which is out of scope).
