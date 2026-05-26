# Error Handling

**Exception hierarchy** (`src/itsdangerous/exc.py:1-106`):

| Exception | Raised when | Carries |
|---|---|---|
| `BadData` | Root for all library errors | `message` |
| `BadSignature` | Signature doesn't match | `payload` (the unsigned value if recoverable) |
| `BadTimeSignature` | Bad signature on a timestamped value | + `date_signed` |
| `SignatureExpired` | Timestamp older than `max_age` (or negative age) | + `date_signed` |
| `BadHeader` | Signed header is malformed | + `header`, `original_error` |
| `BadPayload` | Payload load/decode failed | + `original_error` |

**Catch sites:**
- `base64_decode` wraps `TypeError`/`ValueError` into `BadData` (`src/itsdangerous/encoding.py:35-38`).
- `Serializer.load_payload` wraps any deserialization exception into `BadPayload(original_error=e)` (`src/itsdangerous/serializer.py:264-269`).
- `Serializer.loads` iterates `iter_unsigners`, captures `BadSignature` per attempt, re-raises the **last** one if all signers fail (`src/itsdangerous/serializer.py:328-343`).
- `Signer.unsign` raises `BadSignature(f"No {sep!r} found in value")` when no separator present, otherwise `BadSignature(f"Signature {sig!r} does not match", payload=value)` (`src/itsdangerous/signer.py:248-256`).
- `Signer.validate` / `TimestampSigner.validate` catch `BadSignature` → return `False` (never raise) (`src/itsdangerous/signer.py:258-266`, `src/itsdangerous/timed.py:160-167`).
- `URLSafeSerializerMixin.load_payload` wraps base64 / zlib failures into `BadPayload(original_error=e)` (`src/itsdangerous/url_safe.py:36-51`).
- `TimedSerializer.loads` propagates `SignatureExpired` immediately (no fallback) but catches `BadSignature` to try the next signer (`src/itsdangerous/timed.py:213-220`).
