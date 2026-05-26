# Agent Design Doc — itsdangerous

This document orients an AI coding agent to the `itsdangerous` codebase. It is
intentionally short: read this first, then jump to the cited files. Every
factual claim ends with a citation to the file (and line, where useful) that
backs it up.

## 1. What this project is

`itsdangerous` is a small, dependency-free Python library that
**cryptographically signs values so they can be passed through untrusted
environments and verified later.** It does *not* encrypt — the data is
readable, just tamper-evident. (`README.md`, `docs/index.rst`)

Typical uses (`docs/index.rst:36-47`):

- Signed user IDs in unsubscribe / activation URLs.
- Signed payloads stored in cookies (the original use case in Flask sessions).
- Signed round-trip state between server and client.

Python `>=3.10`, BSD-3-Clause, no runtime dependencies. (`pyproject.toml:17`,
`pyproject.toml:6`)

## 2. Layered architecture

The package is a clean four-layer stack. Each layer adds one capability on top
of the layer below. **An agent making any change should know which layer it is
touching.**

```
            URLSafeSerializer / URLSafeTimedSerializer    (url_safe.py)
                          |   adds: zlib + base64 URL-safe encoding
            TimedSerializer / TimestampSigner            (timed.py)
                          |   adds: signed timestamp + max_age expiry
            Serializer                                    (serializer.py)
                          |   adds: serialize arbitrary objects (default JSON)
            Signer                                        (signer.py)
                          |   sign/verify bytes via HMAC
            encoding / exc / _json                        (foundations)
```

| Layer | File | What it does |
|---|---|---|
| Foundations | `src/itsdangerous/encoding.py` | `want_bytes`, `base64_encode/decode` (URL-safe, unpadded), `int_to_bytes` / `bytes_to_int` via `struct.Struct(">Q")`. |
| Foundations | `src/itsdangerous/exc.py` | Exception hierarchy (see section 5). |
| Foundations | `src/itsdangerous/_json.py` | `_CompactJSON` — `json` wrapper with `separators=(",",":")`, `ensure_ascii=False`. |
| 1. Sign bytes | `src/itsdangerous/signer.py` | `Signer` derives a key from `secret_key + salt`, signs `bytes`, supports key rotation (`secret_keys` list). |
| 2. Sign objects | `src/itsdangerous/serializer.py` | `Serializer` wraps a `Signer` and runs the value through a configurable serializer (default `json`). |
| 3. Add expiry | `src/itsdangerous/timed.py` | `TimestampSigner` appends a base64 unix timestamp before signing; `unsign(max_age=...)` raises `SignatureExpired`. |
| 4. URL safety | `src/itsdangerous/url_safe.py` | Mixin that compresses with zlib if it shrinks the payload and base64-encodes; combined with `Serializer` and `TimedSerializer`. |

The public API surface is the entire `src/itsdangerous/__init__.py` (17
re-exports). **If you add a public class/function, re-export it there.**

## 3. The wire format (read this before touching `Signer` or `*Serializer`)

A signed token from `Signer.sign(value)` is:

```
<value> <sep> base64url(HMAC(derived_key, value))
```

- `sep` defaults to `b"."` and **must not be a character in the base64 URL-safe
  alphabet**, otherwise the parser cannot split signature from value
  (`signer.py:146-151`).
- `derived_key = digest(salt + b"signer" + secret_key)` by default
  (`key_derivation="django-concat"`, `signer.py:200-213`). Other modes: `concat`,
  `hmac`, `none`.
- Base64 is **URL-safe and unpadded** (`encoding.py:25`,
  `encoding.py:32-33`). Decode re-pads with `=` to a multiple of 4.

`TimestampSigner` extends the format to (`timed.py:45-51`):

```
<value> <sep> base64(int_to_bytes(unix_ts)) <sep> base64(HMAC(...))
```

`int_to_bytes` strips leading null bytes (`encoding.py:50`), and the inverse
left-pads to 8 bytes before unpacking a big-endian `uint64`
(`encoding.py:53-54`). **Do not change the struct format without thinking about
existing tokens in the wild.**

`URLSafeSerializerMixin` further wraps the *payload* (not the signature)
(`url_safe.py:55-69`):

- Serialize object -> bytes
- Try `zlib.compress`; if result is at least 2 bytes shorter, use it
- Base64-encode the (maybe compressed) bytes
- If compressed, prepend `b"."` as a sentinel

Decompression reverses this (`url_safe.py:23-53`). **The leading-`.` flag is
load-bearing — don't change it without a migration story.**

## 4. Key rotation

`Signer.__init__` accepts either a single key or an iterable of keys. They are
stored in `self.secret_keys`, oldest first (`signer.py:67-73`,
`signer.py:143`). Signing always uses the **last** (newest) key
(`signer.py:175-180`); verification tries keys in reverse order
(`signer.py:236-242`). The same scheme is inherited by `Serializer`
(`serializer.py:208`).

`Serializer.fallback_signers` lets you accept tokens signed with a *different*
signer configuration (e.g. old digest method). `iter_unsigners` yields the
primary signer first, then each fallback (`serializer.py:287-307`). This is the
designed migration path for changing parameters.

