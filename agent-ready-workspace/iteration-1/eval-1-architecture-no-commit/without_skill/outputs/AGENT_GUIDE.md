# Agent Guide: itsdangerous

A deeper map of the codebase for AI agents. Pairs with `CLAUDE.md` (rules) and `ARCHITECTURE.md` (diagrams).

## 1. What problem this library solves

You want to hand a piece of data to a client (cookie, URL token, password-reset link, signed download URL) and trust it when it comes back. You don't want server-side session state. itsdangerous gives you:

- **Signer** — appends an HMAC of the payload so tampering is detectable.
- **TimestampSigner** — additionally embeds a signing timestamp so signatures can expire.
- **Serializer** — wraps a Signer so you can sign arbitrary JSON-serializable objects, not just bytes.
- **TimedSerializer / URLSafeSerializer / URLSafeTimedSerializer** — orthogonal mixins that add timestamping and URL-safe (base64 + optional zlib) framing.

No external runtime dependencies. Pure stdlib (`hmac`, `hashlib`, `base64`, `json`, `zlib`, `struct`).

## 2. Module-by-module reference

### `encoding.py` (54 lines, leaf)
Pure helpers; no dependencies on other modules in the package except `exc.BadData`.
- `want_bytes(s)` — idempotent str→bytes coercion (utf-8 by default).
- `base64_encode` / `base64_decode` — urlsafe base64 with padding stripped/re-added.
- `int_to_bytes` / `bytes_to_int` — big-endian uint64 packing via a `struct.Struct(">Q")`, with leading zero bytes stripped on encode and re-padded on decode. This is how timestamps are embedded compactly.
- `_base64_alphabet` — the set of bytes a separator MUST NOT be in (else it could appear inside the signature).

### `exc.py` (106 lines, leaf)
Exception hierarchy. Order matters for `except` clauses.

```
BadData
  └── BadSignature        (.payload)
        ├── BadTimeSignature  (.date_signed)
        │     └── SignatureExpired
        ├── BadHeader     (.header, .original_error)
  └── BadPayload          (.original_error)
```

`BadPayload` is a sibling of `BadSignature`, NOT a child — catching `BadSignature` will not catch payload errors.

### `signer.py` (266 lines)
- `SigningAlgorithm` (abstract) — `get_signature`, `verify_signature` (default impl uses `hmac.compare_digest`).
- `NoneAlgorithm` — empty signature; for tests / "I just want serialization".
- `HMACAlgorithm` — wraps `hmac.new(key, msg, digestmod)`.
- `_lazy_sha1` — wraps `hashlib.sha1` lookup to support FIPS builds that disable SHA-1 at import time.
- `_make_keys_list` — normalizes a key/key-iterable into `list[bytes]` for key rotation.
- `Signer` — the core. Holds `secret_keys` (newest last), `salt`, `sep`, `key_derivation`, `algorithm`. Sign/unsign flow:
  - `sign(value)` → `value + sep + base64(HMAC(derive_key(newest), value))`
  - `unsign(signed_value)` → rsplit on `sep`, base64-decode sig, iterate keys newest→oldest, constant-time compare via `verify_signature`. Raise `BadSignature` on miss.
  - `derive_key` supports four modes: `concat`, `django-concat` (the default — `H(salt + b"signer" + key)`), `hmac`, `none`.

### `timed.py` (228 lines)
- `TimestampSigner(Signer)` — overrides `sign`/`unsign` to embed `base64(int_to_bytes(now))` between the value and the signature:
  - `sign`: `value + sep + b64(ts) + sep + sig(value + sep + b64(ts))`
  - `unsign`: peels timestamp, optionally checks `max_age` AND `age < 0` (clock skew). Returns either bytes or `(bytes, datetime)` depending on `return_timestamp`.
