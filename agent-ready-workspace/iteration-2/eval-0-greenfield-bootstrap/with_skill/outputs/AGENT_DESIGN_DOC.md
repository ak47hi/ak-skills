# AGENT_DESIGN_DOC.md

## 1. What This Project Does

`itsdangerous` is a small Python library (single namespace package `itsdangerous`) for **safely passing data to untrusted environments and getting it back unmodified**, by attaching a cryptographic signature to the payload. Typical use: signed URLs, signed cookies, password-reset tokens, anywhere a server hands a bearer token to a client and later needs to verify the client didn't tamper with it.

The library is positioned as a building block for the Pallets ecosystem (Flask uses it for session cookies). It does **not** provide encryption — payloads are signed but not hidden — and it does **not** provide token revocation; security relies on a strong secret key, optional timestamp + `max_age` expiration, and optional key rotation (`README.md:6-13`, `pyproject.toml:1-7`, `src/itsdangerous/signer.py:76-112`).

Distributed under BSD-3-Clause (`LICENSE.txt`, `pyproject.toml:6`). Supports Python >= 3.10 (`pyproject.toml:16`). The CI matrix exercises CPython 3.10–3.13 and PyPy 3.11 across Linux/macOS/Windows (`.github/workflows/tests.yaml:9-25`).

## 2. Architecture

Layered library with no runtime dependencies on third parties (only Python stdlib: `hashlib`, `hmac`, `base64`, `json`, `zlib`, `time`, `datetime`, `struct`, `typing`).

```
                       ┌──────────────────────────────┐
                       │ src/itsdangerous/__init__.py │  ← public re-exports
                       └──────────────┬───────────────┘
                                      │
              ┌───────────────────────┼──────────────────────────────┐
              │                       │                              │
   ┌──────────▼──────────┐ ┌──────────▼──────────┐  ┌────────────────▼────────────┐
   │  serializer.py      │ │  timed.py           │  │  url_safe.py                │
   │  Serializer         │ │  TimestampSigner    │  │  URLSafeSerializer          │
   │  + _PDataSerializer │ │  TimedSerializer    │  │  URLSafeTimedSerializer     │
   │    Protocol         │ │  (extends Serializer│  │  (mixin: zlib + base64 +    │
   │                     │ │   + Signer)         │  │   _CompactJSON)             │
   └──────────┬──────────┘ └──────────┬──────────┘  └──────────────┬──────────────┘
              │                       │                            │
              └─────────────┬─────────┴────────────────────────────┘
                            │
                ┌───────────▼──────────────┐         ┌────────────────────────────┐
                │ signer.py                │         │ _json.py                   │
                │ SigningAlgorithm Protocol│         │ _CompactJSON               │
                │ NoneAlgorithm            │         │ (used by url_safe)         │
                │ HMACAlgorithm            │         └────────────────────────────┘
                │ Signer                   │
                └───────────┬──────────────┘
                            │
                ┌───────────▼──────────────┐         ┌────────────────────────────┐
                │ encoding.py              │         │ exc.py                     │
                │ want_bytes               │         │ BadData (root)             │
                │ base64_encode/decode     │         │  ├─ BadSignature           │
                │ int_to_bytes/bytes_to_int│         │  │   ├─ BadTimeSignature   │
                └──────────────────────────┘         │  │   │   └─ SignatureExpired│
                                                     │  │   └─ BadHeader          │
                                                     │  └─ BadPayload             │
                                                     └────────────────────────────┘
```

Entry point for library users: `from itsdangerous import …` — the package `__init__.py` re-exports the entire public surface (`src/itsdangerous/__init__.py:1-17`). There is no CLI, HTTP server, or daemon — this is a pure import-time library.

## 3. Core Data Structures

The library is organised around four pluggable abstractions — `Signer`, `Serializer`, the `SigningAlgorithm` protocol, and the `BadData`-rooted exception hierarchy — with `Timestamp*` and `URLSafe*` variants composed on top.

→ See `.agent-docs/data-structures.md`

## 4. Key Algorithms

Key derivation (4 schemes, default `django-concat`), HMAC sign/verify with constant-time comparison, URL-safe payload encoding with optional zlib compression marked by a leading `.` byte, and a fallback-signer retry loop that differs subtly between `Serializer.loads` and `TimedSerializer.loads`.

→ See `.agent-docs/algorithms.md`

## 5. Business Logic Rules

Top 10 rules most likely to mislead an agent if unknown — full numbered list in `.agent-docs/business-rules.md` (15 total).

