# AGENT_DESIGN_DOC.md

## 1. What This Project Does

`itsdangerous` is a small Python library that **cryptographically signs values so they can be passed through untrusted environments (URLs, cookies, hidden form fields) and verified intact on the way back**. It does not encrypt — payloads are visible — it only proves they have not been tampered with by anyone who lacks the secret key (`README.md:7-9`).

The library is layered: byte-level `Signer` → arbitrary-data `Serializer` (default JSON) → time-stamped variants (`TimestampSigner`, `TimedSerializer`) → URL-safe + zlib-compressed variants (`URLSafeSerializer`, `URLSafeTimedSerializer`). The README's hello-world example uses the topmost layer (`README.md:21-32`).

Pallets distributes it as part of the Flask ecosystem (`pyproject.toml:8`, `pyproject.toml:20-23`).

## 2. Architecture

Public surface is re-exported from a single `__init__.py` (`src/itsdangerous/__init__.py:1-17`).

```
┌──────────────────────────────────────────────────────┐
│ Public API (src/itsdangerous/__init__.py)            │
└──────────────────────────────────────────────────────┘
        │                       │                  │
        ▼                       ▼                  ▼
┌──────────────────┐   ┌──────────────────┐   ┌─────────────────────┐
│ URLSafeSerializer│   │ TimedSerializer  │   │ Serializer          │
│ URLSafeTimedSer..│   │ TimestampSigner  │   │ Signer              │
│ (url_safe.py)    │   │ (timed.py)       │   │ (serializer/signer) │
└──────────────────┘   └──────────────────┘   └─────────────────────┘
        │                       │                  │
        ▼                       ▼                  ▼
┌──────────────────────────────────────────────────────┐
│ encoding.py (base64/url, want_bytes, int<->bytes)    │
│ exc.py      (BadData hierarchy)                      │
│ _json.py    (_CompactJSON)                           │
└──────────────────────────────────────────────────────┘
```

Entry point: there is no CLI — this is a library. Users import from the package root (`src/itsdangerous/__init__.py:1-17`). Tests in `tests/test_itsdangerous/` mirror modules 1:1.

## 3. Core Data Structures

### `Signer`
- Fields: `secret_keys: list[bytes]`, `salt: bytes`, `sep: bytes`, `key_derivation: str`, `digest_method`, `algorithm: SigningAlgorithm` (`src/itsdangerous/signer.py:129-173`).
- Invariant: `sep` MUST NOT be in `_base64_alphabet` or constructor raises `ValueError` (`src/itsdangerous/signer.py:146-151`, alphabet at `src/itsdangerous/encoding.py:42`).
- `secret_keys[-1]` is the signing key; all entries are tried for verification, newest first (`src/itsdangerous/signer.py:175-180`, `src/itsdangerous/signer.py:236-242`).

### `SigningAlgorithm` hierarchy
- `SigningAlgorithm` (abstract; `get_signature` raises `NotImplementedError`) → `NoneAlgorithm` (returns `b""`) → `HMACAlgorithm` (default; `digest_method` defaults to lazy SHA-1) (`src/itsdangerous/signer.py:15-64`).
- `HMACAlgorithm.default_digest_method` uses `_lazy_sha1` so import does not fail on FIPS builds that exclude SHA-1 (`src/itsdangerous/signer.py:40-45`).

### `TimestampSigner`
- Subclass of `Signer` (`src/itsdangerous/timed.py:22`).
- `sign(value)` produces `value + sep + base64(int_to_bytes(now)) + sep + signature` (`src/itsdangerous/timed.py:45-51`).
- `unsign()` can validate `max_age` and optionally return `(value, datetime_utc_aware)` (`src/itsdangerous/timed.py:72-158`).

