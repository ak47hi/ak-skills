# Core Data Structures

### `Signer`
- Fields: `secret_keys: list[bytes]`, `salt: bytes`, `sep: bytes`, `key_derivation: str`, `digest_method`, `algorithm: SigningAlgorithm`
- Definition: `src/itsdangerous/signer.py:76-173`
- Invariants:
  - `sep` MUST NOT be in the urlsafe-base64 alphabet (ASCII letters/digits/`-_=`) — enforced in `__init__` (`src/itsdangerous/signer.py:146-151`).
  - `secret_keys` is always a list ≥ 1; coerced via `_make_keys_list` (`src/itsdangerous/signer.py:67-73, 143`).
  - The last entry of `secret_keys` is the active signing key; older entries are accepted for verification (`src/itsdangerous/signer.py:175-180, 236-242`).

### `SigningAlgorithm` (Protocol) and `HMACAlgorithm`
- Definition: `src/itsdangerous/signer.py:15-28` (base), `:48-64` (HMAC).
- `HMACAlgorithm.default_digest_method` is `_lazy_sha1` — SHA-1 is resolved lazily so FIPS-only builds without SHA-1 don't fail at import time (`src/itsdangerous/signer.py:40-45, 54`).

### `Serializer` (generic in `_TSerialized`, bound `str | bytes`)
- Fields: `secret_keys`, `salt`, `serializer` (module-like with `dumps`/`loads`), `is_text_serializer: bool`, `signer: type[Signer]`, `signer_kwargs: dict`, `fallback_signers: list`, `serializer_kwargs: dict`
- Definition: `src/itsdangerous/serializer.py:40-234`
- Default `serializer = json` stdlib module (`src/itsdangerous/serializer.py:95`); default `signer = Signer` (`:99`); default `fallback_signers = []` (`:102-104`).

### `TimestampSigner`
- Extends `Signer`; signed payload format is `value + sep + base64(timestamp) + sep + signature` (`src/itsdangerous/timed.py:45-51`).

### `TimedSerializer`
- Extends `Serializer`; `default_signer = TimestampSigner` (`src/itsdangerous/timed.py:175`); `loads(..., max_age=)` enforces expiration (`src/itsdangerous/timed.py:185-220`).

### `URLSafeSerializerMixin`
- Mixin used to build `URLSafeSerializer` and `URLSafeTimedSerializer`. `default_serializer = _CompactJSON` (`src/itsdangerous/url_safe.py:21`). On dump, attempts zlib-compress; if compressed is more than 1 byte shorter than raw, uses compressed and prepends `.` marker (`src/itsdangerous/url_safe.py:55-69`).

### Exception hierarchy
- Root: `BadData(Exception)` (`src/itsdangerous/exc.py:7-19`)
- `BadSignature(BadData)` with `payload` attribute (`src/itsdangerous/exc.py:22-33`)
- `BadTimeSignature(BadSignature)` with `date_signed` (`src/itsdangerous/exc.py:36-57`)
- `SignatureExpired(BadTimeSignature)` (`src/itsdangerous/exc.py:60-63`)
- `BadHeader(BadSignature)` with `header`, `original_error` (`src/itsdangerous/exc.py:66-89`)
- `BadPayload(BadData)` with `original_error` (`src/itsdangerous/exc.py:92-106`)
