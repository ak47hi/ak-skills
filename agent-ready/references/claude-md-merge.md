# CLAUDE.md merge (Phase 3)

This is the **only** phase that prompts the user. Get it right.

## Goal

Ensure the project's root `CLAUDE.md` contains:

1. The line `@AGENT_DESIGN_DOC.md` (so Claude auto-loads the design doc into every session in this repo)
2. A `## Karpathy Guidelines` section if not already present

## Steps

### Step 1: read current state

```bash
[ -f CLAUDE.md ] && CURRENT=$(cat CLAUDE.md) || CURRENT=""
```

- If CLAUDE.md doesn't exist → "current" is empty
- If CLAUDE.md exists and already contains `@AGENT_DESIGN_DOC.md` (as its own line, anywhere) AND `## Karpathy Guidelines` heading, **skip Phase 3 entirely**, log "CLAUDE.md already wired."

### Step 2: build the proposed content

The proposed content is the current content, plus whichever of these are missing:

- If `@AGENT_DESIGN_DOC.md` is absent, prepend it as the first line followed by a blank line
- If `## Karpathy Guidelines` heading is absent, append the verbatim Karpathy block from `karpathy-guidelines.md` (the text between the `<<<BEGIN>>>` and `<<<END>>>` markers — do **not** include those markers)

Always add the design-doc line at the top (not interleaved into existing content), and always append Karpathy at the bottom. This ordering keeps file imports together and standardizes the doc-bottom location for the guidelines section.

### Step 3: render the diff

```bash
if [ -f CLAUDE.md ]; then
    diff -u CLAUDE.md /tmp/agent-ready-claude-md-proposed.$$
else
    # New file — show all lines as additions
    sed 's/^/+/' /tmp/agent-ready-claude-md-proposed.$$
fi
```

Wrap the diff in a fenced ```diff block in your message to the user.

### Step 4: ask the user

Call `AskUserQuestion` with:

```json
{
  "question": "Apply this CLAUDE.md change?",
  "header": "CLAUDE.md merge",
  "options": [
    {
      "label": "Yes, apply",
      "description": "Write CLAUDE.md as shown in the diff (design-doc import + Karpathy Guidelines)."
    },
    {
      "label": "No, only add @AGENT_DESIGN_DOC.md",
      "description": "Skip Karpathy. Ensure CLAUDE.md contains only the @AGENT_DESIGN_DOC.md line (append if file exists)."
    },
    {
      "label": "Abort",
      "description": "Stop the skill now. No changes to CLAUDE.md. Phase 4 and 5 will not run."
    }
  ],
  "multiSelect": false
}
```

### Step 5: act on the answer

**"Yes, apply"** → write the proposed content from step 2.

**"No, only add @AGENT_DESIGN_DOC.md"** →
- If CLAUDE.md exists: append `@AGENT_DESIGN_DOC.md` as a new line if it isn't already present (do not modify anything else)
- If CLAUDE.md doesn't exist: create it containing only `@AGENT_DESIGN_DOC.md\n`
- Do **not** add Karpathy

**"Abort"** → stop the skill immediately. Report:
- What was generated in Phases 1, 2, 2.4, 2.5
- That no CLAUDE.md change was made
- That Phase 4 and 5 were not run
- Exit cleanly (not as an error)

## Why the abort path matters

Phase 3 is the user's "I'm not ready to commit to this yet" checkpoint. They might want to inspect the design doc, fix `[NEEDS_CONTEXT]` markers manually, or hold off on Karpathy. Respect that — never sneak the Karpathy block in, never auto-commit after an abort.
