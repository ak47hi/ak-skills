# ak-skills

A growing collection of generic, reusable Claude Code skills.

Each skill is a self-contained directory with its own `SKILL.md`, references, and templates. Skills are symlinked into `~/.claude/skills/` so Claude Code discovers them in any project on this machine.

This repo is the generic counterpart to domain-specific skill repos (e.g. `flink-skills`). Anything domain-bound (Flink, a specific company, a specific stack) belongs elsewhere; this repo holds only skills that work on any codebase.

## Skills in this repo

| Skill | Purpose | Status |
|-------|---------|--------|
| [`plantuml/`](plantuml/) | Generate valid PlantUML for sequence, component, class, state, activity, deployment, ER, use case, and C4 diagrams. Elicits intent when ambiguous, routes by diagram type, enforces structural rules + anti-patterns, emits a render command. | active |
| [`system-design/`](system-design/) | Design real production systems end-to-end: elicit constraints → capacity estimate → data model & storage → architecture → scale the one bottleneck → failure modes → ADR-style decisions. Numbers first, anti-overengineering, "boring tech until a constraint forces otherwise." Not interview prep. | active |

## Install

```bash
./install.sh
```

`install.sh` discovers every top-level directory containing a `SKILL.md` and creates a symlink at `~/.claude/skills/<skill-name>/`. Adding a new skill = drop a new top-level directory + re-run `install.sh`.

Verify:
```bash
ls -l ~/.claude/skills/
```

Remove the symlinks (without deleting source):
```bash
./uninstall.sh
```

`uninstall.sh` only removes symlinks pointing into THIS repo, so it's safe to run even if you have other skills installed from elsewhere.

## Adding a new skill

1. Create a new top-level directory (e.g. `mermaid/`).
2. Add a `SKILL.md` at its root with valid frontmatter (`name`, `description`).
3. Follow the authoring pattern documented in [`CONVENTIONS.md`](CONVENTIONS.md): elicitation-first where intent is ambiguous, phase-routed where workflow has stages, templates separated from logic.
4. Re-run `./install.sh`.

## Repo layout

```
ak-skills/
├── README.md             ← this file
├── CONVENTIONS.md        ← skill authoring pattern
├── .gitignore
├── install.sh            ← multi-skill aware: symlinks every */SKILL.md
├── uninstall.sh          ← removes only symlinks pointing into THIS repo
└── plantuml/
    ├── SKILL.md
    ├── references/
    └── templates/
```

## License

MIT — see [LICENSE](LICENSE).
