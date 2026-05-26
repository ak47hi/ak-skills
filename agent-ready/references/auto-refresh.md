# Auto-refresh behaviour

The `understand-anything` plugin can install a post-commit hook that re-runs `/understand --auto-update` after every commit. This document describes how `agent-ready` artifacts should behave when that hook fires.

## The decision tree

When the auto-update hook re-runs `/understand` and the KG is updated:

```
Did the KG actually change since last run?
├── No  → Do nothing. (understand-anything's fingerprints handle this.)
└── Yes →
    Is AGENT_DESIGN_DOC.md older than .understand-anything/knowledge-graph.json?
    ├── No  → Doc is current relative to KG. Nothing to do.
    └── Yes →
        Does .understand-anything/config.json have "architecture": true
        AND does ARCHITECTURE.md exist?
        ├── Yes → Re-run **only Phase 2.5** (architecture transform).
        │         Do NOT regenerate the design doc — that would discard
        │         [NEEDS_CONTEXT] markers the human has been resolving.
        └── No  → Print:
                  "⚠ AGENT_DESIGN_DOC.md is older than the KG. Consider
                   running /agent-ready --skip-understand --architecture
                   to refresh."
                  Do NOT auto-regenerate the design doc; the human gets
                  to decide when to spend cycles on that.
```

## Why we don't auto-regenerate the design doc

The design doc accumulates human value over time:

- `[NEEDS_CONTEXT]` markers get resolved manually with answers a human knows but the KG doesn't
- Top-10 rules in §5 (after split) reflect human judgment about importance
- Section 1's project description often gets edited for clarity

Blowing all that away on every commit would burn the value the doc accumulates. The hook only auto-refreshes the architecture overview (Phase 2.5), which **is** a pure transform with no human-curated content.

## Why we DO auto-regenerate ARCHITECTURE.md

`ARCHITECTURE.md` is defined as a pure transform of (design doc + KG). It has no human-curated state worth preserving — every Mermaid edge, every box label, every sequence step is derived. So when the KG changes, the architecture overview can and should re-flow.

## Implementation hint for the skill

If the hook integration ever needs to be coded explicitly (rather than relying on the user re-running `/agent-ready`), add a `.understand-anything/post-update.sh` (or whatever path `understand-anything` expects for post-update scripts) that contains:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Only re-run architecture if it was previously generated
if [ -f .understand-anything/config.json ] && grep -q '"architecture": true' .understand-anything/config.json; then
    # Skip understand (already just ran); skip commit (let the user decide)
    /agent-ready --skip-understand --skip-commit --architecture
elif [ -f AGENT_DESIGN_DOC.md ] && [ AGENT_DESIGN_DOC.md -ot .understand-anything/knowledge-graph.json ]; then
    echo "⚠ AGENT_DESIGN_DOC.md is older than the KG. Consider running /agent-ready --skip-understand --architecture to refresh."
fi
```

This is illustrative — verify the actual hook integration point against the `understand-anything` plugin's documented hook API before wiring this up.
