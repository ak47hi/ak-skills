# Design: <system name>

Owner: <name or team>
Date: YYYY-MM-DD
Status: Draft | Reviewed | Approved | Superseded

---

## 1. Problem framing

<One paragraph. What does this system do? What does it consume (forecast inputs, demand commitments)? What does it produce (allocation decisions)? Where does it sit operationally — between which producer and which planner-consumer?>

## 2. Constraints + assumptions

Per the seven dimensions from `references/00-elicitation.md`. Every inferred value is flagged.

| Dimension | Value | Source |
|---|---|---|
| Forecast horizon + cadence | <e.g., daily horizon 7 days out, hourly refresh> | given / inferred |
| Cohort cardinality + sparsity | <e.g., ~50k cohorts, 70% with <30 obs/wk> | given / inferred |
| Planner objective + constraints | <e.g., min underdelivery s.t. ≤3 replans/cohort/day> | given / inferred |
| SLO | <e.g., underdelivery ≤2% per campaign, p95> | given / inferred |
| Data shape | <e.g., 18-month history, +1-day label lag, censored on caps> | given / inferred |
| Latency budget | <e.g., 10 ms forecast inference, 1 min planner solve> | given / inferred |
| Operational reality | <e.g., 3-person ML team, weekly retrain, PyTorch + Ray stack> | given / inferred |

Archetype: <none / guaranteed-ad-delivery / capacity-planning / supply-chain / scheduler-quotas>

## 3. Mathematical framing

### Forecast

<Objective. Define ŷ, y, the loss L. State conditioning (per-cohort / global / factorized). State output shape (point / quantile / distribution).>

### Planner

<Optimization objective. Decision variables. Hard constraints. Soft costs (smoothness, churn). Loss asymmetry if any.>

### Coupling

<How does the forecast output feed the planner input? Quantile? Distribution? Single point?>

## 4. Approach comparison

Two or more candidate approaches, comparable structure.

### Candidate A: <name>

- **Description.** One paragraph.
- **Scalability.** Memory + compute at the stated cardinality.
- **Sparsity behavior.** How does it degrade as sparse-cohort fraction rises?
- **Planner coupling.** How does forecast error propagate into planner output?
- **Operational cost.** Training, serving, monitoring, on-call surface area.
- **Reference.** `references/<area>.md`

### Candidate B: <name>

- (Same structure)

### Candidate C: <name> (if applicable)

- (Same structure)

## 5. Recommended approach

<Which candidate ships. The binding constraint that picked it. The sacrifice accepted. The trigger that would force a switch.>

Per `references/90-tradeoffs.md` template:

- **Binding constraint:** <…>
- **Accepted sacrifice:** <…>
- **Reversal cost:** one-way / two-way door. <Details if one-way.>
- **Monitoring:** <metric that confirms the decision is working / would force a change>

## 6. Scalability analysis

<Memory + compute estimates at the stated cohort cardinality + event rate. Identify the binding bottleneck. The one thing to deep-dive.>

- Forecast model size: <…>
- Forecast inference QPS at peak: <…>
- Planner solve time at expected commitment count: <…>
- Storage footprint: <…>
- Training time per retrain: <…>

**Binding bottleneck:** <name the one piece that constrains the design>

## 7. Data requirements

- **History depth needed:** <e.g., 90 days minimum for stable seasonality fit>
- **Features:** lag, calendar, regime, cohort attributes, embeddings — name them.
- **Label availability lag:** <e.g., +1 day for delivery confirmation>
- **Retraining cadence:** <…> — operated by <team> via <pipeline>
- **Data quality monitors:** <what's checked, what triggers alerts>

## 8. Failure modes

Per dependency / per assumption: how does it fail, blast radius, degradation strategy.

| Failure | Blast radius | Detection | Degradation |
|---|---|---|---|
| Forecast pipeline broken (training fails) | All cohorts affected | drift monitor / training-success alert | Fall back to last-known-good forecast |
| Forecast drifts (regime shift undetected) | Subset of cohorts | per-cohort calibration monitor | Trigger retraining; widen pacing buffer |
| Planner solver times out | All allocation for the tick | solve-time alert | Use previous-tick allocation; alert on repeat |
| Cohort introduction (new cohort, no history) | Specific cohort | unseen-cohort eval / serving log | Factorized backoff handles automatically |
| Sim ≠ prod (recently silently diverged) | Affects new launches | reproducibility check on baselines | Recalibrate sim; freeze launches until sim re-baselines |

## 9. Evaluation plan

### Forecast metrics (Table 1)

| Metric | Slice | Target |
|---|---|---|
| Pinball loss (q=0.5, q=0.9) | aggregate, per-cohort decile, per-horizon | <…> |
| CRPS | aggregate, per-cohort tier | <…> |
| Coverage at 90% | per-cohort tier | 0.88 - 0.92 |
| Bias | aggregate, by regime | within ±2% |

### Planner metrics (Table 2)

| Metric | Slice | Target |
|---|---|---|
| Underdelivery % | per commitment, p95 | ≤2% |
| Replan churn | per cohort per day | ≤3 |
| Smoothness | aggregate | <…> |
| Planner regret vs oracle | aggregate | <≤X%> |
| SLA violation count | per commitment tier | <…> |

### Baselines

- Production system (current state)
- Even-pacing
- Oracle planner (ground-truth supply)

Per `references/91-eval-metrics.md`.

## 10. Simulation strategy

- **Strategy:** <replay / Monte Carlo / synthetic / counterfactual planner replacement>, per `references/15-simulation.md`.
- **Perturbation grid:** forecast error magnitudes (0%, 5%, 10%, 20%), drift scenarios (stationary, gradual, regime shift), traffic shocks.
- **Sim calibration check:** the sim reproduces production baseline metrics within <X%> before being trusted.
- **Cadence:** every model PR runs the sim; every planner change runs the full perturbation grid.

## 11. Open questions

<Inferred constraints to confirm. Deferred decisions with a trigger (e.g., "revisit cohort embedding dimension when CRPS plateaus"). Risks not yet mitigated.>

---

## Appendix: anti-pattern check

Walked against `references/93-anti-patterns.md`:

- [ ] No one-model-per-cohort at scale
- [ ] No cohort ID as categorical / embedding key
- [ ] Forecast loss matches planner asymmetry
- [ ] Planner consumes uncertainty (not just point forecast)
- [ ] Calibration measured (PIT / coverage / CRPS)
- [ ] Drift monitor wired in
- [ ] Replan-churn control in place
- [ ] Two-table eval (forecast + planner)
- [ ] Sim calibrated against production baselines
- [ ] Fallback when forecast fails
