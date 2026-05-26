#!/usr/bin/env bash
# uninstall.sh — remove symlinks from ~/.claude/skills/ that point into THIS repo.
#
# Defensive: only removes symlinks whose target is inside this project.
# If you have skills installed from elsewhere with the same name, they're left alone.
#
# Flags:
#   --also-agents  Also remove mirror symlinks from ~/.agents/skills/ that
#                  point into this repo. Same defensive check applies.

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

removed=0
left_alone=0

# unlink_one: remove $target if it's a symlink into this repo.
unlink_one() {
    local target="$1"
    local skill_dir="$2"
    local name="$3"
    local home_label="$4"

    if [[ -L "$target" ]]; then
        local existing
        existing="$(readlink "$target")"
        if [[ "$existing" == "$skill_dir" ]]; then
            rm "$target"
            echo "[$name] uninstalled from $home_label (removed symlink)"
            removed=$((removed + 1))
        else
            echo "[$name] symlink at $target points elsewhere ($existing); leaving it alone"
            left_alone=$((left_alone + 1))
        fi
    fi
}

if [[ ! -d "$SKILLS_HOME" ]] && [[ ! -d "$AGENTS_HOME" || $ALSO_AGENTS -eq 0 ]]; then
    echo "No skill homes found; nothing to do."
    exit 0
fi

for skill_dir in "$PROJECT_DIR"/*/; do
    skill_dir="${skill_dir%/}"
    name=$(basename "$skill_dir")
    if [[ ! -f "$skill_dir/SKILL.md" ]]; then
        continue
    fi

    [[ -d "$SKILLS_HOME" ]] && unlink_one "$SKILLS_HOME/$name" "$skill_dir" "$name" "~/.claude/skills"
    if [[ $ALSO_AGENTS -eq 1 && -d "$AGENTS_HOME" ]]; then
        unlink_one "$AGENTS_HOME/$name" "$skill_dir" "$name" "~/.agents/skills"
    fi
done

echo
echo "Summary: $removed removed, $left_alone left alone (point elsewhere)"
