# Skill authoring conventions

Conventions for skills in this repo. Read this before adding a new skill or editing an existing one.

## Three core patterns

Each skill in this repo follows some mix of three patterns. Pick the ones that fit; don't force a skill into all three.

### 1. Elicitation-first (when intent is ambiguous)

If a request can mean two different things, **ask before generating**. Don't guess and produce a plausible-looking artifact that's wrong in a way the user can only catch by re-reading.

Skip elicitation when the user's prompt already pins down the ambiguous axes. Decision rules for "complete enough to skip" live in each skill's `references/00-elicitation.md`.

**Test:** if a skilled human reading the prompt would also have to ask the same question, the skill should ask.

### 2. Phase-routed (when workflow has stages)

If the skill's work splits into stages with different concerns, name the phases explicitly in `SKILL.md` and route by phase. Example: `ELICIT → ROUTE → GENERATE → VERIFY`.

Phases let the model context-switch deliberately rather than blending stages into one undifferentiated pass.

Don't fake phases. If the work is a single pass, say so.

### 3. Templates separated from logic

Keep the rules of *what* to produce in `references/<topic>.md` and the *shape* of the produced artifact in `templates/<name>.<ext>`.

- `references/` — decision rules, API surface, anti-patterns, output contracts. Markdown.
- `templates/` — the skeleton the agent fills in and emits. Whatever file type the artifact is.

Reasons:
- The agent can load only the reference it needs (progressive disclosure).
- Templates are easy to update without rewriting prose.
- Reviewers can read the rules without wading through example output.

## File layout per skill

```
<skill-name>/
├── SKILL.md           ← entry point: frontmatter + phase flow + reference pointers
├── references/        ← rules, decision trees, API surface, anti-patterns
└── templates/         ← skeletons of the artifact the skill produces
```

Optional: `scripts/` (Python 3 stdlib only, no external deps) when the skill needs deterministic checks.

## SKILL.md frontmatter

```yaml
---
name: skill-name
description: <one paragraph, ≤1024 chars>. Includes both WHAT it does AND specific trigger phrases for WHEN to use it. Ends with a "Do NOT use for ..." clause that routes to siblings or rules out adjacent tooling.
---
```

Description guidance:
- Lead with what the skill produces, then trigger phrases (real prompts a user would type), then an explicit "do not use for" clause.
- Keep it ≤1024 chars (Claude Code's frontmatter limit).
- Be a little "pushy" — Claude tends to undertrigger skills. Include synonyms and casual phrasings.

## Writing style

- Terse, professional. No emoji. No decorative prose.
- Imperative voice in instructions ("Pick the matching template", not "You should pick the matching template").
- Explain the *why* behind rules so the model can extrapolate to edge cases. Heavy-handed MUSTs without reasoning age badly.
- Per-file table of contents only if the file exceeds ~300 lines.

## Cross-skill etiquette

- Skills are self-contained. No cross-skill imports of references, templates, or scripts.
- Doc-level cross-references (markdown links between SKILL.md files) are fine when one skill genuinely consumes another's rules — but prefer pointing the user at the sibling skill rather than restating its content.
- If shared content emerges, add an explicit top-level `shared/` directory and discuss before pulling content in.

## When working in this repo

- Before editing any skill's `SKILL.md`, read it AND its `references/00-elicitation.md` / `references/01-routing.md` (whichever exist) so changes preserve the discipline that makes the skill useful.
- Sanity-check after non-trivial `SKILL.md` edits: description ≤1024 chars, trigger phrases present, "do not use for" clause present.
- Don't add scripts unless they pay for the maintenance cost (deterministic check, runs in CI, replaces a check humans would otherwise eyeball).

## External plugin / tool prereqs

Most skills in this repo are self-contained — they need only Claude Code and standard CLI tools. Some skills (e.g., `agent-ready` invokes the `understand-anything` Claude Code plugin) depend on something a user must install separately.

When a skill has external prereqs:

- **Document them in the `Prereqs` column of the README skills table.** Link to the upstream install instructions. The Prereqs column is the user's one-stop shop for "what do I need before this skill works."
- **Document them in the skill's own SKILL.md error path** so the skill itself surfaces a clear install command if the prereq is missing at runtime. The README documents the prereq *upfront*; the SKILL.md provides the *recovery instruction* when someone tries to run the skill without it.
- **Don't extend `install.sh` to install third-party plugins.** Tool installation is the user's choice; this repo's install.sh only manages symlinks for the skills it owns.

## Third-party content and licensing

If a skill bundles content from a third-party source (e.g., verbatim text from another open-source project), each skill must include `references/THIRD_PARTY_LICENSES.md` enumerating:

- Source URL + canonical home
- License declared by upstream + bundled commit/fetch date
- Full license text (verbatim from upstream's LICENSE file when one exists; otherwise the standard text from a public template plus a note about the upstream gap)
- A one-line attribution comment at the top of the bundled content file pointing at THIRD_PARTY_LICENSES.md

Reproducing the license inside the skill (not at repo root) keeps the attribution co-located with the bundled content. If a skill is later removed or extracted to its own repo, its license attribution travels with it.

## Install-script flags

`install.sh` and `uninstall.sh` support per-platform flags for users who run multiple agent platforms:

- Default: symlinks into `~/.claude/skills/` only.
- `--also-agents`: additionally mirror symlinks into `~/.agents/skills/` (read by Codex, Gemini CLI, Copilot CLI, and other platforms that follow that convention).

When adding new install behaviors, prefer additive flags (opt-in, default behavior unchanged) over expanding the default scope. Existing users shouldn't get surprise filesystem mutations from a `git pull`.

## Eval workspace shape

Each skill's eval workspace (`<skill>-workspace/`) is its own subdirectory at the repo root, tracked alongside the skill itself. Two layouts are valid based on the testing depth used:

**Flat layout** (e.g., `system-design-workspace/iteration-N/eval-N/`) — one set of output files per eval, no with-skill-vs-baseline comparison. Use when testing was qualitative or with-skill-only.

**Comparative layout** (e.g., `agent-ready-workspace/iteration-N/eval-N-name/{with_skill,without_skill}/outputs/` + per-condition `eval_metadata.json` + `grading.json` + `timing.json`, plus a top-level `benchmark.json`) — produced by the canonical `skill-creator` workflow that spawns parallel with-skill and baseline subagents. Use when comparing the skill against a baseline matters and the `eval-viewer/generate_review.py` HTML output is wanted.

Pick whichever matches your testing approach; don't retrofit the other shape for consistency's sake. Always gitignore the generated HTML viewers (`*/review.html`) — they're regenerable from `benchmark.json`.
