# Plantuml skill — 5-iteration validation & refinement summary

Date: 2026-05-26.  Eval set: 6 focused cases (see `../plantuml/evals/evals.json`).
Each iteration ran 6 unbiased subagents in parallel; outputs graded against the per-case assertion lists.

## Headline

| Config | Pass | Asserts | Tokens | Time |
|---|---|---|---|---|
| baseline-no-skill      | 2P/3Pa/1F | 29/36 | 151,131 | 174.4s |
| iteration-1            | 6P/0Pa/0F | 36/36 | 230,793 | 269.1s |
| iteration-2            | 6P/0Pa/0F | 36/36 | 229,875 | 245.9s |
| iteration-3            | 6P/0Pa/0F | 36/36 | 212,680 | 226.2s |
| iteration-4            | 6P/0Pa/0F | 36/36 | 204,453 | 250.4s |
| iteration-5            | 6P/0Pa/0F | 36/36 | 209,658 | 226.5s |

**Iter-1 vs no-skill baseline**: +4 PASS cases, +7 passing assertions (29 → 36 / 36).
**Iter-5 vs iter-1**: token cost -9.2% (21,135 tokens saved per 6-case run); time -15.8%; pass rate held at 6/6.

## Refinements applied each iteration

Every refinement was evidence-driven from the prior iteration's transcripts, not speculative.

**Iter-1 — baseline measurement.** No skill changes; established the starting line.
  - Win vs no-skill: baseline used the *deprecated* `#COLOR:text;` activity-color form on eval-14; with-skill used the modern `<<#hex>>` form — direct validation that today's 14-activity.md doc additions filled a real gap.
  - Win vs prior `subagent-run-1.json`: case 0 PARTIAL → PASS — the 'cap at 3 candidates' elicitation rule held this time.

**Iter-2 — lint.py W022 false positive on colored participants.** The iter-1 eval-13 subagent flagged that `participant WebApp #AED6F1` (the exact pattern documented in today's coloring section) was being mis-classified as an undeclared participant by `scripts/lint.py:191`. The regex didn't allow a trailing `#color` suffix.
  - Fix: added optional `(\s+#\w+)?` to the declaration regex.
  - Impact: eval-13 time -29% (65.1s → 46.0s) because the subagent no longer had to debug the lint output; overall time -8.6%.

**Iter-3 — moved Changelog out of SKILL.md.** SKILL.md was 196 lines; the trailing changelog was 57 lines (~30%) of historical context that loaded on every invocation.
  - Fix: created `plantuml/CHANGELOG.md`, replaced the inline changelog with a one-line pointer.
  - Impact: tokens -7.4% vs iter-2 (230k → 213k); time -8.0%.

**Iter-4 — tightened color cross-references in `10-sequence.md` and `14-activity.md`.** Transcript review showed eval-13 consistently read `22-styling-colored.md` just to confirm 'inline override is fine here' — a redundant read because today's coloring sections already explained the inline pattern.
  - Fix: rewrote the cross-ref paragraph to say 'inline `#HexColor` is enough — no preset, no extra read' explicitly.
  - Impact: eval-13 tokens 35,793 (-15.5% vs iter-1's 42,338); overall tokens -11.4% vs iter-1.

**Iter-5 — trimmed advanced `!pragma teoz true` section in `10-sequence.md`.** The 12-line section never surfaced in any eval. Compressed to a 3-line paragraph preserving the pointer for power users.
  - Impact: pass rate held 6/6; tokens roughly flat (+2.5% vs iter-4, within natural variance). The trim is mostly future-load savings, not measurable in this small focused set.

## Net change from session start

- `scripts/lint.py` regex fix (1 line) — accepts colored participant declarations.
- `plantuml/CHANGELOG.md` created; `SKILL.md` 196 → 142 lines.
- `references/10-sequence.md` — tightened color cross-ref; compressed teoz section. 239 → 231 lines.
- `references/14-activity.md` — tightened color cross-ref. Net flat.
- `evals/evals.json` — +2 cases (coloring-sequence-participant, coloring-activity-step-status) covering today's doc additions.

## What I deliberately did NOT change

- Elicitation candidate-trimming language. iter-1 produced 3 candidates cleanly (improvement vs prior subagent-run-1 listing 6). The 'cap at 3' rule is working.
- Description / triggering. Out of scope for this 5-iteration pass (separate skill-creator workflow, `run_loop.py`).
- Per-type references beyond what evidence touched. Tempting to trim `18-c4.md` or `20-sprites.md` but no eval signal pointed there.

## Open follow-ups

- The 2 new evals (13, 14) need to be added to the master `evals.json` review and trigger-eval set, if you re-run description tuning.
- Iter-5 eval-13 was 40,090 tokens vs iter-4's 35,793 — variance not regression, but a 3-run average per iteration would tighten the signal next time.
- `scripts/lint.py` could grow a W023 check for the deprecated `#COLOR:text;` activity-color form (would catch the BASELINE failure mode mechanically). Cheap, deterministic, evidence-justified.