## 5. Exception hierarchy (`exc.py`)

```
BadData
├── BadSignature
│   ├── BadTimeSignature
│   │   └── SignatureExpired
│   └── BadHeader
└── BadPayload
```

Notes for agents writing `except` clauses:

- `BadData` is the catch-all root (`exc.py:7-19`).
- `BadSignature.payload` carries the (untrusted) decoded value
  (`exc.py:25-33`) — useful for inspection but **never trust it**.
- `BadTimeSignature.date_signed` is **timezone-aware UTC** since 2.0; older
  code that expected naive datetimes will break (`exc.py:46-57`,
  `timed.py:35-43`).
- `SignatureExpired` is raised when `age > max_age` *or* `age < 0` (clock
  skew / token from the future), `timed.py:138-153`.
- `loads_unsafe` returns `(False, payload_or_None)` instead of raising; only
  use for debugging (`serializer.py:349-365`).

## 6. Typing notes (will save the agent time)

- `Serializer` is `Generic[_TSerialized]` where `_TSerialized` is bound to
  `str | bytes`. The four overloads on `__init__` exist so the type checker
  infers `Serializer[str]` (default JSON) vs `Serializer[bytes]` (binary
  serializer) (`serializer.py:107-188`). **If you add a new overload, keep
  parameter order identical.**
- `_PDataSerializer` is a `Protocol` with `dumps`/`loads`; `is_text_serializer`
  uses it as a runtime + type guard (`serializer.py:24-37`).
- `default_digest_method` is a `staticmethod(_lazy_sha1)` to support FIPS
  builds without SHA-1 — accessing `hashlib.sha1` is deferred until first use
  (`signer.py:40-45`, `signer.py:120`). Don't change to a direct
  `hashlib.sha1` reference.

## 7. Where the tests live

One test module per source module (`tests/test_itsdangerous/`):

| Source | Test |
|---|---|
| `encoding.py` | `tests/test_itsdangerous/test_encoding.py` |
| `signer.py` | `tests/test_itsdangerous/test_signer.py` |
| `serializer.py` | `tests/test_itsdangerous/test_serializer.py` |
| `timed.py` | `tests/test_itsdangerous/test_timed.py` |
| `url_safe.py` | `tests/test_itsdangerous/test_url_safe.py` |

Total: ~480 LoC of tests for ~1180 LoC of source.

Run with `pytest`. The project standardizes on `tox` / `tox-uv` for matrix
testing (`pyproject.toml:[dependency-groups].dev`). Lint with `ruff`
(configured in `pyproject.toml`; enforced by `.pre-commit-config.yaml`).

## 8. Docs

User-facing docs live in `docs/`, Sphinx-rendered via
`.readthedocs.yaml`. The most useful files for an agent are:

- `docs/concepts.rst` — explains secret-key vs salt vs key rotation. **Read
  this before changing signing semantics.**
- `docs/signer.rst`, `docs/serializer.rst`, `docs/timed.rst`,
  `docs/url_safe.rst`, `docs/encoding.rst`, `docs/exceptions.rst` — per-module
  reference.
- `CHANGES.rst` — release notes (8 KB; check before introducing a behavior
  change).

## 9. Knowledge graph

A machine-readable view of the modules, classes, inheritance, and import edges
is in `knowledge-graph.json` at the repo root. Use it to answer "what depends
on X?" without re-grepping.

## 10. Common change recipes

| Task | Where |
|---|---|
| Add a new serialization format (e.g. msgpack) | Pass an object with `dumps`/`loads` as the `serializer=` arg to `Serializer`. No code changes needed. |
| Change default digest (e.g. SHA-256) | Subclass `Signer`, override `default_digest_method`; add an `HMACAlgorithm(sha1)` fallback in `Serializer.default_fallback_signers` to keep old tokens working. (`signer.py:114-120`, `serializer.py:101-104`) |
| Add a new exception | Add it in `exc.py` under the right parent, re-export from `__init__.py`. |
| Add a new public class | Add it in the appropriate module, re-export from `__init__.py`, add a docs `.rst`, add a test module. |
| Change the wire format | **Don't, without a fallback signer / version byte plan.** Existing tokens in cookies/URLs across the Flask ecosystem will break. |

## 11. Things that look weird but are intentional

- `default_digest_method = staticmethod(_lazy_sha1)` — defers `hashlib.sha1`
  access for FIPS (`signer.py:40-45`).
- `Serializer.default_fallback_signers = []` in 2.0 — the 1.1 SHA-512 default
  fallback was removed. Keep the empty list. (`serializer.py:101-104`,
  `serializer.py:78-86`).
- `URLSafeSerializerMixin` uses `_CompactJSON`, not stdlib `json`, so tokens
  don't carry extra whitespace (`url_safe.py:21`, `_json.py`).
- `int_to_bytes` strips leading `\x00` (`encoding.py:50`) — older tokens with
  smaller timestamps are still parseable because the inverse left-pads.
- `TimestampSigner.unsign` checks `age < 0` as well as `age > max_age` — guards
  against client clock skew and forged future timestamps
  (`timed.py:148-153`).
