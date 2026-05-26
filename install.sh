#!/usr/bin/env bash
# install.sh — symlink every skill in this repo into ~/.claude/skills/
# so Claude Code discovers them from any project on this machine.
#
# Discovery rule: any top-level subdirectory containing a SKILL.md file is
# treated as a skill. Add a new skill = drop a new subdir + re-run this.
#
# Flags:
#   --also-agents  Also mirror symlinks into ~/.agents/skills/ (for users
#                  who run Codex / Gemini CLI / Copilot CLI alongside Claude
#                  Code — those platforms read from ~/.agents/skills/).

set -euo pipefail

ALSO_AGENTS=0
for arg in "$@"; do
    case "$arg" in
        --also-agents) ALSO_AGENTS=1 ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Usage: $0 [--also-agents]" >&2
            exit 1
            ;;
    esac
done

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_HOME="$HOME/.claude/skills"
AGENTS_HOME="$HOME/.agents/skills"

mkdir -p "$SKILLS_HOME"
[[ $ALSO_AGENTS -eq 1 ]] && mkdir -p "$AGENTS_HOME"

found=0
installed=0
skipped=0
errored=0

# link_one: create or refresh a single symlink at $target -> $skill_dir.
# Sets $link_status to "installed", "skipped", or "errored".
link_one() {
    local target="$1"
    local skill_dir="$2"
    local name="$3"
    local home_label="$4"

    if [[ -L "$target" ]]; then
        local existing
        existing="$(readlink "$target")"
        if [[ "$existing" == "$skill_dir" ]]; then
            echo "[$name] already installed in $home_label (symlink correct)"
            link_status="skipped"
            return
        fi
        echo "[$name] replacing stale symlink in $home_label ($existing → $skill_dir)"
        rm "$target"
    elif [[ -e "$target" ]]; then
        echo "[$name] ERROR: $target exists in $home_label and is not a symlink. Move it aside before installing."
        link_status="errored"
        return
    fi

    ln -s "$skill_dir" "$target"
    echo "[$name] installed → $target"
    link_status="installed"
}

for skill_dir in "$PROJECT_DIR"/*/; do
    skill_dir="${skill_dir%/}"
    name=$(basename "$skill_dir")

    # Only treat dirs with a SKILL.md as skills.
    if [[ ! -f "$skill_dir/SKILL.md" ]]; then
        continue
    fi

    found=$((found + 1))

    link_one "$SKILLS_HOME/$name" "$skill_dir" "$name" "~/.claude/skills"
    case "$link_status" in
        installed) installed=$((installed + 1)) ;;
        skipped)   skipped=$((skipped + 1)) ;;
        errored)   errored=$((errored + 1)) ;;
    esac

    if [[ $ALSO_AGENTS -eq 1 ]]; then
        link_one "$AGENTS_HOME/$name" "$skill_dir" "$name" "~/.agents/skills"
        case "$link_status" in
            installed) installed=$((installed + 1)) ;;
            skipped)   skipped=$((skipped + 1)) ;;
            errored)   errored=$((errored + 1)) ;;
        esac
    fi
done

echo
if [[ $found -eq 0 ]]; then
    echo "No skills found (looking for top-level subdirs containing SKILL.md)"
    exit 1
fi
echo "Summary: $found skill(s) found, $installed link(s) installed, $skipped already current, $errored errored"
echo "Verify with: ls -l $SKILLS_HOME"
if [[ $ALSO_AGENTS -eq 1 ]]; then
    echo "         and: ls -l $AGENTS_HOME"
fi
