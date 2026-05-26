#!/usr/bin/env python3
"""
Programmatic grading for the connection-leak skill evals.

For each eval directory, reads eval_metadata.json (the assertions) and
both response.md outputs (with_skill / without_skill), runs each assertion
against the response, and writes grading.json into each condition's directory.

Two assertion types:
- "keyword": passes if ANY of the assertion's keywords appears (case-insensitive)
- "semantic": cannot be auto-graded purely from keywords; we use a curated
  per-assertion check function defined inline below. If you want pure-keyword
  grading for "semantic" assertions too, the SEMANTIC_CHECKS dict below maps
  assertion-id -> list of phrase groups, where the assertion passes only if
  EVERY group has at least one phrase present.
"""

import json
import re
from pathlib import Path

ITERATION_DIR = Path(__file__).resolve().parent

# For "semantic" assertions, we encode required-phrase groups.
# An assertion passes iff EVERY group has at least one phrase present (case-insensitive substring).
# Multiple groups = AND. Multiple phrases in a group = OR.
SEMANTIC_CHECKS = {
    # ----- eval 0: hikari -----
    "diagnoses-scope-too-wide": [
        ["scope", "hold", "held", "across", "outside the transaction", "between"],
        ["stripe", "http", "external", "outbound", "network"],
    ],
    "shows-two-tx-fix": [
        ["two transaction", "two short", "split", "separate bean", "before", "after"],
        ["@transactional", "transactional"],
    ],
    "warns-against-pool-size-bump": [
        ["pool size", "maximumpoolsize", "raise the", "bump", "increase"],
        ["mask", "won't fix", "anti-pattern", "not a fix", "doesn't fix", "won't help", "wrong fix"],
    ],
    # ----- eval 1: flink -----
    "diagnoses-lifecycle-not-steady-state":[
        ["lifecycle", "restart", "cancel", "close()"],
        ["per-restart", "step", "each restart", "across restart", "on cancel"],
    ],
    "shows-richasyncfunction-template": [
        ["close()", "@override"],
        ["shutdown", "awaittermination"],
    ],
    "verification-restart-5x": [
        ["5", "five", "multiple", "several"],
        ["restart"],
        ["baseline", "flat", "not step", "doesn't step", "should return", "between restarts"],
    ],
    # ----- eval 2: aiohttp -----
    "starts-with-triage": [
        ["triage", "before", "first", "confirm", "step 1", "1.", "/proc/1/fd", "fd count"],
        ["classify", "fd type", "remote", "endpoint", "lsof", "/proc/1/fd", "ss "],
    ],
    "diagnoses-per-client-leak": [
        ["per-client", "per client", "per-request construction", "session per request", "session-per-request", "per request"],
        ["construct", "create", "instantiat", "new clientsession"],
    ],
    "instrumentation-snippet": [
        ["__init__", "monkey", "patch", "traceback", "logging", "log", "instrument"],
        ["clientsession", "ClientSession", "session"],
    ],
    "anti-pattern-bare-requests": [
        ["per-request", "per request", "session per request", "session-per-request", "constructing", "creating a", "new session"],
        ["singleton", "hoist", "one per", "lifespan", "long-lived", "shared"],
    ],
}


def passes_keyword(response: str, keywords: list[str]) -> bool:
    rl = response.lower()
    return any(k.lower() in rl for k in keywords)


def passes_semantic(response: str, assertion_id: str) -> bool:
    groups = SEMANTIC_CHECKS.get(assertion_id)
    if not groups:
        return False
    rl = response.lower()
    return all(any(phrase.lower() in rl for phrase in group) for group in groups)


def grade_response(response: str, assertions: list[dict]) -> list[dict]:
    results = []
    for a in assertions:
        check_type = a.get("check_type", "semantic")
        if check_type == "keyword":
            passed = passes_keyword(response, a["keywords"])
            evidence = next((k for k in a["keywords"] if k.lower() in response.lower()), "")
            evidence = f"Found keyword: '{evidence}'" if passed else f"None of keywords {a['keywords']} found"
        else:
            passed = passes_semantic(response, a["id"])
            evidence = "All semantic phrase groups matched" if passed else f"Semantic check '{a['id']}' missed at least one required phrase group"
        results.append({
            "text": a["text"],
            "passed": passed,
            "evidence": evidence,
        })
    return results


def main():
    for eval_dir in sorted(ITERATION_DIR.iterdir()):
        if not eval_dir.is_dir():
            continue
        meta_path = eval_dir / "eval_metadata.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        assertions = meta["assertions"]

        for condition in ("with_skill", "without_skill"):
            response_path = eval_dir / condition / "run-1" / "outputs" / "response.md"
            if not response_path.exists():
                print(f"SKIP: {response_path} not found")
                continue
            response = response_path.read_text()
            graded = grade_response(response, assertions)
            passed = sum(1 for g in graded if g["passed"])
            total = len(graded)
            grading = {
                "eval_id": meta["eval_id"],
                "eval_name": meta["eval_name"],
                "condition": condition,
                "summary": {
                    "passed": passed,
                    "failed": total - passed,
                    "total": total,
                    "pass_rate": round(passed / total, 4) if total else 0.0,
                },
                "expectations": graded,
            }
            out_path = eval_dir / condition / "run-1" / "grading.json"
            out_path.write_text(json.dumps(grading, indent=2))
            print(f"{eval_dir.name}/{condition}: {passed}/{total} ({grading['summary']['pass_rate']*100:.0f}%)")


if __name__ == "__main__":
    main()
