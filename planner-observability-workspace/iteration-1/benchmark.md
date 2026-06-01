# planner-observability — benchmark, iteration 1

Comparative subset: **eval 0** (canonical DESIGN — underdelivery root-cause console) and
**eval 6** (adversarial — "make it 3D and animated"). Each prompt run by a fresh
general-purpose subagent in two conditions — `with_skill` (reads + follows
`planner-observability/SKILL.md`) and `without_skill` (own judgment, forbidden from
reading the skill) — then graded against the eval's assertions. Grader: claude-opus-4-8.

| Eval | with_skill | without_skill |
|---|---|---|
| 0 — underdelivery root-cause dashboard | **7/7 (1.00)** | 4/7 (0.57) |
| 6 — adversarial 3D / animation | **4/4 (1.00)** | 2/4 (0.50) |
| **Total** | **11/11 (1.00)** | **6/11 (0.55)** |

## Where the skill earned its lift

The baseline is genuinely strong — both `without_skill` runs are competent and the eval-0
baseline independently invents a failure-class router and a sound ClickHouse rollup strategy.
The skill's measurable advantage was in the places a strong generalist still misses:

- **Structured completeness.** `with_skill` produced all ten template sections; the baseline
  dropped Accessibility and decision-value Success-metrics entirely, and never walks an
  anti-pattern catalog. The skill turns "a good design" into "a reviewable, complete design."
- **Domain-specific visualization discipline.** The skill produced the allocation-flow Sankey
  and the *calibrated* forecast band (with a coverage note); the baseline used a treemap and
  did not surface calibration. These are exactly the forecast/planner-domain idioms the skill
  encodes from its sibling `forecast-allocation`.
- **Outright rejection of decoration vs partial capitulation.** On the adversarial eval the
  skill declined the animated donut outright (CH1) and named every fired anti-pattern; the
  baseline pushed back on the globe but *kept an animated donut* and cited no rule — the
  classic "reasonable-looking compromise that still ships the wrong chart."

## Honesty notes

- Single run per configuration (n=1); treat pass rates as directional, not precise.
- The 9 other evals in `planner-observability/evals/evals.json` are specified but not yet run
  comparatively (matching how `agent-ready` shipped `evals_run` as a subset of its eval set).
- Token/tool/duration are from the subagent harness usage reports.
- The PROTOTYPE eval (#1) is verified separately and directly: the shipped
  `templates/prototype/` app type-checks and builds (`npm run build` succeeds) — see the
  prototype README. It is not in this comparative subset because grading a runnable app is a
  build check, not an assertion diff.

## Reproduce

Re-run a condition by giving a fresh agent the eval's `prompt` (from `eval_metadata.json`),
for `with_skill` instructing it to read `planner-observability/SKILL.md` first, then grade the
written `outputs/design.md` against the eval's `assertions`.
