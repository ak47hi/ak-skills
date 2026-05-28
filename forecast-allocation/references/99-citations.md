# Citations

Load when the user asks for literature backing, or when a design needs
to cite the primary source for a method. **Not** loaded by default in
any phase — references in `10-…15-*.md`, `90-93-*.md`, and the
archetypes file link by name into this bibliography.

Each entry is one line: authors, year, title, *what this skill uses it
for*. The "for" clause is the load-bearing part — citations without a
purpose-of-use are decoration.

## Forecasting models

- **Hyndman & Athanasopoulos (2021).** *Forecasting: Principles and
  Practice* (3rd ed.). The reference for ETS, Holt-Winters, ARIMA,
  Theta, exponential smoothing, and the classical statistical baselines
  in `10-forecast.md` rungs 1–2.
- **Taylor & Letham (2018).** "Forecasting at Scale" (Prophet).
  Justifies the Prophet rung; trend + seasonality + holiday
  decomposition.
- **Triebe et al. (2021).** "NeuralProphet: Explainable Forecasting at
  Scale." The Prophet-to-deep upgrade path; used as the rung-3 ceiling
  before climbing to TFT.
- **Makridakis, Spiliotis, Assimakopoulos (2022).** "The M5 accuracy
  competition: Results, findings, and conclusions." Empirical
  justification for the GBDT default at rung 4 — LightGBM-style
  approaches won M5 across hierarchical retail forecasting.
- **Salinas et al. (2020).** "DeepAR: Probabilistic forecasting with
  autoregressive recurrent networks." The RNN-based probabilistic
  forecaster at rung 5.
- **Oreshkin et al. (2020).** "N-BEATS: Neural basis expansion
  analysis for interpretable time series forecasting." Interpretable
  deep forecaster at rung 5.
- **Lim et al. (2021).** "Temporal Fusion Transformers for
  Interpretable Multi-horizon Time Series Forecasting" (TFT). The
  reference transformer for multi-horizon hierarchical forecasting.
- **Nie et al. (2023).** "A Time Series is Worth 64 Words: Long-term
  Forecasting with Transformers" (PatchTST). Patch-based transformer;
  stronger on long-context single-series than per-step attention.
- **Wu et al. (2023).** "TimesNet: Temporal 2D-Variation Modeling for
  General Time Series Analysis." Multi-periodicity modeling for
  series with multiple seasonal cycles.
- **Ansari et al. (2024).** "Chronos: Learning the Language of Time
  Series" (Amazon). The foundation-model-for-time-series approach used
  at rung 6.5 — zero-shot quality on unseen series.
- **Das et al. (2024).** "A decoder-only foundation model for
  time-series forecasting" (Google TimesFM). The second major
  open-weights time-series foundation model.
- **Woo et al. (2024).** "Unified Training of Universal Time Series
  Forecasting Transformers" (Salesforce Moirai). Third foundation
  model; multivariate-capable.

## Hierarchical forecasting / reconciliation

- **Hyndman et al. (2011).** "Optimal combination forecasts for
  hierarchical time series." The original hierarchical reconciliation
  framework cited in `10-forecast.md`.
- **Wickramasuriya, Athanasopoulos, Hyndman (2019).** "Optimal
  Forecast Reconciliation for Hierarchical and Grouped Time Series
  Through Trace Minimization" (MinT). The modern reconciliation
  default; used by name in the hierarchical-forecasting section.

## Guaranteed delivery + pacing (ad-platform lineage)

- **Bharadwaj, Mookerjee, et al. (2010).** "Yield Optimization of
  Display Advertising with Ad Exchange" (Yahoo). Foundational paper
  for guaranteed-delivery yield management.
- **Vee, Vassilvitskii, Shanmugasundaram (2010).** "Optimal Online
  Assignment with Forecasts." Introduces the HWM (high-water-mark)
  algorithm — the canonical analytical pacer cited in `11-pacing.md`.
- **Bharadwaj et al. (2012).** "SHALE: An Efficient Algorithm for
  Allocation of Guaranteed Display Advertising" (KDD). Production
  refinement of HWM with priority and supply-factor structure;
  underpins the Yahoo/LinkedIn GD lineage referenced in
  `11-pacing.md` and the `guaranteed-ad-delivery` archetype.
- **Chen, Berkhin, et al. (2011).** "Real-time bidding algorithms for
  performance-based display ad allocation" (Yahoo). Real-time
  allocation theory adjacent to GD.
- **Lee, Jalali, Dasdan (2013).** "Real time bid optimization with
  smooth budget delivery in online advertising" (LinkedIn). Feedback-
  control pacing — informs the PID / control-theoretic rung in
  `11-pacing.md`.
- **Karande, Mehta, Srikant (2013).** "Optimizing budget constrained
  spend in search advertising." Online matching for ad allocation.
- **Devanur & Hayes (2009).** "The Adwords Problem: Online Keyword
  Matching with Budgeted Bidders under Random Permutations." Random-
  order online LP underpinnings of the dual-decomposed pacer.
- **Agrawal, Wang, Ye (2014).** "A Dynamic Near-Optimal Algorithm for
  Online Linear Programming." Competitive-ratio guarantees under
  i.i.d. arrivals; cited in `13-allocation.md` online primal-dual
  subsection.

