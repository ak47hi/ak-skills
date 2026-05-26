# Error Handling

All library errors derive from `BadData` (`src/itsdangerous/exc.py:7-19`). Callers can catch one base type to handle every signature/payload failure.

- **Bad separator** (config error at construction): `ValueError` (`src/itsdangerous/signer.py:147-151`)
- **Bad base64 input**: `BadData("Invalid base64-encoded data")` raised from `encoding.base64_decode` (`src/itsdangerous/encoding.py:35-38`).
- **Missing sep in signed value**: `BadSignature(f"No {sep!r} found in value")` (`src/itsdangerous/signer.py:248-249`).
- **Signature mismatch**: `BadSignature("Signature ... does not match", payload=value)` — `payload` is set so callers can inspect the value even though it's untrusted (`src/itsdangerous/signer.py:256`).
- **Missing/malformed timestamp**: `BadTimeSignature("timestamp missing" | "Malformed timestamp", payload=value)` (`src/itsdangerous/timed.py:106, 126-128, 135`).
- **Expired or future-dated timestamp**: `SignatureExpired(..., payload=value, date_signed=...)` (`src/itsdangerous/timed.py:142-153`).
- **Bad header** (serializer subclasses with header support): `BadHeader(message, payload, header, original_error)` (`src/itsdangerous/exc.py:66-89`). Not raised by any code in `src/itsdangerous/*.py` currently — intended for downstream subclasses.
- **Bad payload** (deserialization failure even after signature check): `BadPayload(message, original_error=...)` from `Serializer.load_payload` (`src/itsdangerous/serializer.py:264-269`) and from URL-safe base64/zlib paths (`src/itsdangerous/url_safe.py:38-42, 48-51`).
- **Fallback-signer loop**: `Serializer.loads` and `TimedSerializer.loads` both walk every configured signer; only the **last** `BadSignature` is re-raised (`src/itsdangerous/serializer.py:337-343`, `src/itsdangerous/timed.py:213-220`). `TimedSerializer` short-circuits on `SignatureExpired` (it ran a valid signature, just past `max_age`).

Notably absent: no logging, no metric emission, no retry, no network calls. Errors are raised; the caller decides what to do.