### `Serializer[_TSerialized]`
- Generic over `str | bytes` result type (`src/itsdangerous/serializer.py:18-29`, `src/itsdangerous/serializer.py:40`).
- Fields: `secret_keys`, `salt`, `serializer` (default `json`), `serializer_kwargs`, `signer` (default `Signer`), `signer_kwargs`, `fallback_signers` (`src/itsdangerous/serializer.py:190-234`).
- `is_text_serializer` cached at init based on `dumps({})` return type (`src/itsdangerous/serializer.py:33-37`, `src/itsdangerous/serializer.py:220`).

### `URLSafeSerializerMixin`
- `dump_payload()`: zlib-compress, prepend `b"."` marker iff `len(compressed) < len(json) - 1`, then urlsafe base64 (`src/itsdangerous/url_safe.py:55-69`).
- `load_payload()`: strip leading `b"."` and zlib-decompress if present (`src/itsdangerous/url_safe.py:23-53`).
- Default data serializer is `_CompactJSON` (`src/itsdangerous/url_safe.py:21`).

### Exceptions
- `BadData` (`src/itsdangerous/exc.py:7-19`) is the base; descendants: `BadSignature` (`:22-33`, carries `payload`), `BadTimeSignature` (`:36-57`, adds `date_signed`), `SignatureExpired` (`:60-63`), `BadHeader` (`:66-89`, adds `header`, `original_error`), `BadPayload` (`:92-106`, adds `original_error`).

## 4. Key Algorithms

### Key derivation (4 modes)
Implemented in `Signer.derive_key` (`src/itsdangerous/signer.py:182-213`):
- `"concat"`: `digest(salt + secret_key)`
- `"django-concat"` (default): `digest(salt + b"signer" + secret_key)` (`src/itsdangerous/signer.py:127`)
- `"hmac"`: `hmac(secret_key, salt, digest_method)`
- `"none"`: returns `secret_key` unchanged
- Unknown value → `TypeError("Unknown key derivation method")` (`src/itsdangerous/signer.py:213`).

### Sign / Unsign
- `sign(value) = value + sep + base64(algorithm.get_signature(derived_key, value))` (`src/itsdangerous/signer.py:222-225`, `:215-220`).
- `unsign(signed)` splits on the last `sep`, then `verify_signature` tries every key newest-first; raises `BadSignature` with `payload=value` on failure (`src/itsdangerous/signer.py:227-256`).
- `verify_signature` uses `hmac.compare_digest` to avoid timing leaks (`src/itsdangerous/signer.py:28`).

### Timestamp encoding
- Timestamp is a Unix `int` (`time.time()` truncated) packed via `struct.Struct(">Q").pack`, leading null bytes stripped, then urlsafe base64 (`src/itsdangerous/timed.py:29-33`, `src/itsdangerous/encoding.py:44-50`).
- Decode right-justifies to 8 bytes before unpacking (`src/itsdangerous/encoding.py:53-54`).

### Time validation in `TimestampSigner.unsign`
- Splits inner result on `sep` to recover `(value, ts_bytes)` (`src/itsdangerous/timed.py:108`).
- If signature was bad but timestamp parses, re-raises as `BadTimeSignature(..., date_signed=ts_dt)` so callers can show "link expired N days ago" (`src/itsdangerous/timed.py:119-130`).
- `age > max_age` → `SignatureExpired("Signature age {age} > {max_age} seconds", date_signed=...)` (`src/itsdangerous/timed.py:138-146`).
- `age < 0` (clock skew or forged future timestamp) → `SignatureExpired("Signature age {age} < 0 seconds", ...)` (`src/itsdangerous/timed.py:148-153`).
- Returns aware UTC `datetime` via `timestamp_to_datetime` (`src/itsdangerous/timed.py:35-43`).

### URL-safe compression heuristic
- Compress only when `len(zlib.compress(json)) < len(json) - 1`; the `-1` budgets for the leading `.` marker (`src/itsdangerous/url_safe.py:58-67`).

