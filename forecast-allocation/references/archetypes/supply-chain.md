# Archetype: supply-chain allocation

Forecast demand per (SKU, region, time); allocate inventory or fulfillment routing to meet demand under shipping + storage constraints.

## When it fires

- "inventory positioning", "fulfillment routing", "ship-from"
- "SKU × region demand forecast"
- "warehouse allocation", "DC assignment"
- "stockout vs holding cost tradeoff"

This archetype fires when supply is *positioned in advance* and the allocation problem is "which warehouse fulfills which demand."

## Shape

```
Forecast demand(SKU, region, t)
   ↓
Plan inventory placement (which warehouse holds how much)
   ↓
Realize orders; route each to a fulfillment node
   ↓
Pay shipping cost + holding cost; observe stockouts
```

## Additional elicitation

1. **Forecast grain.** Per (SKU × region × day)? Aggregated to category × region? Sparsity per SKU is usually severe — long tail.
2. **Allocation grain.** Inventory positioning (decide stock per warehouse, days ahead) vs real-time routing (assign each order to a warehouse)?
3. **Cost structure.** Shipping cost matrix (origin × destination), holding cost per SKU per day, stockout cost per SKU per missed order.
4. **Substitution.** Can SKU A satisfy demand for SKU B? Adds graph structure.
5. **Lead time.** Replenishment lead time from supplier; routing lead time from warehouse to customer.

## Recurring failure modes

- **Per-SKU independent forecast at high SKU count.** Long-tail SKUs have insufficient history; cross-SKU signal (category, brand) ignored.
- **Inventory plan optimized to mean demand.** Stockouts on tail-side, holding cost from over-stocking on bulk-side.
- **Routing ignores forecast uncertainty.** Greedy nearest-warehouse routing depletes the wrong warehouse on a demand spike.
- **Substitution ignored.** Out-of-stock SKU A's demand absorbed by SKU B isn't accounted for.

## God-tier questions

- "What's the SKU distribution and the per-SKU history depth?" — drives forecast representation.
- "What's the stockout-to-holding cost ratio?" — sets the forecast quantile.
- "Are SKUs substitutable? Is demand correlated across SKUs?" — informs hierarchical/factorized forecast.

## Anchor numbers

| Dimension | Typical range |
|---|---|
| SKUs | 10³ - 10⁷ |
| Regions / warehouses | 10 - 10³ |
| Forecast horizon | Days - weeks |
| Stockout cost vs holding cost | 5× - 50× (stockout usually dominates) |

## Default recipe

1. Hierarchical forecast: category > brand > SKU. Global model with hierarchy features.
2. Quantile loss at q = stockout / (stockout + holding) — translates cost ratio to forecast quantile.
3. Min-cost flow LP for inventory placement; warm-started on the previous solution.
4. Real-time routing: greedy nearest with safety stock thresholds, or LP if the system can afford it.
5. Drift monitor per category; trigger SKU-level re-plan on category-level shift.

Closer to classical inventory theory than to ad-delivery; the allocation problem is min-cost flow rather than dual-priced impression assignment. Cohort representation is hierarchical, not combinatorial.