1. Default key derivation is `"django-concat"`, computed as `digest_method(salt + b"signer" + secret_key)` (`src/itsdangerous/signer.py:127, 202-205`).
2. The separator `sep` must NOT belong to the urlsafe base64 alphabet (`A-Za-z0-9-_=`); supplying one raises `ValueError` at construction (`src/itsdangerous/signer.py:146-151`).
3. Signature verification is constant-time via `hmac.compare_digest` (`src/itsdangerous/signer.py:28`).
4. Secret-key rotation: `secret_key` may be a single value or an iterable; verification tries keys newest-first; new signatures always use the newest (last) key (`src/itsdangerous/signer.py:67-73, 175-180, 236-242`).
5. `TimestampSigner.unsign` rejects both `age > max_age` (expired) AND `age < 0` (timestamp in the future) with `SignatureExpired` (`src/itsdangerous/timed.py:141-153`).
6. `TimedSerializer.loads` re-raises `SignatureExpired` immediately and does NOT try fallback signers (`src/itsdangerous/timed.py:213-216`).
7. `URLSafeSerializerMixin` only uses zlib-compressed payload when it saves at least 2 bytes vs. raw (`src/itsdangerous/url_safe.py:60`); compressed payloads are marked with a leading `.` byte (`:66-67`).
8. URL-safe base64 strips padding `=` on encode and re-pads with `(-len % 4) * "="` on decode (`src/itsdangerous/encoding.py:25, 33`); decode failures are converted to `BadData` (`src/itsdangerous/encoding.py:35-38`).
9. `Serializer.loads_unsafe` returns `(signature_valid, payload)` and never fails — it's explicitly flagged as "potentially very dangerous" and only safe with a non-exploitable serializer (i.e. NOT pickle) (`src/itsdangerous/serializer.py:349-365`).
10. `pytest` is configured with `filterwarnings = ["error"]` (`pyproject.toml:80-82`) — any warning during a test fails the build.

→ Full list in `.agent-docs/business-rules.md` (5 additional rules)

## 6. External Dependencies

Zero runtime dependencies beyond the Python stdlib. Optional dev/docs/tests/typing/pre-commit/CI dependency groups declared in `pyproject.toml`.

→ See `.agent-docs/integrations.md`

## 7. Configuration & Tunables

All configuration is constructor kwargs on `Signer`, `Serializer`, `TimestampSigner`, `TimedSerializer`, and `URLSafe*` (no env vars, no config files). Tooling config (ruff, mypy, pyright, pytest, coverage, tox) lives in `pyproject.toml`.

→ See `.agent-docs/configuration.md`

## 8. Error Handling

Every library error derives from `BadData` (`src/itsdangerous/exc.py:7-19`). No logging, no metrics, no retries — errors are raised and the caller decides.

→ See `.agent-docs/error-handling.md`

## 9. Testing Strategy

`pytest` with `filterwarnings=["error"]`, test files mirror src 1:1 under `tests/test_itsdangerous/`, `freezegun` mocks the clock for timed tests, CI matrix is CPython 3.10–3.13 + PyPy 3.11 on Linux/macOS/Windows via `tox` driven by `uv`.

→ See `.agent-docs/testing.md`

## 10. Open Questions

1. [NEEDS_CONTEXT]: `pyproject.toml:86` sets `coverage.run.source = ["jinja2", "tests"]` — this looks copy-pasted from the jinja2 repo template; should it be `["itsdangerous", "tests"]`? No coverage report would actually cover the library code as configured.
2. [NEEDS_CONTEXT]: `BadHeader` exception is defined (`src/itsdangerous/exc.py:66-89`) and re-exported (`src/itsdangerous/__init__.py:5`), but no module in `src/itsdangerous/*.py` raises it. Is it for downstream subclasses (e.g. JWS) that never landed, or vestigial?
3. [NEEDS_CONTEXT]: Default key derivation is documented as defaulting to `default_key_derivation`, which is `"django-concat"` (`src/itsdangerous/signer.py:122-127`). Is `"django-concat"` retained for back-compat with old Django sessions / Flask cookies, or is it considered the best choice for new code? The docstring doesn't say.
4. [NEEDS_CONTEXT]: `Serializer.loads_unsafe` discards the actual exception details and returns `(False, None)` if `e.payload is None` (`src/itsdangerous/serializer.py:383-384`). Is that intentional, or should the caller get the exception for debugging?
5. [NEEDS_CONTEXT]: There's no rate-limiting or constant-time guard around the `iter_unsigners` loop in `Serializer.loads` (`src/itsdangerous/serializer.py:337`); if `fallback_signers` is long, this becomes an oracle for the number of valid keys. Is this an accepted trade-off?
