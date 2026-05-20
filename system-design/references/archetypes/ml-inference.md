# ML inference

Load when the prompt describes online model serving: real-time predictions, feature stores, model versioning, A/B-testing models, "fraud score lookup," "recommendation API."

The defining concern: **serving model predictions within a tight latency budget while keeping training-time and serving-time feature semantics aligned and models versionable, rollback-able, and testable.**

## When this archetype fires

Signal cues:
- "ML inference" / "model serving" / "online prediction" / "real-time scoring"
- "Feature store" / "feature serving"
- "Model versioning" / "deploy model v2" / "shadow traffic"
- "A/B test models" / "champion/challenger"
- "TensorFlow Serving" / "Triton" / "TorchServe" / "Sagemaker endpoint" / "BentoML"
- "Embedding lookup" / "vector search at inference time"
- "Training-serving skew"

Non-signals:
- A batch prediction job (nightly score all users) — that's `batch-etl`, not online inference.
- A simple business-rule scoring (if/else) sold as "ML" — not really this archetype; the design doesn't need the ML-inference machinery.
- LLM API calls to an external provider — the inference concerns shift to the provider; your design is API-integration, not ML serving.

## Additional elicitation (beyond the universal seven)

1. **Inference latency budget.** p50 and p99 of the inference call alone, separate from upstream/downstream. < 10ms requires careful engineering (small model, no remote feature lookups in the hot path); 50–100ms is comfortable; > 200ms suggests online inference may not be the right shape.
2. **Online vs batch inference.** Per-request inference is only required when input is fresh and unpredictable. If the inference input is stable (user profile, item catalog), precompute scores nightly and serve from a fast KV store.
3. **Feature freshness requirements.** Some features are static (user demographics — daily refresh fine); some are real-time (last-N-second activity — sub-second). The freshness spectrum dictates the feature store architecture.
4. **Feature count and source.** How many features per prediction? 10? 200? 2000? Each feature is potentially a separate fetch from the feature store. Round-trip count is often the dominant latency.
5. **Model count and routing.** One model serves all traffic, or multiple models (per-segment, per-experiment)? How is traffic routed?
6. **Versioning and rollback.** How do you deploy model v2? How do you roll back to v1 if v2 produces bad predictions? How fast can rollback happen?
7. **A/B testing or shadow traffic.** Are you running parallel models for evaluation? Shadow traffic (send both, log both, use one) is non-disruptive but doubles compute; A/B (some users see v1, some v2) requires deterministic user→variant assignment.
8. **Training-serving skew prevention.** How do you ensure the features computed at training time match the features computed at serving time? Same code? Same data source? This is the leading cause of bad model performance in production.
9. **Inference compute profile.** Model size, CPU vs GPU, batching tolerance. Batching multiple requests into one GPU call multiplies throughput by 10–100× but adds latency.

## Recurring failure modes

### Training-serving skew

**Symptom.** Model offline metrics look great; online metrics are mediocre or worsening over time. Same model, different inputs.

**Why it happens.** Features computed at training time (Spark batch over historical data) are subtly different from features computed at serving time (real-time computation). Different default values, different timestamp semantics, different filtering rules.

**Mitigation.** Shared feature computation library used by both training and serving; or a feature store that backfills training data from the same code that serves features online. Skew detection: log feature values at serving time, compare distributions to training data weekly.

### Model staleness

**Symptom.** The deployed model is from 6 months ago. The world has moved (seasonal shift, product launch, behavior change). Predictions degrade slowly; no one notices until a quarterly review.

**Why it happens.** Retraining is manual and infrequent. No retraining cadence; no model-performance monitoring.

**Mitigation.** Scheduled retraining cadence (weekly, monthly, depends on domain). Online metrics on production model performance (not just offline test set). Alert when prediction quality drifts.

### Hot model / hot prediction

**Symptom.** One model variant (or one prediction path) gets 90% of traffic; serving infrastructure for that path is saturated while others are idle.

**Why it happens.** Routing logic concentrates on one variant. Cache for one prediction type is hot. One feature has high cardinality but skewed distribution.

**Mitigation.** Even out routing where possible; provision capacity per variant; cache hot predictions explicitly with TTLs that match prediction freshness needs.

### Feature store latency dominates inference

**Symptom.** Model inference itself is 2ms; total request latency is 80ms. Profiling shows 75ms in serial feature lookups.

**Why it happens.** Many features × per-feature round-trip × serial fetching. Sometimes 50+ features per prediction, each as a separate Redis GET.

**Mitigation.** Pipeline / batch feature lookups (one MGET for many features). Co-locate feature store with inference. Reduce feature count (most models tolerate fewer than designers think). Precompute composite features at training time.

### Embedding / vector store hot path

**Symptom.** Inference includes a vector similarity search (top-K nearest neighbors). Search latency dominates total inference time, especially under load.

**Why it happens.** Vector search at high dimensionality + large index is expensive. Approximate-nearest-neighbor structures (HNSW, IVF) help but still have load-dependent latency.

**Mitigation.** Cache top-K results per query for repeated queries; pre-warm the index; size the vector DB for working-set-in-RAM; consider approximate algorithms tuned for latency over recall.

### Untested rollback

