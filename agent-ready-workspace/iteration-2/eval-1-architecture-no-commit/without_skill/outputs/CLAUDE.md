# CLAUDE.md

Guidance for Claude / AI agents working in this repository.

## What this project is

**itsdangerous** is a small Python library by the Pallets team that cryptographically signs data so it can safely be passed through untrusted environments (URLs, cookies, hidden form fields, etc.) and verified on the way back.

- Language: Python (>= 3.10), strict typing (mypy + pyright)
- Build backend: `flit_core`
- Package manager / runner: `uv` + `tox`
- Lint/format: `ruff` (configured in `pyproject.toml`)
- Tests: `pytest` (+ `freezegun`)

## Repo layout (the parts that matter)

```
src/itsdangerous/
  __init__.py     # public API surface — re-exports everything
  encoding.py     # bytes/str helpers, urlsafe base64, int<->bytes
  exc.py          # exception hierarchy (BadData -> BadSignature -> ...)
  signer.py       # Signer + SigningAlgorithm/HMACAlgorithm/NoneAlgorithm
  timed.py        # TimestampSigner, TimedSerializer
  serializer.py   # Serializer (wraps Signer; adds dump/load semantics)
  url_safe.py     # URLSafeSerializer(Mixin) + URLSafeTimedSerializer
  _json.py        # _CompactJSON helper (whitespace-stripped JSON)
tests/test_itsdangerous/
  test_signer.py, test_serializer.py, test_timed.py,
  test_url_safe.py, test_encoding.py
docs/             # Sphinx documentation
```

See `AGENT_GUIDE.md` for a deeper map and `ARCHITECTURE.md` for diagrams.

## How to set up & run

This project uses `uv` for environment management. The dev groups are configured in `pyproject.toml`.

```bash
# install dev deps and run tests
uv sync
uv run pytest

# or via tox (matches CI)
uvx tox -e py3.12              # tests on a specific interpreter
uvx tox -e style               # pre-commit (ruff)
uvx tox -e typing              # mypy + pyright
uvx tox -e docs                # build sphinx docs
```

Tests are configured with `filterwarnings = ["error"]` — any warning fails the suite.

## Conventions you should respect

- **Strict typing.** `mypy` is `strict = true` and `pyright` is run too. Use `from __future__ import annotations`, prefer `t.cast` over `# type: ignore` where possible.
- **Public API is the `__init__.py` re-exports.** Do not break those names or their signatures without a deliberate `versionchanged` note.
- **Backwards compatibility matters.** Old tokens in the wild must still verify. The `fallback_signers` mechanism on `Serializer` is the supported way to evolve signing parameters.
- **No secrets in code.** Examples and tests use literal `"secret-key"` strings — that's fine for tests but the docstrings repeatedly remind users not to do it in real apps. Preserve those reminders.
- **HMAC compare with `hmac.compare_digest`** (already used in `SigningAlgorithm.verify_signature`). Never replace with `==`.
- **Docstrings** follow Sphinx style with `:param:` blocks and `.. versionadded::` / `.. versionchanged::` directives. Match the style of nearby code.
- **Ruff** rules in `pyproject.toml` select B/E/F/I/UP/W. Import sorting is `force-single-line=true, order-by-type=false`.

## Crypto safety rules

When editing `signer.py`, `timed.py`, or anything signing-related, agents must:

1. **Never** weaken signature comparison (must remain constant-time).
2. **Never** silently switch the default `digest_method` or `key_derivation` — both are versioned/documented defaults users rely on.
3. **Preserve** the multi-key (key rotation) verification order: newest key signs, verification iterates all keys.
4. **Preserve** the `fallback_signers` iteration in `Serializer.iter_unsigners` — it's how token formats are migrated.
5. **Timestamp handling** in `TimestampSigner.unsign` raises `SignatureExpired` for both `age > max_age` and `age < 0` (clock skew protection). Keep both checks.

## Common tasks

- **Adding a new exception**: add to `exc.py` and re-export from `__init__.py`.
- **Adding a new serializer variant**: subclass `Serializer` / `TimedSerializer`, override `dump_payload` / `load_payload` (see `url_safe.py` for the pattern), re-export.
- **Adding a new signing algorithm**: subclass `SigningAlgorithm` in `signer.py`, implement `get_signature`. `verify_signature` already uses constant-time compare.

## Things to avoid

- Don't add runtime dependencies — this library has none and that's a feature.
- Don't introduce a new top-level module without re-exporting from `__init__.py` AND adding a docs page under `docs/`.
- Don't change the wire format (separator `.`, base64-urlsafe-no-padding, optional `.`-prefix for compressed payloads). Existing tokens must still verify.
- Don't commit on the user's behalf unless explicitly asked.
