# Cohort representation

Load when the prompt mentions cohorts, segments, ad-group sets, combinatorial cohorts, unseen segments, or set representations.

This is the most-load-bearing reference for guaranteed-ad-delivery and any problem where the unit of allocation is a *set* rather than a single entity.

## The combinatorial problem

A "cohort" is often a *set* of compatible objects:

- Guaranteed ad delivery: a cohort is the **set of ad-groups eligible to serve to a given impression** (defined by market × locale × device × placement × audience × frequency-cap × budget-state × …).
- Capacity planning: a cohort is the set of workloads that share a resource pool.
- Supply chain: a cohort is the set of orders that ship from the same warehouse on the same date.

The number of distinct sets grows combinatorially in the number of constituent attributes. With 20 ad-group eligibility dimensions and binary on each, the upper bound is `2^20 ≈ 10⁶` sets; in practice the cohort distribution is heavy-tailed — most cohorts are extremely rare, a few are extremely common.

**Enumerating cohorts and modeling each one independently fails on three axes simultaneously**: data efficiency (most cohorts have ~zero history), generalization (an unseen cohort has no model), and infrastructure (10⁶ models is operationally untenable).

## Three failed defaults

### Fail 1: One model per cohort

Train an ARIMA / Prophet / GBDT per cohort. Works at 10² cohorts with rich history. At 10⁴+ cohorts with long-tail sparsity:

- 70%+ of cohorts have < 30 observations — classical methods are unfit.
- Cross-cohort signal is wasted (similar cohorts can't share information).
- Unseen-cohort inference is undefined.
- Operational cost (training pipelines, monitoring, rollback) is N× linear in cohort count.

### Fail 2: Cohort ID as a categorical feature

"Just one-hot encode the cohort." Or "use an embedding layer keyed on cohort ID." This gives the model a learnable lookup; it cannot generalize to unseen cohort IDs and it doesn't exploit the *structure* of what a cohort *is*. Two cohorts differing in one attribute look unrelated to the model.

This is the dominant anti-pattern in cohort modeling and is **explicitly banned by this skill**.

### Fail 3: Naive lookup table

Aggregate historical traffic per cohort and use that as the forecast. Strong as a *baseline*, fails as a *system*: no extrapolation, no drift handling, no uncertainty, no generalization.

## The right answers: compositional / factorized / latent

### A. Factorized representation

Represent a cohort by its constituent attributes; let the model compose them.

For ad-delivery: don't forecast `impressions(cohort_id, t)`. Forecast `impressions(market, locale, device, placement, t)` — a tractable cardinality, ~10⁴-10⁵ tuples instead of 10⁶+ cohorts. Compute per-cohort supply at query time by aggregating eligible (market, locale, device, placement) tuples that match the cohort's eligibility.

```
supply(cohort, t) = Σ_{(m,l,d,p) ∈ eligibility(cohort)} impressions(m, l, d, p, t)
```

This converts a 10⁶-cohort forecasting problem into a 10⁴-tuple forecasting problem. The factor structure is **causally meaningful** — actual impressions are generated from these attributes, not from cohort IDs. Generalization to unseen cohorts is automatic because the cohort is just a new aggregation over a known forecast tensor.

**This is the most important compositional pattern in the skill.** Use it whenever cohort growth is combinatorial in named attributes.

### B. Set-based representations

When a cohort is genuinely a set (variable-size membership, no fixed schema), encode it permutation-invariantly:

- **DeepSets** (Zaheer et al.). Embed each element, mean/sum-pool the embeddings, then MLP. Permutation-invariant by construction.
- **Set Transformer** (Lee et al.). Multi-head self-attention with learnable seed vectors. More expressive than DeepSets, more compute.

Use when the cohort's membership is the primary feature (e.g., the cohort is literally "ad-groups {A, B, C}") and elements have their own embeddings (ad-group features).

### C. Latent embeddings with structure

Learn an embedding per fundamental object (ad-group, SKU, segment) — not per cohort. The cohort is represented by an aggregation of its members' embeddings. Two cohorts with overlapping members share signal automatically.

Combine with the factorized approach: per-(market, locale, …) embeddings × cohort-membership aggregation.

### D. Hierarchical / graph structure

If cohorts have a hierarchy or a graph relationship (cohort A is a subset of cohort B, or cohort A overlaps cohort B by N members), exploit it:

- **Hierarchical models.** Shrink each cohort's parameters toward its parent's. The Bayesian default at modest scale.
- **GNN message passing.** Each cohort = a node; edges = shared-membership. Propagate signal over the graph. Strong on overlapping-cohort problems.

Cost: graph construction, training pipeline, debuggability. Justify with the structure being load-bearing.

## Cold-start cohorts via clustering

A brand-new cohort with zero history needs a forecast at serve time. Factorization handles most of this (the cohort is a known aggregation over a known forecast tensor), but when a cohort has *novel* attribute combinations the factorization can still misprice. The fix is to **borrow from the nearest known cluster**:

- **k-means / hierarchical clustering** over cohort embeddings learned across the active population. At serve time, find the new cohort's nearest cluster; use the cluster's pooled forecast as the prior.
- **k-NN on attribute space.** Cheaper; works when cohorts are described by a small fixed attribute vector.
- **Bayesian shrinkage to cluster mean.** Combine a thin per-cohort estimate with the cluster prior weighted by the cohort's history length — the standard hierarchical-Bayes pattern.

Pair this with the **unseen-cohort eval slice** in `91-eval-metrics.md`: a held-out cohort set with zero training observations measures whether the cold-start path actually works.

## Probabilistic / sketch-based cohort approximation

When cohort cardinality genuinely exceeds memory (>10⁷ cohorts, or unbounded due to high-dimensional eligibility intersections), even the factorized representation can overflow. Sketch-based aggregates trade exactness for bounded space:

- **Count-Min sketch** for per-cohort impression counts with bounded multiplicative error.
- **Bloom filter** for cohort-membership queries when only "is this ad-group eligible for this cohort" matters.
- **HyperLogLog** for per-cohort distinct-user counts when reach (not impressions) is the metric.

Reach for these only when factorization itself overflows; otherwise factorization is exact and the sketch is a downgrade. The skill's default is factorized; sketches are the last-resort path.

## Cohort feature engineering

When a global model conditions on a cohort identity, the *features* must be compositional — never the cohort ID itself (anti-pattern A2). The useful features:

- **Set cardinality** (number of ad-groups in the cohort).
- **Entropy / Gini over member weights** — concentrated cohorts behave differently from uniform ones.
- **Overlap metrics** with reference cohorts (Jaccard or cosine over member sets).
- **Dominant-attribute presence** (one-hot encoding of the most common ad-group attribute in the set).
- **Mean / max / sum-pooled member embeddings** (the DeepSets-style aggregation; permutation-invariant).
- **Recency-weighted member features** (newer members weight more — captures cohort drift).

These all generalize to unseen cohorts because they're computed from the members, not from the cohort ID.

## Sparsity handling

For cohorts with < 30 observations (or whatever your threshold is):

- **Borrow strength from siblings.** Hierarchical shrinkage; cohort embeddings learned across all cohorts.
- **Backoff to factorized forecast.** Compute the cohort's forecast from the factor decomposition; no per-cohort fit at all.
- **Confidence-weighted ensemble.** Use the per-cohort model when its uncertainty is tight; fall back to factorized when wide.

**Never report a forecast from a sparse-cohort fit without an uncertainty band.** A point forecast on 5 observations is noise.

## Unseen-cohort generalization

The forecast at serve time for a cohort that wasn't in training data must work. Factorized + set-based + embedding approaches all support this naturally; per-cohort models do not.

Test this explicitly in eval: a held-out set of cohorts that have *zero* training observations. Measure forecast quality on them. If the model fails the unseen-cohort eval, it will fail in production whenever a new ad-group, SKU, or segment is added.

## Anchor numbers

| Cohort count | Sparsity | Default representation |
|---|---|---|
| < 100 | Any | Per-cohort models defensible; even ARIMA per cohort is fine. |
| 100 - 10⁴ | < 30% sparse | Global GBDT + cohort features + cohort embedding. |
| 10⁴ - 10⁶ | Any | Factorized forecast (decompose into 10⁴-10⁵ named factors). |
| > 10⁶ or combinatorial | Any | Factorized forecast + set representation if cohorts are sets. |
| Any cardinality with high unseen-rate | Any | Compositional/factorized only; never enumeration. |

## Anti-patterns (cross-ref `93-anti-patterns.md`)

- One-model-per-cohort at scale.
- Cohort ID as a categorical/one-hot feature.
- Cohort ID as an embedding key (cannot generalize to new IDs).
- Naive lookup table without uncertainty or extrapolation.
- Reporting a per-cohort forecast on < 30 observations without an uncertainty band.
- Forgetting the unseen-cohort eval.
- Picking a set transformer when DeepSets + factorized features beat it (over-engineering — the structure matters more than the model class).
