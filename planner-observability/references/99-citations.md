# Citations

Load when the user asks for sources, or when a recommendation needs its primary backing. **Not** loaded by default. References in `10-…18-*.md` and `93/94` link here by name.

Each entry: source, *what this skill uses it for*. The "for" clause is load-bearing — a citation without a purpose-of-use is decoration.

## Graphical perception (why these chart choices)

- **Cleveland & McGill (1984).** "Graphical Perception: Theory, Experimentation, and Application to the Development of Graphical Methods." The empirical ranking of encodings — position > length > angle/area > color. The justification for bars-over-pie (`11`, CH1) and for position-based encodings generally.
- **Tufte (2001).** *The Visual Display of Quantitative Information.* Data-ink ratio, chartjunk, small multiples. Backs the anti-chartjunk rules (`11`, CH5) and small-multiples (`11`).
- **Munzner (2014).** *Visualization Analysis & Design.* The what-why-how framework (data type → task → encoding); marks/channels and their effectiveness. The systematic basis for "choose the chart by the decision" (`11`).
- **Few (2006).** *Information Dashboard Design.* Dashboard-specific: curation over decoration, the single-screen discipline, KPI/stat design with context. Backs executive-reporting (`16`) and the vanity-metric/sprawl bans (`93` SD1–SD4).

## Color & accessibility

- **Okabe & Ito (2008).** "Color Universal Design" — the 8-color colorblind-safe qualitative palette. Used for categorical series (`94`).
- **Smith & van der Walt (2015).** The viridis/magma/cividis perceptually-uniform colormaps (matplotlib). Used for magnitude heatmaps (`11` CH4, `94`).
- **WCAG 2.1 (W3C).** Contrast minimums (4.5:1 text, 3:1 graphical) and the non-text-contrast / use-of-color success criteria. The basis for `94` and `93` AC1–AC3.

## Forecast explainability

- **Lundberg & Lee (2017).** "A Unified Approach to Interpreting Model Predictions" (SHAP). The per-prediction feature-attribution panel (`12`, panel 3).
- **Gneiting & Raftery (2007).** "Strictly Proper Scoring Rules, Prediction, and Estimation." CRPS and calibration as proper scoring — the basis for the calibration view (`12`).
- **Reliability diagrams / PIT** — standard calibration diagnostics for probabilistic forecasts; the PIT-histogram and per-quantile-coverage panels (`12`). (See also `forecast-allocation/references/14-uncertainty.md` for the modeling side.)

## Observability & alerting

- **Beyer et al. (2016/2018).** *Site Reliability Engineering* / *The SRE Workbook* (Google). Alert on symptoms not causes; SLO error-budget and burn-rate alerting; multi-window thresholds. The basis for alert design (`14`, `93` OB4).
- **Grafana / Datadog dashboard patterns** — the operational conventions for SRE dashboards: RED/USE-style health grids, percentile latency, SLA reference lines, event overlays. Backs the health-overview and percentile/SLA rules (`14`).

## Cross-skill

- **`forecast-allocation`** (sibling skill in this repo). Designs the forecaster + planner this skill observes. Doc-level reference only — the modeling concepts (calibration, drift, planner regret, replan churn, sim calibration) are defined there; this skill renders them as panels. Several anti-patterns here are the *visualization* of `forecast-allocation` anti-patterns (its D4 per-cohort coverage → EX2; its E4 sim calibration → `15`; its F2 debuggability → `12` panel 3).
