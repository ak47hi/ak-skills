#!/usr/bin/env bash
# uninstall.sh — remove symlinks from ~/.claude/skills/ that point into THIS repo.
#
# Defensive: only removes symlinks whose target is inside this project.
# If you have skills installed from elsewhere with the same name, they're left alone.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_HOME="$HOME/.claude/skills"

if [[ ! -d "$SKILLS_HOME" ]]; then
    echo "No $SKILLS_HOME directory; nothing to do."
    exit 0
fi

removed=0
left_alone=0

for skill_dir in "$PROJECT_DIR"/*/; do
    skill_dir="${skill_dir%/}"
    name=$(basename "$skill_dir")
    if [[ ! -f "$skill_dir/SKILL.md" ]]; then
        continue
    fi

    target="$SKILLS_HOME/$name"
    if [[ -L "$target" ]]; then
        existing="$(readlink "$target")"
        if [[ "$existing" == "$skill_dir" ]]; then
            rm "$target"
            echo "[$name] uninstalled (removed symlink)"
            removed=$((removed + 1))
        else
            echo "[$name] symlink at $target points elsewhere ($existing); leaving it alone"
            left_alone=$((left_alone + 1))
        fi
    fi
done

echo
echo "Summary: $removed removed, $left_alone left alone (point elsewhere)"