### Serializer fallback chain
- `iter_unsigners` yields the configured signer first, then for each `fallback_signers` entry constructs a `Signer` per `secret_key` (`src/itsdangerous/serializer.py:287-307`).
- `loads` walks the chain; on `BadSignature` it remembers the last exception and continues, then re-raises if all fail (`src/itsdangerous/serializer.py:328-343`).
- `TimedSerializer.loads` short-circuits on `SignatureExpired` — does not try the next signer (`src/itsdangerous/timed.py:213-216`).

## 5. Business Logic Rules

1. Public values are signed but **not encrypted**; treat payloads as world-readable (`README.md:7-13`).
2. The newest key in `secret_keys` is always the signing key; older keys remain valid for verification only (`src/itsdangerous/signer.py:175-180`, `src/itsdangerous/signer.py:236-242`).
3. `sep` MUST NOT be a base64-alphabet character (`A-Za-z0-9-_=`); the constructor raises `ValueError` to prevent ambiguous splits (`src/itsdangerous/signer.py:146-151`, alphabet at `src/itsdangerous/encoding.py:42`).
4. The default key-derivation scheme is `"django-concat"` (`src/itsdangerous/signer.py:127`); changing it without re-issuing tokens invalidates existing signatures.
5. The default digest is SHA-1 via `_lazy_sha1`, deliberately deferred so import works on FIPS builds that disable SHA-1 (`src/itsdangerous/signer.py:40-45`, `src/itsdangerous/signer.py:120`).
6. Signature verification uses `hmac.compare_digest` (constant-time) to defeat timing attacks (`src/itsdangerous/signer.py:28`).
7. `TimestampSigner` returns timezone-aware UTC `datetime` since 2.0 (was naive in 1.x) (`src/itsdangerous/timed.py:39-41`, `src/itsdangerous/timed.py:84-86`).
8. Both `age > max_age` AND `age < 0` raise `SignatureExpired`; future-dated tokens are treated as expired (`src/itsdangerous/timed.py:138-153`).
9. On expiry, `SignatureExpired.payload` holds the original payload and `date_signed` is set — callers may still display the data after warning (`src/itsdangerous/timed.py:142-153`, `src/itsdangerous/exc.py:36-57`).
10. `loads_unsafe` returns `(signature_valid: bool, payload)` and never raises `BadSignature`; explicitly meant for debugging only and is unsafe with eval-style serializers (e.g. pickle) (`src/itsdangerous/serializer.py:349-395`).
11. URL-safe payloads are zlib-compressed only when compression actually saves bytes; a leading `.` marker indicates compression (`src/itsdangerous/url_safe.py:55-69`).
12. `URLSafeSerializer` defaults to `_CompactJSON` (no whitespace, `ensure_ascii=False`) rather than stdlib `json` (`src/itsdangerous/url_safe.py:21`, `src/itsdangerous/_json.py:7-18`).
13. `Serializer.fallback_signers` lets callers migrate signing parameters (e.g., new digest algorithm) while still accepting old tokens (`src/itsdangerous/serializer.py:287-307`).
14. `TimedSerializer.loads` re-raises `SignatureExpired` immediately rather than trying fallback signers; only `BadSignature` (non-expiry) triggers fallback (`src/itsdangerous/timed.py:213-220`).
15. `BadSignature.payload` exposes the raw value even on tamper failure so callers can choose to inspect it (with appropriate warnings) (`src/itsdangerous/exc.py:22-33`).

## 6. External Dependencies

Runtime: **none beyond the Python stdlib** (`hashlib`, `hmac`, `json`, `zlib`, `base64`, `struct`, `time`, `datetime`, `collections.abc`, `typing`). The `[project]` section in `pyproject.toml` lists no `dependencies` (`pyproject.toml:1-23`).

