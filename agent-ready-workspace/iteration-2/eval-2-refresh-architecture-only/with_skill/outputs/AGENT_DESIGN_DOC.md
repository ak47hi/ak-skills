# AGENT_DESIGN_DOC.md

## 1. What This Project Does

ItsDangerous is a small Python library for safely passing data to untrusted environments and getting it back unmodified. It cryptographically signs serialized data so the recipient (typically the same server, later) can verify the payload hasn't been tampered with. It does **not** encrypt — anyone can read the payload, but they can't change it without the secret key (`README.md:1-9`).

The library is best known as the engine behind Flask's signed session cookies. Typical uses: password-reset links, email-confirmation tokens, signed session cookies, signed query parameters. Data is JSON-serialized by default, optionally zlib-compressed when shorter, and base64-url-encoded so the result is safe to drop into a URL or cookie (`README.md:16-32`, `src/itsdangerous/url_safe.py:15-69`).

Package metadata: name `itsdangerous`, version `2.3.0.dev`, license BSD-3-Clause, requires Python ≥ 3.10 (`pyproject.toml:1-16`).

## 2. Architecture

The library is a small, single-package Python module. It composes four layers:

```
Public API (src/itsdangerous/__init__.py)
        |
        v
Serializers ── (wraps) ──> Signers ── (uses) ──> SigningAlgorithm
        |                       |                       |
        v                       v                       v
URLSafeSerializer        TimestampSigner         HMACAlgorithm
URLSafeTimedSerializer   (adds timestamp +       NoneAlgorithm
TimedSerializer           max_age check)
        |                       |
        +------> encoding.py (base64 url-safe, int<->bytes) <------+
        +------> exc.py     (BadData hierarchy)                     +
```

**Entry point / public API:** `src/itsdangerous/__init__.py:1-17` re-exports `Signer`, `Serializer`, `TimestampSigner`, `TimedSerializer`, `URLSafeSerializer`, `URLSafeTimedSerializer`, plus algorithm classes (`HMACAlgorithm`, `NoneAlgorithm`) and the exception hierarchy.

**Major subsystems:**
- **Signing:** `src/itsdangerous/signer.py` — `SigningAlgorithm` (abstract), `HMACAlgorithm` (default, HMAC-SHA1), `NoneAlgorithm`, `Signer` (`src/itsdangerous/signer.py:15-266`).
- **Serialization:** `src/itsdangerous/serializer.py` wraps a `Signer` to dump/load arbitrary objects, defaults to stdlib `json` (`src/itsdangerous/serializer.py:40-405`).
- **Time-aware variants:** `src/itsdangerous/timed.py` — `TimestampSigner`, `TimedSerializer` (`src/itsdangerous/timed.py:22-228`).
- **URL-safe variants:** `src/itsdangerous/url_safe.py` — base64+optional-zlib mixin, `URLSafeSerializer`, `URLSafeTimedSerializer` (`src/itsdangerous/url_safe.py:15-83`).
- **Support:** `src/itsdangerous/encoding.py` (base64 url-safe + int↔bytes), `src/itsdangerous/exc.py` (exception hierarchy), `src/itsdangerous/_json.py` (compact JSON wrapper).

## 3. Core Data Structures

`Signer`, `Serializer`, `TimestampSigner`/`TimedSerializer`, `URLSafeSerializerMixin`/`URLSafeSerializer`/`URLSafeTimedSerializer`, and the `BadData` exception hierarchy. Each carries field-level invariants and inheritance relationships.

→ See `.agent-docs/data-structures.md`

## 4. Key Algorithms

Key derivation (4 schemes, default `django-concat`), sign/unsign, time-stamped sign/unsign with `max_age` + negative-age check, URL-safe compression marker, base64 with padding fix-up, int↔bytes via `struct.Struct(">Q")`.

→ See `.agent-docs/algorithms.md`

## 5. Business Logic Rules

Top 10 most critical (full list in `.agent-docs/business-rules.md`):

1. **`sep` byte must not be in the base64 URL-safe alphabet** (`ascii_letters + digits + "-_="`); construction of `Signer` raises `ValueError` otherwise (`src/itsdangerous/signer.py:146-151`).
2. **Default key-derivation scheme is `django-concat`** = `digest(salt || b"signer" || secret_key)` (`src/itsdangerous/signer.py:127`, `src/itsdangerous/signer.py:202-205`).
3. **Default HMAC digest is SHA-1**, resolved lazily at runtime so FIPS builds without SHA-1 can override before first use (`src/itsdangerous/signer.py:40-45`, `src/itsdangerous/signer.py:54`).
4. **Key rotation: signing uses the newest (last) key**; verification iterates `reversed(secret_keys)` so newer keys are tried first (`src/itsdangerous/signer.py:180`, `src/itsdangerous/signer.py:236-242`).
5. **Signature verification uses `hmac.compare_digest`** (constant-time) (`src/itsdangerous/signer.py:24-28`).
6. **Timestamped `unsign` rejects negative ages** (clock-skew protection): if `now - ts < 0`, raise `SignatureExpired` (`src/itsdangerous/timed.py:148-153`).
7. **Timestamped `unsign` raises `BadTimeSignature` if the inner separator is missing**, even when the signature is otherwise valid (`src/itsdangerous/timed.py:102-106`).
8. **`SignatureExpired` is NOT swallowed by `TimedSerializer.loads` fallback loop** — once a signature unsigns successfully but is expired, no further signer is tried (`src/itsdangerous/timed.py:213-216`).
9. **The 1.x SHA-512 fallback signer was removed in 2.0** — `default_fallback_signers` is now an empty list; users who relied on it must opt back in explicitly (`src/itsdangerous/serializer.py:101-104`, `src/itsdangerous/serializer.py:79-81`).
10. **`loads_unsafe` returns `(signature_valid, payload)`** rather than raising — explicitly dangerous and documented as such; never use with a pickle serializer (`src/itsdangerous/serializer.py:349-365`).

→ Full list in `.agent-docs/business-rules.md` (7 additional rules)

## 6. External Dependencies

No third-party runtime dependencies; relies on stdlib `hmac`, `hashlib`, `base64`, `json`, `zlib`, `struct`, `string`, `time`, `datetime`.

→ See `.agent-docs/integrations.md`

## 7. Configuration & Tunables

Class-level attributes and constructor parameters (no env vars / config files at runtime). Tooling config lives in `pyproject.toml`.

→ See `.agent-docs/configuration.md`

## 8. Error Handling

`BadData` is the root; subclasses carry `payload`, `date_signed`, `header`, or `original_error`. Errors are caught/wrapped at base64 decode, payload load, signer iteration, and URL-safe decode boundaries.

→ See `.agent-docs/error-handling.md`

## 9. Testing Strategy

pytest with `filterwarnings = ["error"]`, module-per-source layout under `tests/test_itsdangerous/`, mypy + pyright strict typing (plus `--verifytypes` for public-API completeness), ruff linting, tox multi-env (py3.10–3.13, pypy311, style, typing, docs).

→ See `.agent-docs/testing.md`

## 10. Open Questions

1. [NEEDS_CONTEXT]: `pyproject.toml:86` lists `source = ["jinja2", "tests"]` for coverage — is this an intentional cross-project alias or a copy-paste bug that should be `["itsdangerous", "tests"]`?
