# CLAUDE.md

This file is the entry point for a Claude agent working in this repo.

## Start here

1. Read `AGENT_DESIGN_DOC.md` — short, cited overview of the architecture,
   wire format, exception hierarchy, and common change recipes.
2. Cross-reference `knowledge-graph.json` for the module / class / import
   graph when you need to answer "what depends on X?" without grepping.

## Project at a glance

- **Library:** `itsdangerous` — cryptographic signing (not encryption) of
  values for safe passage through untrusted environments.
- **Source:** `src/itsdangerous/` (8 modules, ~1180 LoC).
- **Tests:** `tests/test_itsdangerous/` — one test module per source module.
- **Public API:** everything re-exported from `src/itsdangerous/__init__.py`.
  **If you add a public class/function, re-export it there.**
- **Python:** `>=3.10`. **No runtime dependencies.** Keep it that way.

## Commands

| Task | Command |
|---|---|
| Install dev deps | `uv sync` (or `pip install -e .[dev]`) |
| Run tests | `pytest` |
| Matrix tests | `tox` |
| Lint | `ruff check .` |
| Format | `ruff format .` |
| Build docs | `cd docs && make html` |

## Rules for changes

- **Wire format is a public contract.** Tokens signed by older versions live
  in cookies and URLs across the Flask ecosystem. Do not change the on-wire
  layout (separator, base64 alphabet, timestamp encoding, leading-`.` zlib
  flag) without an explicit `fallback_signers` migration path. See section 3
  and section 11 of `AGENT_DESIGN_DOC.md`.
- **Layer discipline.** `encoding` and `exc` are foundations; `signer` builds
  on them; `serializer` wraps `signer`; `timed` extends both; `url_safe`
  composes on top. Don't introduce a backward import.
- **Add a test for every change.** Tests are colocated 1:1 with source
  modules.
- **Run `ruff` and `pytest` before claiming done.** `.pre-commit-config.yaml`
  enforces ruff.
- **Don't add runtime dependencies.** Dev/docs deps go in `pyproject.toml`
  `[dependency-groups]`.

## File pointers (most-asked questions)

- "How does signing work?" -> `src/itsdangerous/signer.py`, `Signer.sign` /
  `Signer.unsign` / `Signer.derive_key`.
- "How does expiry work?" -> `src/itsdangerous/timed.py`,
  `TimestampSigner.sign` / `TimestampSigner.unsign`.
- "How do URL-safe tokens get compressed?" ->
  `src/itsdangerous/url_safe.py`, `URLSafeSerializerMixin.dump_payload`.
- "What exceptions can I catch?" -> `src/itsdangerous/exc.py` (root is
  `BadData`).
- "What's the public API?" -> `src/itsdangerous/__init__.py`.
- "How do I rotate keys?" -> pass a list to `secret_key=`. See
  `docs/concepts.rst` "Key Rotation" and section 4 of
  `AGENT_DESIGN_DOC.md`.

## When the design doc and the code disagree

The code wins. Update `AGENT_DESIGN_DOC.md` and `knowledge-graph.json` in the
same PR.
