#!/usr/bin/env bash
# install.sh — symlink every skill in this repo into ~/.claude/skills/
# so Claude Code discovers them from any project on this machine.
#
# Discovery rule: any top-level subdirectory containing a SKILL.md file is
# treated as a skill. Add a new skill = drop a new subdir + re-run this.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_HOME="$HOME/.claude/skills"

mkdir -p "$SKILLS_HOME"

found=0
installed=0
skipped=0
errored=0

for skill_dir in "$PROJECT_DIR"/*/; do
    skill_dir="${skill_dir%/}"
    name=$(basename "$skill_dir")

    # Only treat dirs with a SKILL.md as skills.
    if [[ ! -f "$skill_dir/SKILL.md" ]]; then
        continue
    fi

    found=$((found + 1))
    target="$SKILLS_HOME/$name"

    if [[ -L "$target" ]]; then
        existing="$(readlink "$target")"
        if [[ "$existing" == "$skill_dir" ]]; then
            echo "[$name] already installed (symlink correct)"
            skipped=$((skipped + 1))
            continue
        fi
        echo "[$name] replacing stale symlink ($existing → $skill_dir)"
        rm "$target"
    elif [[ -e "$target" ]]; then
        echo "[$name] ERROR: $target exists and is not a symlink. Move it aside before installing."
        errored=$((errored + 1))
        continue
    fi

    ln -s "$skill_dir" "$target"
    echo "[$name] installed → $target"
    installed=$((installed + 1))
done

echo
if [[ $found -eq 0 ]]; then
    echo "No skills found (looking for top-level subdirs containing SKILL.md)"
    exit 1
fi
echo "Summary: $found skill(s) found, $installed installed, $skipped already current, $errored errored"
echo "Verify with: ls -l $SKILLS_HOME"