| Dependency | Purpose | Where used |
|---|---|---|
| `hmac`, `hashlib` (stdlib) | Constant-time compare + HMAC signing | `src/itsdangerous/signer.py:4-5`, `:28`, `:62-64` |
| `zlib` (stdlib) | URL-safe payload compression | `src/itsdangerous/url_safe.py:4`, `:46`, `:58` |
| `base64`, `struct` (stdlib) | URL-safe encoding, int packing | `src/itsdangerous/encoding.py:3-5` |
| `freezegun` (test) | Frozen-clock tests for timed signer | `tests/test_itsdangerous/test_timed.py:7`, `pyproject.toml:47` |
| `pytest` (test) | Test runner | `pyproject.toml:48`, `pyproject.toml:78-82` |
| `flit_core` (build) | PEP 517 build backend | `pyproject.toml:56-58` |
| `sphinx`, `pallets-sphinx-themes` (docs) | Documentation build | `pyproject.toml:31-35` |
| `ruff`, `mypy`, `pyright` (dev) | Lint + type-check | `pyproject.toml:27`, `:50-54` |
| `tox`, `tox-uv` (dev) | Multi-env test runner | `pyproject.toml:28-29`, `:138-205` |

## 7. Configuration & Tunables

Library has no runtime env-var configuration; tunables are constructor arguments.

| Name | Default | Where defined | Effect |
|---|---|---|---|
| `Signer.default_digest_method` | `_lazy_sha1` | `src/itsdangerous/signer.py:120` | Hash used inside HMAC |
| `Signer.default_key_derivation` | `"django-concat"` | `src/itsdangerous/signer.py:127` | Key-derivation scheme |
| `Signer.__init__(salt=...)` | `b"itsdangerous.Signer"` | `src/itsdangerous/signer.py:132` | Namespacing salt |
| `Signer.__init__(sep=...)` | `b"."` | `src/itsdangerous/signer.py:133` | Field separator (must not be in base64 alphabet) |
| `Serializer.default_serializer` | `json` module | `src/itsdangerous/serializer.py:95` | Data serializer |
| `Serializer.default_signer` | `Signer` | `src/itsdangerous/serializer.py:99` | Signer class |
| `Serializer.default_fallback_signers` | `[]` | `src/itsdangerous/serializer.py:102-104` | Migration signers |
| `Serializer.__init__(salt=...)` | `b"itsdangerous"` | `src/itsdangerous/serializer.py:111` | Salt for the wrapped signer |
| `TimedSerializer.default_signer` | `TimestampSigner` | `src/itsdangerous/timed.py:175` | Time-stamping signer |
| `URLSafeSerializerMixin.default_serializer` | `_CompactJSON` | `src/itsdangerous/url_safe.py:21` | Compact JSON for URL payloads |
| `max_age` (per-call) | `None` | `src/itsdangerous/timed.py:75`, `:188` | Seconds before `SignatureExpired` |

Project-level config:

| File | Purpose | Key sections |
|---|---|---|
| `pyproject.toml` | Build, lint, test, docs | `[project]`, `[tool.ruff]`, `[tool.mypy]`, `[tool.pyright]`, `[tool.pytest.ini_options]`, `[tool.tox]` (`pyproject.toml:1-205`) |
| `.pre-commit-config.yaml` | Pre-commit hooks | n/a |
| `.readthedocs.yaml` | RTD build | n/a |
| `.github/workflows/*.yaml` | CI pipelines | tests, pre-commit, publish, lock |

## 8. Error Handling

All exceptions inherit from `BadData` (`src/itsdangerous/exc.py:7-19`).

