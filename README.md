# ak-skills

A growing collection of generic, reusable Claude Code skills.

Each skill is a self-contained directory with its own `SKILL.md`, references, and templates. Skills are symlinked into `~/.claude/skills/` so Claude Code discovers them in any project on this machine.

This repo is the generic counterpart to domain-specific skill repos (e.g. `flink-skills`). Anything domain-bound (Flink, a specific company, a specific stack) belongs elsewhere; this repo holds only skills that work on any codebase.

## Skills in this repo

| Skill | Purpose | Prereqs | Status |
|-------|---------|---------|--------|
| [`plantuml/`](plantuml/) | Generate valid PlantUML for sequence, component, class, state, activity, deployment, ER, use case, and C4 diagrams. Elicits intent when ambiguous, routes by diagram type, enforces structural rules + anti-patterns, emits a render command. | — | active |
| [`system-design/`](system-design/) | Design real production systems end-to-end: elicit constraints → capacity estimate → data model & storage → architecture → scale the one bottleneck → failure modes → ADR-style decisions. Numbers first, anti-overengineering, "boring tech until a constraint forces otherwise." Not interview prep. | — | active |
| [`agent-ready/`](agent-ready/) | Prepare any repository for AI agents: generate a knowledge graph, write a cited `AGENT_DESIGN_DOC.md` (10 sections, every claim traced to `file:line`), optionally produce an `ARCHITECTURE.md` with validated Mermaid diagrams, wire `CLAUDE.md` with the design-doc import + Karpathy Guidelines, then commit only the generated files. Flags: `--skip-understand`, `--skip-commit`, `--architecture`, `--no-split`. | Claude Code plugin: [`Lum1104/Understand-Anything`](https://github.com/Lum1104/Understand-Anything) | active |
| [`connection-leak/`](connection-leak/) | Diagnose and fix connection leaks in JVM (Java/Kotlin) and Python services across three resource classes: JDBC/DB pools (HikariCP, asyncpg, SQLAlchemy), Apache Flink 1.18 operator lifecycle (`RichFunction.close`, AsyncIO, RocksDB iterators), and HTTP/gRPC clients (OkHttp, Apache HC, Netty, gRPC, ktor, aiohttp, httpx, requests). Runs cross-cutting triage (FD trend, FD classification, runtime ID) before routing to the matching domain reference. Replaces an earlier 4-skill family (`connection-leak-hunt` + 3 siblings). | — | active |
| [`forecast-allocation/`](forecast-allocation/) | Design constrained forecasting + allocation systems — the class where a forecast feeds a planner that allocates scarce supply against committed demand under uncertainty. Modes: DESIGN (cited design doc), PROTOTYPE (runnable Python skeleton with forecaster + planner + simulator), EVALUATE (forecast + planner metrics + perturbation grid). Six phases — ELICIT → ROUTE → FRAME → ANALYZE → EVALUATE → OUTPUT — with research-area refs (forecasting, pacing, cohort representation, allocation optimization, uncertainty, simulation) loaded only when the prompt touches them. Archetype catalog: guaranteed ad delivery, capacity planning, supply-chain allocation, scheduler/quotas. Rejects cohort-ID memorization, one-model-per-cohort, RMSE-only eval, planner-unaware objectives. | — | active |
| [`planner-observability/`](planner-observability/) | The observability counterpart to `forecast-allocation`: design the operational analytics dashboards + monitoring you *see* a forecast/planner/guaranteed-delivery system through. Modes: DESIGN (dashboard design doc — 10 sections), PROTOTYPE (runnable Vite + React + TS app with ECharts, TanStack Query, Zustand, virtualized cohort table, calibrated forecast band — boots with `npm run dev`), AUDIT (critique an existing dashboard against the anti-pattern catalog). Six phases — ELICIT → ROUTE → FRAME → ANALYZE → MEASURE → OUTPUT — with concern refs (information architecture, chart selection, forecast explainability, planner debugging, observability/health, simulation/replay, executive reporting, analytics UX, React architecture) loaded only when touched. Eight dashboard-category catalog (executive-overview … root-cause-analysis). Decision-first not chart-first; explainability over decoration; drill-down over breadth. Rejects vanity metrics, pie-for-non-part-to-whole, uncalibrated uncertainty bands, dead-end overviews, alert fatigue, unvirtualized high-cardinality tables, color-only encoding. | Node/npm (for PROTOTYPE) | active |

## Install

```bash
./install.sh
```

`install.sh` discovers every top-level directory containing a `SKILL.md` and creates a symlink at `~/.claude/skills/<skill-name>/`. Adding a new skill = drop a new top-level directory + re-run `install.sh`.

If you also use Codex, Gemini CLI, or Copilot CLI (which read from `~/.agents/skills/`), pass `--also-agents` to mirror the symlinks there too:

```bash
./install.sh --also-agents
```

Verify:
```bash
ls -l ~/.claude/skills/
ls -l ~/.agents/skills/   # if you used --also-agents
```

Remove the symlinks (without deleting source):
```bash
./uninstall.sh
./uninstall.sh --also-agents   # also remove the ~/.agents/skills/ mirror
```

`uninstall.sh` only removes symlinks pointing into THIS repo, so it's safe to run even if you have other skills installed from elsewhere.

## Adding a new skill

1. Create a new top-level directory (e.g. `mermaid/`).
2. Add a `SKILL.md` at its root with valid frontmatter (`name`, `description`).
3. Follow the authoring pattern documented in [`CONVENTIONS.md`](CONVENTIONS.md): elicitation-first where intent is ambiguous, phase-routed where workflow has stages, templates separated from logic.
4. Re-run `./install.sh`.

## Validating a skill against open-source projects

When changing a skill, generate sample outputs against a handful of well-known open-source projects to eyeball the result before shipping. Drop them in `docs/skill-sample-outputs/`:

```bash
mkdir -p docs/skill-sample-outputs
# Have Claude apply the skill to e.g. Kafka, Redis, nginx, etc.
# Save the generated markdown / .puml / artifacts under that directory.
# Render and review.
```

`docs/skill-sample-outputs/` is gitignored — it's a local sandbox for manual validation, not a checked-in artifact. The repo-tracked equivalent is `evals/` inside each skill, which holds the formal eval set (skill-creator schema).

## Repo layout

```
ak-skills/
├── README.md             ← this file
├── CONVENTIONS.md        ← skill authoring pattern
├── .gitignore
├── install.sh            ← multi-skill aware: symlinks every */SKILL.md
├── uninstall.sh          ← removes only symlinks pointing into THIS repo
├── plantuml/
│   ├── SKILL.md
│   ├── references/
│   └── templates/
├── system-design/
├── agent-ready/
│   ├── SKILL.md
│   ├── references/        ← rules, license attribution
│   ├── templates/         ← the design-doc skeleton
│   ├── scripts/           ← validate-mermaid.sh
│   └── evals/             ← skill-creator eval prompts
├── connection-leak/
│   ├── SKILL.md           ← six-phase router (ELICIT → TRIAGE → ROUTE → DIAGNOSE → FIX → VERIFY)
│   └── references/        ← 00-elicitation, 01-routing, 10-triage, 20-jdbc, 21-flink, 22-http-grpc, 90-anti-patterns, 91-output-contract
└── planner-observability/
    ├── SKILL.md           ← six-phase router (ELICIT → ROUTE → FRAME → ANALYZE → MEASURE → OUTPUT); modes DESIGN / PROTOTYPE / AUDIT
    ├── references/        ← 00-elicitation, 01-routing, 10-18 concern refs, 90-94 support, 99-citations, categories/
    ├── templates/         ← design-doc.md, audit-report.md, prototype/ (runnable Vite + React + TS app)
    └── evals/             ← skill-creator eval set (evals.json)
```

## License

MIT — see [LICENSE](LICENSE).