## Online matching / primal-dual

- **Mehta (2013).** "Online Matching and Ad Allocation." Survey;
  the standard reference for the family.
- **Buchbinder & Naor (2009).** "The Design of Competitive Online
  Algorithms via a Primal-Dual Approach." Theoretical framework for
  the dual-decomposed pacer in `11-pacing.md` and `13-allocation.md`.
- **Hazan (2016).** *Introduction to Online Convex Optimization*.
  The reference for the online-convex-optimization framing of pacing
  cited in `13-allocation.md`.

## Set / GNN representations

- **Zaheer et al. (2017).** "Deep Sets." Permutation-invariant
  set encoder used in `12-cohort.md`.
- **Lee et al. (2019).** "Set Transformer: A Framework for Attention-
  based Permutation-Invariant Neural Networks." The attention-based
  extension referenced in `12-cohort.md`.
- **Hamilton, Ying, Leskovec (2017).** "Inductive Representation
  Learning on Large Graphs" (GraphSAGE). The GNN reference for
  cohort-graph problems.
- **Veličković et al. (2018).** "Graph Attention Networks." Attention-
  based GNN alternative cited in `12-cohort.md`.

## Uncertainty / conformal / calibration

- **Vovk, Gammerman, Shafer (2005).** *Algorithmic Learning in a
  Random World.* The foundational text for conformal prediction
  cited in `14-uncertainty.md`.
- **Romano, Patterson, Candès (2019).** "Conformalized Quantile
  Regression" (CQR). The method named explicitly in `14-uncertainty.md`
  for combining quantile regression with conformal coverage.
- **Angelopoulos & Bates (2023).** "A Gentle Introduction to Conformal
  Prediction and Distribution-Free Uncertainty Quantification."
  Practical reference for conformal + group-conditional variants used
  in `14-uncertainty.md`.
- **Gneiting & Raftery (2007).** "Strictly Proper Scoring Rules,
  Prediction, and Estimation." Theoretical basis for CRPS and pinball
  loss in `91-eval-metrics.md`.
- **Lakshminarayanan, Pritzel, Blundell (2017).** "Simple and Scalable
  Predictive Uncertainty Estimation using Deep Ensembles." The deep-
  ensembles reference cited in `14-uncertainty.md`.
- **Gal & Ghahramani (2016).** "Dropout as a Bayesian Approximation:
  Representing Model Uncertainty in Deep Learning" (MC dropout). The
  cheap-Bayesian alternative cited in `14-uncertainty.md`.

## Differentiable optimization / planner-coupled loss

- **Amos & Kolter (2017).** "OptNet: Differentiable Optimization as a
  Layer in Neural Networks." The QP-as-a-layer reference for planner-
  coupled training in `13-allocation.md`.
- **Agrawal et al. (2019).** "Differentiable Convex Optimization
  Layers" (cvxpylayers). The production-friendly differentiable-
  convex-optimization library cited in `13-allocation.md`.
- **Donti, Amos, Kolter (2017).** "Task-based End-to-end Model
  Learning in Stochastic Optimization." The task-based learning
  framing — train the forecast to minimize the downstream cost.
- **Elmachtoub & Grigas (2022).** "Smart 'Predict, then Optimize'"
  (SPO / SPO+ loss). Surrogate loss that aligns prediction with the
  downstream linear-optimization objective; cited in
  `13-allocation.md`.

## Stochastic / robust optimization

- **Birge & Louveaux (2011).** *Introduction to Stochastic
  Programming* (2nd ed.). The reference textbook for the two-stage /
  scenario-based formulations in `13-allocation.md`.
- **Shapiro, Dentcheva, Ruszczyński (2014).** *Lectures on
  Stochastic Programming: Modeling and Theory.* Companion text.
- **Ben-Tal & Nemirovski (1998 / 2002).** Foundational robust-
  optimization papers; reformulation of uncertain LPs into tractable
  deterministic equivalents.
- **Bertsimas & Sim (2004).** "The Price of Robustness." The Γ-robust
  LP formulation cited in the `13-allocation.md` robust LP section.

## Drift / non-stationarity

- **Gama et al. (2014).** "A Survey on Concept Drift Adaptation."
  Reference for the feature/prediction/performance drift triad in
  `14-uncertainty.md`.
- **Lipton, Wang, Smola (2018).** "Detecting and Correcting for
  Label Shift with Black Box Predictors" (BBSD). Label-shift
  detection cited in `14-uncertainty.md` drift subsection.

## How to use this file

In a design doc, cite by author + year and the section number from
this file. E.g., "we adopt the dual-decomposed pacer (Buchbinder &
Naor 2009; Bharadwaj et al. 2012)" — readers chase the bibliography
here for the original.

Do **not** include citations as decoration. Every citation should be
attached to a *decision* in the design — the load-bearing reason a
choice was made. Citations on background material belong in an
appendix, not the main design.

## Maintenance

- New entries: keep the one-line format (authors, year, title,
  purpose-of-use). Long abstracts belong in the paper, not here.
- Removed methods: if a reference file stops citing a paper, remove
  the entry. Dead citations rot.
- Versioning: foundation models (Chronos / TimesFM / Moirai) are
  fast-moving — note the date alongside the citation if the field
  shifts substantially.
