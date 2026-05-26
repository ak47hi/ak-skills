# Commit safety (Phase 5)

Skip this entire phase if `--skip-commit` was passed.

## The bash template

Use this verbatim. Do not regenerate it from memory.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Refuse to run if the working tree has uncommitted changes outside the allowlist.
# (We don't want to mix the user's in-progress work into the agent-ready commit.)
#
# Use `-u` (== --untracked-files=all) so untracked DIRECTORIES are listed per-file
# instead of collapsed to "?? dirname/". Without -u, an untracked .understand-anything/
# shows up as a single entry that the allowlist regex can't match, causing a false abort.
DIRTY=$(git status --porcelain -u | awk '{print $2}' | grep -vE '^(\.understand-anything/(config|knowledge-graph|meta|fingerprints)\.json|\.understand-anything/\.understandignore|AGENT_DESIGN_DOC\.md|\.agent-docs/.*\.md|CLAUDE\.md|ARCHITECTURE\.md)$' || true)
if [ -n "$DIRTY" ]; then
    echo "ABORT: working tree has uncommitted changes outside the agent-ready allowlist:"
    echo "$DIRTY"
    echo "Commit or stash these before running /agent-ready, then re-run."
    exit 1
fi

# Build the allowlist of paths to stage (only those that actually exist)
PATHS=()
for p in .understand-anything/config.json \
         .understand-anything/knowledge-graph.json \
         .understand-anything/meta.json \
         .understand-anything/fingerprints.json \
         AGENT_DESIGN_DOC.md \
         CLAUDE.md \
         ARCHITECTURE.md; do
    [ -e "$p" ] && PATHS+=("$p")
done
[ -d .agent-docs ] && PATHS+=(.agent-docs)

if [ ${#PATHS[@]} -eq 0 ]; then
    echo "Nothing to commit — no generated files found."
    exit 0
fi

# Stage exactly the allowlist
git add "${PATHS[@]}"

# Post-stage guard: verify nothing else snuck in (defense in depth against
# pre-existing staged changes or accidental directory expansion).
UNEXPECTED=$(git diff --cached --name-only | grep -vE '^(\.understand-anything/(config|knowledge-graph|meta|fingerprints)\.json|\.understand-anything/\.understandignore|AGENT_DESIGN_DOC\.md|\.agent-docs/.*\.md|CLAUDE\.md|ARCHITECTURE\.md)$' || true)
if [ -n "$UNEXPECTED" ]; then
    echo "ABORT: unexpected files staged:"
    echo "$UNEXPECTED"
    echo "Do NOT auto-unstage. Investigate before retrying."
    exit 1
fi

# Commit. No Co-Authored-By. No --no-verify. No --amend.
git commit -m "feat: make repo agent-ready with knowledge graph auto-update and design doc"

echo "Done. Local commit created. No push performed."
git log -1 --stat
```

## What's allowed

| Path | Source |
|---|---|
| `.understand-anything/config.json` | Phase 1 (understand-anything) |
| `.understand-anything/knowledge-graph.json` | Phase 1 |
| `.understand-anything/meta.json` | Phase 1 |
| `.understand-anything/fingerprints.json` | Phase 1 |
| `.understand-anything/.understandignore` | Phase 1 (bootstrap file the `understand` plugin always creates) |
| `AGENT_DESIGN_DOC.md` | Phase 2 (or slim version from Phase 2.4) |
| `.agent-docs/*.md` | Phase 2.4 (only when split happened) |
| `CLAUDE.md` | Phase 3 |
| `ARCHITECTURE.md` | Phase 2.5 (only with `--architecture`) |

## What's banned (and why)

| Pattern | Why banned |
|---|---|
| `git add .` / `git add -A` / `git add *` | Would grab user's in-progress work; violates "only generated files" rule |
| `git push` (any form) | Local commit only; pushing is the user's decision |
| `git push --force` | As above, plus destructive |
| `--no-verify` | Skipping hooks hides real issues; user's pre-commit hooks exist for a reason |
| `--amend` | Pre-commit hook failures don't roll back the commit — amend would mutate the wrong commit and silently destroy work |
| `Co-Authored-By: Claude` (any variant) | User's global CLAUDE.md hard-bans this trailer. **NO EXCEPTIONS.** Apply silently; never ask "should I add it this time" |

## Failure modes

**Dirty working tree (files outside allowlist modified):** abort with the file list. Do not stash. The user knows what their in-progress work is; stashing it inside the skill is presumptuous.

**Post-stage guard fires:** abort. Do not run `git reset HEAD` to "fix" it — that may unstage legitimate prior staging the user intended. Report and let the user resolve.

**Pre-commit hook fails:** the commit did NOT happen. Do NOT `--amend`. Do NOT re-stage and re-commit silently. Surface the hook output to the user and exit; they decide whether to fix the hook violation and re-run.

**Nothing in the allowlist exists:** print "Nothing to commit" and exit 0. This can happen if every phase was skipped or every artifact already matched what's in HEAD.