- `TimedSerializer(Serializer)` — same shape as `Serializer` but `default_signer = TimestampSigner` and `loads` accepts `max_age`/`return_timestamp`. `SignatureExpired` short-circuits fallback iteration (don't try the next signer if the timestamp is bad).

### `serializer.py` (404 lines, the biggest)
- `_PDataSerializer` (Protocol) — anything with `loads/dumps`. Defaults to the stdlib `json` module.
- `is_text_serializer(s)` — runtime check: does `dumps({})` return `str`?
- `Serializer[_TSerialized]` — generic over the dump return type (str or bytes). Five `__init__` overloads exist so type checkers can infer the right parameterization based on the serializer arg.
  - Pipeline (dumps): `obj → dump_payload (serializer.dumps + want_bytes) → make_signer(salt).sign → maybe decode utf-8`.
  - Pipeline (loads): `s → want_bytes → for signer in iter_unsigners(salt): signer.unsign → load_payload`.
  - `fallback_signers` is a list of `dict | type[Signer] | tuple[type[Signer], dict]`. `iter_unsigners` yields the primary signer first, then a fallback signer per (fallback, secret_key) pair. This is the migration mechanism for changing signing parameters.
  - `loads_unsafe` returns `(valid_bool, payload_or_None)` and never raises — for debugging only.

### `url_safe.py` (83 lines)
- `URLSafeSerializerMixin(Serializer[str])` — wraps payload bytes in zlib+base64. If zlib makes the payload at least 2 bytes shorter, the compressed form is used and prefixed with `b"."` as a marker.
- `URLSafeSerializer = mixin + Serializer[str]`
- `URLSafeTimedSerializer = mixin + TimedSerializer[str]`
- Default internal serializer for the mixin is `_CompactJSON` (smaller URLs).

### `_json.py` (18 lines)
- `_CompactJSON` — stdlib `json` wrapper with `separators=(",",":")` and `ensure_ascii=False`. Static methods only.

## 3. Cross-cutting flows

### Sign flow (text path, e.g., `URLSafeTimedSerializer.dumps({"id": 5}, salt="auth")`)
1. `Serializer.dumps` calls `dump_payload` → JSON-encode via `_CompactJSON` → `want_bytes` → zlib-compress, keep shorter form, prepend `b"."` if compressed → urlsafe-b64-no-padding.
2. `make_signer(salt)` constructs a `TimestampSigner` (since `default_signer = TimestampSigner` via `TimedSerializer`).
3. `TimestampSigner.sign` appends `b64(int_to_bytes(time.time()))`, then HMAC-signs `value + sep + ts`.
4. Result is bytes; `Serializer.dumps` decodes utf-8 because the mixin's serializer is text.

### Unsign flow
1. `Serializer.loads(s, salt)` coerces to bytes, then iterates `iter_unsigners(salt)` (primary signer + each fallback signer × each secret key).
2. For each signer, `TimestampSigner.unsign` rsplits sig off, validates HMAC (newest → oldest key), then rsplits timestamp off and checks `max_age` / clock skew.
3. On success, `load_payload` reverses base64 (+ optional zlib decompress) and JSON-decodes.
4. On `SignatureExpired`, propagate immediately (don't try fallbacks — the signature was structurally valid, just stale).

### Key rotation
- `secret_key` is normalized to a list. Newest signs; verification tries newest → oldest (`reversed(self.secret_keys)`).
- Rotating a key out invalidates tokens older than the retention window — that's the security model.

### Algorithm migration via `fallback_signers`
- Configure a new `Serializer` with a stronger `digest_method` but a fallback for the old one. New tokens use the new algo; old tokens still verify until they expire / are re-signed.

## 4. Test map

| Test file | Covers |
|---|---|
| `test_encoding.py` | base64 round-trip, int<->bytes edge cases |
| `test_signer.py` | Signer construction, salt, key derivation variants, key rotation, separator validation |
| `test_serializer.py` | Serializer dumps/loads round-trip, fallback signers, `loads_unsafe`, custom serializer interop |
| `test_timed.py` | TimestampSigner expiration, `freezegun` for time control, `return_timestamp` |
| `test_url_safe.py` | Compression heuristic, `.` prefix marker, url-safe character set |

When adding a feature, add to the corresponding test file and reuse existing fixtures.

## 5. Where to start for common asks

- "Where is the wire format defined?" → `signer.py:Signer.sign`, `timed.py:TimestampSigner.sign`, `url_safe.py:URLSafeSerializerMixin.dump_payload`. The format is `value [sep b64(ts)] sep b64(sig)`, with payload optionally `b"." + b64(zlib(json))`.
- "How do I add a new signing algorithm?" → subclass `SigningAlgorithm` in `signer.py`, pass via `algorithm=` to `Signer` or via `signer_kwargs={"algorithm": ...}` to `Serializer`.
- "How are old tokens migrated?" → `fallback_signers` on `Serializer` + `iter_unsigners`.
- "Why is SHA-1 still the default?" → see `docs/concepts.rst` "Digest Method Security". HMAC-SHA1 is fine; users who don't believe that can configure `digest_method=hashlib.sha512` and add a SHA-1 fallback.

## 6. Out of scope

- This library does NOT do encryption. Signed payloads are readable; the signature only prevents tampering. Don't put secrets in them.
- This library does NOT manage secret keys, key generation, or rotation scheduling. Callers do that and pass in a list.
- This library does NOT provide session middleware — Flask's `itsdangerous`-backed session is in Flask, not here.