**Symptom.** Bad model deployed. Rollback procedure was never tested. Rolling back takes 30 minutes during an incident; meanwhile bad predictions flow.

**Why it happens.** Rollback is rarely exercised in calm periods.

**Mitigation.** Practice rollback monthly. Make rollback a single command (or automatic on metric regression). Always keep the previous model warm and routable.

### Silent model degradation

**Symptom.** Model output distribution drifts (slowly more "positive" labels, or fewer "high-confidence" predictions). No alarm fires; downstream effects accumulate.

**Why it happens.** Output drift looks normal at any single point; only the trajectory is wrong.

**Mitigation.** Track output distribution as a monitored signal. Alert on drift exceeding thresholds. Compare to a baseline (canonical historical day; offline test set distribution).

## What god-tier designers always ask

1. **Online vs batch — is online actually required?** Many predictions can be precomputed. If the input is stable, batch + KV-store-lookup beats online inference on cost and latency.
2. **How do you detect training-serving skew?** "Carefully written code" is not the answer. Logging + distribution comparison is.
3. **What's the rollback procedure, and when was it last tested?** Untested rollback is not rollback.
4. **Feature store consistency: same code in training and serving?** If different code paths, drift is guaranteed.
5. **What metrics gate a model promotion?** Offline metrics (test-set AUC, etc.); online metrics (user engagement, downstream business KPI); guardrails (no segment is severely worse).
6. **GPU vs CPU economics for this model?** GPUs are great for batched inference of larger models; CPUs are simpler and cheaper for small models or low concurrency.
7. **What's the shadow-traffic story for new models?** Send to both, log both, compare. Critical for model changes before customer impact.
8. **What's the model's freshness budget?** Per-day retraining? Per-week? Per-month? The training pipeline cost scales with cadence.
9. **For models with embeddings: how are embeddings versioned with the model?** A model trained on embedding v1 won't work with v2. Both must move together.

## Common pitfalls

### Loading the model on every request

The model file is read from disk and deserialized for each inference. Adds tens to hundreds of milliseconds. The model should load once at service startup and stay in memory.

### Training and serving codepaths diverge

Training uses Python + pandas + scikit-learn; serving uses Java + a re-implementation. Identical bug fixes have to be made twice; subtle differences accumulate. Use a shared feature transformation library, or serve the same code that trained (PyTorch / TF SavedModel / ONNX).

### No model versioning in the artifact registry

The deployed model is "the latest one." Rollback requires finding "yesterday's." Build a model registry (MLflow, BentoML, custom S3 + metadata): every model has a version, a creation timestamp, training metrics, and a path to the artifact.

### Features computed differently in training vs serving

The classic source of skew. Training-time feature: "user's purchases in last 30 days, computed from event log via Spark." Serving-time feature: "user's purchases in last 30 days, computed from Redis cache that may be stale by 6 hours." The cache lag means serving sees a different feature than training did.

### Including a slow external call in the hot path

The hot inference path includes a call to a third-party API (e.g., fraud signal lookup). When that API is slow, your inference is slow; when it's down, your inference fails. Either cache the external signal (and accept staleness) or fall back to a default.

### Untested A/B test routing

"50% of users see model v2." But the routing logic is per-request random, so the same user sees v1 sometimes and v2 sometimes. Statistical analysis is invalid. Use a sticky hash on user ID for deterministic assignment.

### Model serving as the source of truth

Predictions are served and never logged. After 3 months, no one can reproduce what a user saw last Tuesday for debugging. Log predictions with inputs and model version. (Mind privacy / PII — log responsibly.)

## Anchor numbers

- **Online inference latency budget**: typically **10–100ms** for user-facing predictions; **< 10ms** requires aggressive engineering; **> 200ms** suggests batch or async patterns might fit better.
- **Feature store read**: target **< 5ms** per lookup; batch lookups (MGET) make 50+ features feasible within budget.
- **Model server throughput**: small models (logistic regression, tree ensembles) handle **thousands of QPS per replica** on CPU; larger neural nets do **hundreds of QPS per replica**, much higher with GPU batching.
- **GPU batching**: 10–100× throughput improvement at the cost of 10–100ms added latency. Acceptable for non-realtime workloads; not for synchronous user-facing APIs.
- **Model size**: < 100MB models load fast and replicate easily; > 1GB models need careful provisioning. LLMs and large CV models are their own design problem.
- **Retraining cadence**: typically weekly to monthly for behavioral models; daily for rapidly drifting domains (ads, fraud); quarterly for stable domains (demographics).
- **A/B test minimum sample size**: depends on metric variance; often needs **weeks** of traffic at low percentage allocation to detect small effects. Plan accordingly.

## Cross-archetype interactions

- **ML inference + real-time streaming**: streaming feeds feature freshness (last-N-seconds activity computed in Flink, written to feature store, read at inference time).
- **ML inference + multi-tenant**: per-tenant models may be needed for personalization or compliance; balance between one shared model and many per-tenant models (operational cost vs prediction quality).
- **ML inference + observability**: model metrics (prediction latency, feature freshness, output distribution) are first-class observability concerns; standard app metrics miss them.
- **ML inference + batch ETL**: training pipeline IS a batch ETL pipeline. The serving layer reads what training produced.
