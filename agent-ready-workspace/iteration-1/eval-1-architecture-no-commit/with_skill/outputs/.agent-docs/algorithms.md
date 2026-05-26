# Key Algorithms

### Key derivation (`Signer.derive_key`, `src/itsdangerous/signer.py:182-213`)
Four schemes, selected by `key_derivation` (default `"django-concat"`):
- `"concat"`: `digest(salt || secret_key)` (`src/itsdangerous/signer.py:200-201`).
- `"django-concat"`: `digest(salt || b"signer" || secret_key)` — default (`src/itsdangerous/signer.py:202-205`, `src/itsdangerous/signer.py:127`).
- `"hmac"`: HMAC(secret_key, salt) (`src/itsdangerous/signer.py:206-209`).
- `"none"`: returns `secret_key` unchanged (`src/itsdangerous/signer.py:210-211`).
- Unknown value → `TypeError("Unknown key derivation method")` (`src/itsdangerous/signer.py:212-213`).

### Sign / unsign (`src/itsdangerous/signer.py:215-256`)
- `sign(value)` returns `value + sep + base64_encode(get_signature(value))` (`src/itsdangerous/signer.py:222-225`).
- `unsign(signed_value)` splits on the **last** occurrence of `sep` using `rsplit(sep, 1)`, then verifies (`src/itsdangerous/signer.py:244-256`).
- `verify_signature` iterates `secret_keys` in **reverse** (newest first) so rotated-out keys are tried last (`src/itsdangerous/signer.py:236-242`).

### Time-stamped sign / unsign (`src/itsdangerous/timed.py:45-158`)
- `sign(value)`: `value + sep + base64(uint64(now)) + sep + base64(signature)` (`src/itsdangerous/timed.py:45-51`).
- `unsign(signed_value, max_age=None, return_timestamp=False)`:
  1. Super-class `unsign` verifies the signature first. If it fails, the failure is captured but not raised yet (`src/itsdangerous/timed.py:88-93`).
  2. The result must still contain `sep` separating value from timestamp; missing → `BadTimeSignature("timestamp missing")` (`src/itsdangerous/timed.py:102-106`).
  3. Timestamp parsed via `bytes_to_int(base64_decode(ts_bytes))` (`src/itsdangerous/timed.py:108-115`).
  4. If signature was bad, re-raise with structured payload + date_signed (`src/itsdangerous/timed.py:118-130`).
  5. If `max_age` provided: `age = now - ts`; `age > max_age` → `SignatureExpired`; `age < 0` (clock went backwards) → `SignatureExpired` (`src/itsdangerous/timed.py:138-153`).

### URL-safe compression (`URLSafeSerializerMixin.dump_payload`, `src/itsdangerous/url_safe.py:55-69`)
- Compress payload with zlib.
- If `len(compressed) < len(json) - 1` (saves at least 2 bytes net after the marker), use the compressed form and prefix with `b"."` (`src/itsdangerous/url_safe.py:60-67`).
- Otherwise use uncompressed payload.
- `load_payload` checks for the leading `b"."` to decide whether to decompress (`src/itsdangerous/url_safe.py:30-51`).

### Base64 URL-safe encoding (`src/itsdangerous/encoding.py:20-38`)
- `base64_encode`: standard `base64.urlsafe_b64encode` with trailing `=` padding stripped (`src/itsdangerous/encoding.py:20-25`).
- `base64_decode`: re-adds `=` padding (`len % 4`) before decoding; `TypeError`/`ValueError` → `BadData("Invalid base64-encoded data")` (`src/itsdangerous/encoding.py:28-38`).

### Int↔bytes (`src/itsdangerous/encoding.py:44-54`)
- Uses `struct.Struct(">Q")` (big-endian uint64); `int_to_bytes` strips leading null bytes; `bytes_to_int` right-pads with nulls to 8 bytes before unpacking (`src/itsdangerous/encoding.py:44-54`).