- **Signature mismatch:** `BadSignature(message, payload=value)` raised from `Signer.unsign` (`src/itsdangerous/signer.py:256`). Missing separator raises with a different message (`src/itsdangerous/signer.py:249`).
- **Timestamp expired:** `SignatureExpired(message, payload=value, date_signed=...)` from `TimestampSigner.unsign` for both `age > max_age` and `age < 0` (`src/itsdangerous/timed.py:142-153`). `TimedSerializer.loads` re-raises `SignatureExpired` immediately without trying fallback signers (`src/itsdangerous/timed.py:213-216`).
- **Malformed timestamp:** `BadTimeSignature("Malformed timestamp", payload=value)` when base64 decode succeeds-but-parse-fails OR when datetime conversion overflows (`ValueError`, `OSError` on Windows, `OverflowError` on 32-bit) (`src/itsdangerous/timed.py:123-135`).
- **Missing timestamp:** `BadTimeSignature("timestamp missing", payload=result)` when `sep not in result` (`src/itsdangerous/timed.py:102-106`).
- **Bad payload:** `BadPayload("Could not load the payload ...", original_error=e)` chained from any serializer-side exception in `load_payload` (`src/itsdangerous/serializer.py:264-269`). URL-safe variants raise `BadPayload` for base64 failures and zlib-decompression failures (`src/itsdangerous/url_safe.py:36-51`).
- **Bad base64:** `BadData("Invalid base64-encoded data")` from `encoding.base64_decode` (`src/itsdangerous/encoding.py:37-38`).
- **Construction-time:** `ValueError` if `sep` is in the base64 alphabet (`src/itsdangerous/signer.py:146-151`); `TypeError` if `key_derivation` is unknown (`src/itsdangerous/signer.py:213`); `NotImplementedError` from `SigningAlgorithm.get_signature` (`src/itsdangerous/signer.py:22`).
- **Exception payload pattern:** `BadSignature.payload` and `BadTimeSignature.date_signed` are intentionally exposed so callers can offer a "link expired N days ago" UX without re-parsing the token (`src/itsdangerous/exc.py:22-57`).

[NEEDS_CONTEXT]: Is the choice of swallowing `Exception` (broad) at `src/itsdangerous/url_safe.py:38` and `:47` intentional vs. catching only `binascii.Error` / `zlib.error`? It currently masks bugs.

## 9. Testing Strategy

- **Runner:** pytest (`pyproject.toml:48`, configured at `pyproject.toml:78-82` with `testpaths = ["tests"]` and `filterwarnings = ["error"]` — any warning fails the suite).
- **Layout:** `tests/test_itsdangerous/test_<module>.py` mirrors `src/itsdangerous/<module>.py` 1:1 — five test files for five source modules (`tests/test_itsdangerous/`).
- **Inheritance pattern:** `TestTimestampSigner(FreezeMixin, TestSigner)` reuses parent test methods under a frozen clock (`tests/test_itsdangerous/test_timed.py:29`), same for `TestTimedSerializer(FreezeMixin, TestSerializer)` (`:96`).
- **Time-travel:** `freezegun.freeze_time` injected via autouse fixture (`tests/test_itsdangerous/test_timed.py:18-26`).
- **Parametrization:** `test_key_derivation` exercises all four derivations; `test_algorithm` exercises `None`, `NoneAlgorithm`, `HMACAlgorithm`, and a custom `_ReverseAlgorithm` (`tests/test_itsdangerous/test_signer.py:67-92`).
- **Type-check:** `mypy --strict` on `src/` and `pyright` in standard mode (`pyproject.toml:98-108`, `:166-173`).
- **Multi-env:** tox matrix `py3.10` – `py3.13` + `pypy311` + style + typing + docs (`pyproject.toml:138-205`).
- **CI:** GitHub Actions — `.github/workflows/tests.yaml`, `pre-commit.yaml`, `publish.yaml`, `lock.yaml`.
- **Coverage:** branch-coverage enabled (`pyproject.toml:84-86`). [NEEDS_CONTEXT]: `[tool.coverage.run] source = ["jinja2", "tests"]` lists `jinja2` rather than `itsdangerous` — appears to be a copy-paste bug from the Pallets template.

## 10. Open Questions

1. [NEEDS_CONTEXT]: Is the choice of swallowing `Exception` (broad) at `src/itsdangerous/url_safe.py:38` and `:47` intentional vs. catching only `binascii.Error` / `zlib.error`? It currently masks bugs.
2. [NEEDS_CONTEXT]: `[tool.coverage.run] source = ["jinja2", "tests"]` (`pyproject.toml:86`) lists `jinja2` rather than `itsdangerous` — appears to be a copy-paste bug from the Pallets template.
