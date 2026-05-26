#!/usr/bin/env python3
"""
lint.py — deterministic anti-pattern checks for a PlantUML source file.

Reads .puml from a path argument (or stdin if path is "-"), prints one line per
violation: <file>:<line>: <code>: <message>. Exit code 0 if clean, 1 otherwise.

Implements the assertion vocabulary from ../evals/evals.json and cross-references
the rules in ../references/90-anti-patterns.md. The model's VERIFY phase calls
this script as the mechanical first pass; the prose checklist in 90-anti-patterns.md
catches what static checks can't (intent, abstraction-level mistakes, layout choice).

Python 3 stdlib only — no external dependencies.

Note on templates: running this against templates/*.puml will fire W003 (placeholder
diagram name) on every template. That's by design — the warning targets the
generated `.puml` after the model copies a skeleton, not the skeleton itself.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Violation:
    line: int
    code: str
    message: str


# Diagram-type detection. Keywords that are *shared* across diagram families
# (`actor` ↔ sequence/usecase, `database`/`queue` ↔ sequence/component/deployment,
# `entity` ↔ sequence/ER) need disambiguation, which detect_types handles below.
_SEQUENCE_EXCLUSIVE = re.compile(r"^\s*(participant|boundary|control|collections)\s+", re.IGNORECASE)
_ACTOR_KW = re.compile(r"^\s*actor\s+", re.IGNORECASE)
_USECASE_SIGNAL = re.compile(r"^\s*usecase\s+|^\s*rectangle\s+\".*\"\s*\{", re.IGNORECASE)
_STATE_SIGNAL = re.compile(r"^\s*\[\*\]\s*-->|^\s*state\s+\w", re.IGNORECASE)
_ER_SIGNAL = re.compile(r"^\s*entity\s+[\"\w][^{]*\{", re.IGNORECASE)
_ACTIVITY_BETA = re.compile(r"^\s*:[^;]+;|^\s*(start|stop|end)\s*$|^\s*if\s*\(", re.IGNORECASE)
_CLASS_DECL = re.compile(r"^\s*(class|abstract class|interface|enum)\s+\w", re.IGNORECASE)
_C4_INCLUDE = re.compile(r"^\s*!include\s*<C4/", re.IGNORECASE)
_DEPLOYMENT_NESTED = re.compile(r"^\s*(node|cloud)\s+\".+\"\s*\{", re.IGNORECASE)
_COMPONENT_KW = re.compile(r"^\s*component\s+", re.IGNORECASE)
_COMPONENT_BRACKET = re.compile(r"^\s*\[[\w\s\-\"]+\]\s*(--|\.\.)?")


def detect_types(lines: list[str]) -> set[str]:
    """Detect which diagram type(s) the source uses. Disambiguation rules:
      - actor + usecase signal → usecase, not sequence
      - entity with body → ER, not sequence
      - shared keywords (database, queue) alone do NOT imply sequence
    """
    found: set[str] = set()
    has_usecase_signal = any(_USECASE_SIGNAL.search(line) for line in lines)
    has_er_signal = any(_ER_SIGNAL.search(line) for line in lines)
    has_c4 = any(_C4_INCLUDE.search(line) for line in lines)

    if has_c4:
        found.add("c4")
    if has_er_signal:
        found.add("er")
    if has_usecase_signal:
        found.add("usecase")
    for line in lines:
        if _STATE_SIGNAL.search(line):
            found.add("state")
        if _ACTIVITY_BETA.search(line):
            found.add("activity")
        if _CLASS_DECL.search(line) and not has_er_signal:
            # `entity X { ... }` matches _ER_SIGNAL but not _CLASS_DECL; the
            # not-has-er-signal guard is belt-and-braces.
            found.add("class")
        if _DEPLOYMENT_NESTED.search(line):
            found.add("deployment")
        if _COMPONENT_KW.search(line) or _COMPONENT_BRACKET.search(line):
            if not has_c4:  # C4 templates use [bracket] for nothing — guard anyway
                found.add("component")

    # Sequence: exclusive keywords always count; `actor` only when not a usecase.
    for line in lines:
        if _SEQUENCE_EXCLUSIVE.search(line):
            found.add("sequence")
        elif _ACTOR_KW.search(line) and not has_usecase_signal:
            found.add("sequence")

    # Pipeline: queue + chain of relations, FLAT structure (no nested cloud/node
    # blocks — those signal deployment), NO `component` keyword (signals
    # component), NOT usecase, NOT C4. LR direction is preferred but not
    # required for detection — check_pipeline will warn (W090) if missing.
    has_queue_decl = any(re.match(r"\s*queue\s+\"", line, re.IGNORECASE) for line in lines)
    relation_count = sum(1 for line in lines if re.search(r"-->|->|\.\.>", line))
    has_nested_node_cloud = any(_DEPLOYMENT_NESTED.search(line) for line in lines)
    has_component_kw = any(_COMPONENT_KW.search(line) for line in lines)
    if (
        has_queue_decl
        and relation_count >= 3
        and not has_usecase_signal
        and not has_c4
        and not has_nested_node_cloud
        and not has_component_kw
    ):
        found.add("pipeline")

    # Fallback: if no diagram type matched and there are message-style lines
    # (`X -> Y: msg` with colon), classify as sequence with implicit participants.
    # This catches the common anti-pattern of using `Alice -> Bob: hi` with no
    # participant declarations.
    if not found:
        msg_re = re.compile(r"^\s*\w+\s+[<-]+>?[xo]?\s+\w+\s*:")
        if any(msg_re.match(line) for line in lines):
            found.add("sequence")

    return found


def check_universal(lines: list[str]) -> list[Violation]:
    """Checks that apply to every diagram type."""
    out: list[Violation] = []

    # @startuml with a non-default name (literal "sequence-diagram", "component-diagram"
    # etc. are placeholders the skill says to rename).
    start_idx = None
    start_name = None
    end_idx = None
    placeholder_names = {
        "sequence-diagram", "component-diagram", "class-diagram",
        "state-diagram", "activity-diagram", "deployment-diagram",
        "er-diagram", "usecase-diagram",
        "c4-context", "c4-container", "c4-component", "c4-dynamic",
        "pipeline-diagram",
    }
    for i, line in enumerate(lines, start=1):
        m = re.match(r"\s*@startuml\b(.*)$", line)
        if m:
            start_idx = i
            start_name = m.group(1).strip()
        if re.match(r"\s*@enduml\b", line):
            end_idx = i

    if start_idx is None:
        out.append(Violation(1, "E001", "missing @startuml"))
    elif not start_name:
        out.append(Violation(start_idx, "E002", "@startuml has no diagram name — name it like @startuml login-sequence"))
    elif start_name in placeholder_names:
        out.append(Violation(start_idx, "W003", f"@startuml uses placeholder name '{start_name}' — rename to match the scope"))

    if end_idx is None:
        out.append(Violation(len(lines), "E004", "missing @enduml"))

    # !theme must appear before any !include (universal pitfall).
    first_include = None
    theme_idx = None
    for i, line in enumerate(lines, start=1):
        if re.match(r"\s*!theme\b", line):
            theme_idx = i
        if re.match(r"\s*!include\b", line):
            if first_include is None:
                first_include = i
    if theme_idx is not None and first_include is not None and theme_idx > first_include:
        out.append(Violation(theme_idx, "E010", "!theme must appear BEFORE !include — current order may be overridden or fight the included stdlib"))

    # !theme plain on a C4 diagram (fights C4 stdlib styling).
    has_c4_include = any(re.match(r"\s*!include\s*<C4/", line) for line in lines)
    has_theme_plain = any(re.match(r"\s*!theme\s+plain\b", line) for line in lines)
    if has_c4_include and has_theme_plain:
        out.append(Violation(theme_idx or 1, "E011", "!theme plain on a C4 diagram — drop the !theme line; C4-PlantUML stdlib applies its own styling"))

    return out


def check_sequence(lines: list[str]) -> list[Violation]:
    out: list[Violation] = []
    # Count message arrows (any of ->, -->, ->>, ->x, <-, <--). Exclude lines
    # that look like state transitions ([*] --> Foo) and C4 Rel(...).
    arrow_re = re.compile(r"^\s*\w[^:]*\s+[<-]+>?[xo]?\s+\w")
    msg_lines = [i for i, line in enumerate(lines, start=1) if arrow_re.match(line) and "[*]" not in line and "Rel(" not in line]
    if len(msg_lines) > 25:
        out.append(Violation(msg_lines[0], "W020", f"sequence has {len(msg_lines)} message lines — likely a god-diagram (>25). Consider decomposing per scenario"))

    has_autonumber = any(re.match(r"\s*autonumber\b", line) for line in lines)
    if has_autonumber and 0 < len(msg_lines) < 6:
        out.append(Violation(msg_lines[0], "W021", f"autonumber is enabled with only {len(msg_lines)} messages — numbering adds noise below ~6 messages"))

    # Implicit participants: lines like `Alice -> Bob: ...` with no prior
    # `participant Alice` / `actor Alice` declaration.
    declared = set()
    decl_re = re.compile(r"^\s*(participant|actor|boundary|control|entity|database|collections|queue)\s+\"?([\w\s\-]+?)\"?(\s+as\s+(\w+))?(\s+#\w+)?\s*$", re.IGNORECASE)
    alias_for = {}
    for line in lines:
        m = decl_re.match(line.strip())
        if m:
            name = m.group(2).strip()
            alias = m.group(4)
            declared.add(name)
            if alias:
                declared.add(alias)
                alias_for[alias] = name

    msg_actor_re = re.compile(r"^\s*([\w]+)\s+[<-]+>?[xo]?\s+([\w]+)")
    for i, line in enumerate(lines, start=1):
        if "Rel(" in line or "[*]" in line:
            continue
        m = msg_actor_re.match(line)
        if m:
            for actor in (m.group(1), m.group(2)):
                if actor and actor not in declared and actor not in {"note", "alt", "else", "end", "loop", "opt", "par", "also", "break", "critical", "group", "ref", "autonumber", "return", "newpage", "title", "header", "footer", "activate", "deactivate", "destroy", "create"}:
                    # Only flag if it looks like an undeclared participant
                    if actor[0].isupper():
                        out.append(Violation(i, "W022", f"participant '{actor}' used without explicit declaration — add `participant {actor}` at the top"))
                        # one warning per actor across the file
                        declared.add(actor)
    return out


def check_state(lines: list[str]) -> list[Violation]:
    out: list[Violation] = []
    has_state_kw = any(re.search(r"\bstate\s+\w", line, re.IGNORECASE) for line in lines)
    has_state_transition = any("-->" in line and "[*]" not in line for line in lines)
    has_initial = any("[*]" in line for line in lines)
    if (has_state_kw or has_state_transition) and not has_initial:
        out.append(Violation(1, "E030", "state diagram has no [*] entry pseudostate — every state machine needs an entry"))

    # Transitions without labels (warn).
    transition_re = re.compile(r"^\s*\w[\w]*\s+-->\s+\w[\w]*\s*$")
    for i, line in enumerate(lines, start=1):
        if transition_re.match(line) and "[*]" not in line and ":" not in line:
            out.append(Violation(i, "W031", "state transition has no trigger label — add `: event` after the arrow"))

    return out


def check_er(lines: list[str]) -> list[Violation]:
    out: list[Violation] = []
    has_entity = any(re.match(r"\s*entity\s+", line, re.IGNORECASE) for line in lines)
    if not has_entity:
        return out

    # Relation lines should use crow's-foot tokens (||, |o, }|, }o on either end).
    # A "relation line" in ER context = two identifiers connected by --, .., or ~~.
    crowsfoot_re = re.compile(r"(\|\||\|o|\}\||\}o|o\||o\}|\|\{|o\{)")
    relation_re = re.compile(r"^\s*\w[\w]*\s+[\|\}o-]+--[\|\}o-]+\s+\w")
    # Class-diagram arrows have a space (or start-of-token) boundary before the
    # arrow operator: ` o-- `, ` *-- `, ` <|-- `. They must NOT be matched when
    # they appear inside a crow's-foot token like `}o--||` or `||--o{`.
    class_arrow_re = re.compile(r"(?<![|\}])(\s+|^)(o--|\*--|<\|--|<\|\.\.)")
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("'") or stripped.startswith("//") or "@" in stripped:
            continue
        if "--" in line and re.match(r"^\s*\w[\w]*\s+.+\s+\w", line) and "entity" not in line.lower():
            if class_arrow_re.search(line):
                out.append(Violation(i, "E040", "class-diagram arrow inside an ER diagram — use crow's-foot tokens (||--, }o--|{, etc.)"))
            elif not crowsfoot_re.search(line) and re.search(r"\w\s+--\s*\w", line):
                out.append(Violation(i, "W041", "relation line in ER diagram has no crow's-foot cardinality token"))

    return out


def check_c4(lines: list[str]) -> list[Violation]:
    out: list[Violation] = []
    if not any(re.match(r"\s*!include\s*<C4/", line) for line in lines):
        return out

    # Container() / ContainerDb() / ContainerQueue() / Component() should have
    # at least 3 args: alias, label, tech (descr is optional).
    container_re = re.compile(r"^\s*(Container|ContainerDb|ContainerQueue|Component|ComponentDb)\s*\(([^)]*)\)")
    for i, line in enumerate(lines, start=1):
        m = container_re.match(line)
        if m:
            args = [a.strip() for a in m.group(2).split(",")]
            if len(args) < 3:
                out.append(Violation(i, "W050", f"{m.group(1)}() called with {len(args)} args — provide alias, label, AND technology (3rd arg) for C4 usefulness"))

    # Rel() must have a non-empty label (3rd arg).
    rel_re = re.compile(r"^\s*(Rel|Rel_D|Rel_U|Rel_L|Rel_R|Rel_Back|BiRel)\s*\(([^)]*)\)")
    for i, line in enumerate(lines, start=1):
        m = rel_re.match(line)
        if m:
            args = [a.strip() for a in m.group(2).split(",")]
            if len(args) < 3:
                out.append(Violation(i, "E051", f"{m.group(1)}() missing label — every relationship needs a description"))
            elif len(args) >= 3:
                label = args[2].strip().strip('"').strip()
                if not label:
                    out.append(Violation(i, "E052", f"{m.group(1)}() has empty label string"))

    return out


def check_class(lines: list[str]) -> list[Violation]:
    out: list[Violation] = []
    # Find `class X { ... }` bodies; flag members without +/-/#/~ prefix.
    in_class = False
    class_start_line = None
    visibility_chars = {"+", "-", "#", "~"}
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if re.match(r"^\s*(class|abstract class|interface|enum)\s+\w[\w<>]*\s*\{", line):
            in_class = True
            class_start_line = i
            continue
        if in_class:
            if stripped == "}":
                in_class = False
                class_start_line = None
                continue
            # A "member" line has a colon (type) or parens (method). Skip blanks,
            # comments, modifiers-only ({static}, {abstract}).
            if not stripped or stripped.startswith("'") or stripped.startswith("//"):
                continue
            if stripped in {"{static}", "{abstract}"}:
                continue
            if stripped.startswith("=="):  # separator
                continue
            # Check first non-modifier char.
            content = stripped
            for mod in ("{static}", "{abstract}"):
                if content.startswith(mod):
                    content = content[len(mod):].lstrip()
            first_char = content[:1]
            if first_char and first_char not in visibility_chars:
                # Enum literals don't need visibility; if we're in `enum X { ... }`
                # skip. Re-detect.
                k = class_start_line
                if k is not None and re.match(r"^\s*enum\s+", lines[k - 1]):
                    continue
                out.append(Violation(i, "W060", f"class member '{stripped[:30]}...' is missing visibility marker (+/-/#/~)"))

    return out


def check_component(lines: list[str]) -> list[Violation]:
    out: list[Violation] = []
    # Diagram looks component-y? Has `component` keyword or `[Name]` style.
    has_component = any("component " in line.lower() or re.search(r"^\s*\[\w[\w\s\-]*\]\s*$", line) for line in lines)
    if not has_component:
        return out
    # Bracket-only / no semantic containers at leaf level.
    # Anchor to start-of-line so `skinparam database { ... }` (colored preset,
    # references/22-styling-colored.md) doesn't false-suppress this warning.
    semantic_present = any(re.search(r"^\s*(database|queue|cloud|node|stack)\s+", line, re.IGNORECASE) for line in lines)
    if not semantic_present:
        # Only warn if there are 5+ component-ish lines (small diagrams may legitimately have none).
        comp_lines = [line for line in lines if re.search(r"^\s*\[\w", line) or re.search(r"^\s*component\s+", line, re.IGNORECASE)]
        if len(comp_lines) >= 5:
            out.append(Violation(1, "W070", "component diagram uses no semantic containers (database / queue / cloud / node) — consider typing the infra elements"))

    return out


def check_deployment(lines: list[str]) -> list[Violation]:
    out: list[Violation] = []
    # Detect deployment-ness: title contains "deployment" OR top-level uses node/cloud/artifact heavily.
    text = "\n".join(lines).lower()
    is_deployment = "title deployment" in text or "deployment" in (lines[0].lower() if lines else "")
    # Better signal: nested node/cloud blocks.
    has_node = any(re.search(r"^\s*(node|cloud)\s+\".+\"\s*\{", line, re.IGNORECASE) for line in lines)
    if not (is_deployment or has_node):
        return out
    # Anchor to start-of-line so `skinparam node { ... }` (colored preset) doesn't false-suppress.
    has_semantic = any(re.search(r"^\s*(node|cloud|database|queue|artifact|stack|folder)\s+", line, re.IGNORECASE) for line in lines)
    if not has_semantic:
        out.append(Violation(1, "W080", "deployment-like diagram uses no semantic containers (node/cloud/database/queue/artifact)"))
    return out


def check_pipeline(lines: list[str]) -> list[Violation]:
    """Pipeline = horizontal data-flow shape. Required: left to right direction.
    Strong preference: semantic containers (queue / database / cloud / node).
    """
    out: list[Violation] = []
    has_lr = any(re.match(r"\s*left to right direction\s*$", line) for line in lines)
    if not has_lr:
        out.append(Violation(1, "W090", "pipeline-like diagram is missing `left to right direction` — horizontal layout is the point of pipeline; add the directive"))
    has_semantic = any(re.search(r"^\s*(queue|database|cloud|node|artifact|stack)\s+", line, re.IGNORECASE) for line in lines)
    if not has_semantic:
        out.append(Violation(1, "W091", "pipeline diagram uses no semantic containers (queue / database / cloud / node) — typed shapes carry stage-role information"))
    return out


def check_sprites_have_includes(lines: list[str]) -> list[Violation]:
    """W092: best-effort string match. If a `<$name>` sprite reference appears
    in the body, at least one `!include` line should mention "<name>" somewhere
    (`!include SPRITESURL/<name>.puml`). Warning only — sprite collections name
    files differently and we don't want false positives. Skips PlantUML comment
    lines (`'` prefix) so example syntax in comments doesn't false-fire."""
    out: list[Violation] = []
    sprite_refs: dict[str, int] = {}
    for i, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if stripped.startswith("'") or stripped.startswith("/'"):
            continue  # PlantUML line comment / block-comment start
        for m in re.finditer(r"<\$([a-zA-Z][\w\-]*)>", line):
            name = m.group(1).lower()
            sprite_refs.setdefault(name, i)
    if not sprite_refs:
        return out
    include_text = "\n".join(line.lower() for line in lines if "!include" in line.lower())
    for name, first_line in sprite_refs.items():
        if name not in include_text:
            out.append(Violation(first_line, "W092", f"sprite reference `<${name}>` has no matching `!include` for a sprite named '{name}' — check that the sprite file is included"))
    return out


