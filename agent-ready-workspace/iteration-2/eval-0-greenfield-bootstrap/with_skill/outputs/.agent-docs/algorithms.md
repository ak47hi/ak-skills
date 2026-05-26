# Key Algorithms

### Key derivation (`Signer.derive_key`)
- Switch on `self.key_derivation` (`src/itsdangerous/signer.py:182-213`):
  - `"concat"` → `digest(salt + secret_key)` (`:200-201`)
  - `"django-concat"` → `digest(salt + b"signer" + secret_key)` (`:202-205`) — **default** (`:127`)
  - `"hmac"` → `HMAC(secret_key, salt, digestmod=digest_method)` (`:206-209`)
  - `"none"` → returns `secret_key` unchanged (`:210-211`)
  - unknown → raises `TypeError("Unknown key derivation method")` (`:212-213`)

### Sign / unsign
- `Signer.sign`: returns `value + sep + base64(HMAC.digest(derive_key(), value))` (`src/itsdangerous/signer.py:222-225` with `get_signature` at `:215-220`).
- `Signer.unsign`: splits on `rsplit(sep, 1)`, then `verify_signature` iterates secret_keys **in reverse** (newest first) and constant-time-compares HMACs via `hmac.compare_digest` (`src/itsdangerous/signer.py:24-28, 227-242, 244-256`).
- If `sep` is absent: raises `BadSignature(f"No {sep!r} found in value")` (`src/itsdangerous/signer.py:248-249`).
- If signature mismatch: raises `BadSignature("Signature {sig!r} does not match", payload=value)` (`src/itsdangerous/signer.py:256`).

### Timestamp sign / verify
- `TimestampSigner.get_timestamp` returns `int(time.time())` — integer seconds (`src/itsdangerous/timed.py:29-33`).
- `TimestampSigner.sign` interleaves timestamp into the signed value (`src/itsdangerous/timed.py:45-51`).
- `TimestampSigner.unsign` first runs `Signer.unsign`, captures any `BadSignature` to defer until after timestamp parse, then validates `max_age` (`src/itsdangerous/timed.py:72-158`). Notable branches:
  - Missing sep in result → `BadTimeSignature("timestamp missing", ...)` (`:102-106`)
  - Timestamp parse failure → swallowed initially, then `BadTimeSignature("Malformed timestamp", ...)` (`:134-135`)
  - `age > max_age` → `SignatureExpired(f"Signature age {age} > {max_age} seconds", ...)` (`:141-146`)
  - `age < 0` (clock skew / future timestamp) → `SignatureExpired(f"Signature age {age} < 0 seconds", ...)` (`:148-153`)

### URL-safe payload encoding
- `URLSafeSerializerMixin.dump_payload`: serializer-produced bytes → optionally zlib-compress → urlsafe base64 (no padding); `.` prefix marks "this was compressed" (`src/itsdangerous/url_safe.py:55-69`). Threshold: compress only if `len(compressed) < (len(json) - 1)` (`:60`).
- `URLSafeSerializerMixin.load_payload`: detect `.` prefix → strip it and mark `decompress=True`; base64-decode (raises `BadPayload("Could not base64 decode ...")` on failure, `:36-42`); then zlib-decompress if marked (raises `BadPayload("Could not zlib decompress ...")` on failure, `:44-51`); delegate to `Serializer.load_payload`.

### `loads` retry loop (fallback signers)
- `Serializer.loads`: iterates `iter_unsigners(salt)` which yields the primary signer then each fallback signer (`src/itsdangerous/serializer.py:287-307, 328-343`). Returns on first successful `unsign`; remembers the last `BadSignature` and re-raises it after all signers fail (`:337-343`).
- `TimedSerializer.loads`: same loop, but **re-raises `SignatureExpired` immediately** without trying additional signers (`src/itsdangerous/timed.py:202-220`, see comment `:213-216`).

### `is_text_serializer` detection
- Calls `serializer.dumps({})` and checks `isinstance(..., str)` (`src/itsdangerous/serializer.py:33-37`). Used to decide whether to UTF-8 decode/encode at `dumps`/`load_payload` boundaries (`src/itsdangerous/serializer.py:260-263, 317-318`).
