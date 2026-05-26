#!/usr/bin/env bash
# validate-mermaid.sh — wraps `mmdc` to validate a single Mermaid block.
#
# Usage: validate-mermaid.sh <path-to-mmd-file>
#
# Exit codes:
#   0 — block validated successfully, OR `mmdc` is not installed (no-op with warning)
#   1 — block has a syntax error (stderr contains mmdc's complaint)
#   2 — usage error (missing argument)
#
# Why we no-op when mmdc is missing rather than fail:
#   The skill is supposed to produce unvalidated-but-visible diagrams in that
#   case rather than skip the architecture phase entirely. Returning 1 here
#   would cause the skill to flag every block as broken.

set -u

if [ $# -lt 1 ]; then
    echo "usage: $0 <path-to-mmd-file>" >&2
    exit 2
fi

INPUT="$1"

if [ ! -f "$INPUT" ]; then
    echo "validate-mermaid.sh: input file not found: $INPUT" >&2
    exit 2
fi

if ! command -v mmdc >/dev/null 2>&1; then
    echo "validate-mermaid.sh: mmdc not installed; skipping validation. Install with: npm install -g @mermaid-js/mermaid-cli" >&2
    exit 0
fi

# Render to /dev/null to validate without producing output.
# mmdc returns non-zero on syntax errors.
if mmdc -i "$INPUT" -o /dev/null 2>/tmp/mmdc-err.$$; then
    rm -f /tmp/mmdc-err.$$
    exit 0
else
    cat /tmp/mmdc-err.$$ >&2
    rm -f /tmp/mmdc-err.$$
    exit 1
fi