def lint(source: str, name: str = "<stdin>") -> tuple[list[Violation], int]:
    """Return (violations, exit_code) for a single .puml source."""
    lines = source.splitlines()
    types = detect_types(lines)
    violations: list[Violation] = []
    violations += check_universal(lines)
    if "sequence" in types:
        violations += check_sequence(lines)
    if "state" in types:
        violations += check_state(lines)
    if "er" in types:
        violations += check_er(lines)
    if "c4" in types:
        violations += check_c4(lines)
    if "class" in types:
        violations += check_class(lines)
    if "component" in types:
        violations += check_component(lines)
    if "deployment" in types:
        violations += check_deployment(lines)
    if "pipeline" in types:
        violations += check_pipeline(lines)

    # Universal: any sprite reference must be preceded by an include for it.
    violations += check_sprites_have_includes(lines)

    # Sort by line.
    violations.sort(key=lambda v: (v.line, v.code))

    exit_code = 1 if any(v.code.startswith("E") for v in violations) else 0
    return violations, exit_code


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint.py <file.puml> | -", file=sys.stderr)
        return 2

    path_arg = argv[1]
    if path_arg == "-":
        source = sys.stdin.read()
        name = "<stdin>"
    else:
        p = Path(path_arg)
        if not p.exists():
            print(f"lint.py: {path_arg}: no such file", file=sys.stderr)
            return 2
        source = p.read_text()
        name = str(p)

    violations, exit_code = lint(source, name)
    if not violations:
        print(f"{name}: OK")
        return exit_code
    for v in violations:
        print(f"{name}:{v.line}: {v.code}: {v.message}")
    summary = f"{name}: {len(violations)} issue(s)"
    if exit_code == 0:
        summary += " (warnings only)"
    print(summary, file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
