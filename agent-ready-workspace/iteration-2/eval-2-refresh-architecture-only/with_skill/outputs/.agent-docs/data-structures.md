# Core Data Structures

### `Signer`
- Fields: `secret_keys: list[bytes]`, `sep: bytes`, `salt: bytes`, `key_derivation: str`, `digest_method`, `algorithm: SigningAlgorithm`
- Definition: `src/itsdangerous/signer.py:76-173`
- Invariants:
  - `sep` MUST NOT be a character in the base64 URL-safe alphabet (`ascii_letters + digits + "-_="`); construction raises `ValueError` otherwise (`src/itsdangerous/signer.py:146-151`).
  - `secret_keys` is always a list of `bytes` — `_make_keys_list` converts either a single str/bytes or an iterable (`src/itsdangerous/signer.py:67-73`).
  - The `secret_key` property always returns the **last** (newest) key in `secret_keys` for signing; verification iterates **reversed** so newest is tried first (`src/itsdangerous/signer.py:175-180`, `src/itsdangerous/signer.py:236-242`).
  - If `salt is None` is passed to the constructor, it is coerced to `b"itsdangerous.Signer"` (`src/itsdangerous/signer.py:153-156`).

### `SigningAlgorithm` (abstract) + `HMACAlgorithm`, `NoneAlgorithm`
- Definition: `src/itsdangerous/signer.py:15-64`
- `HMACAlgorithm.default_digest_method` defaults to a lazy SHA-1 (resolved at runtime, not import — to support FIPS builds without SHA-1) (`src/itsdangerous/signer.py:40-45`, `src/itsdangerous/signer.py:48-54`).
- `verify_signature` uses `hmac.compare_digest` to avoid timing attacks (`src/itsdangerous/signer.py:24-28`).
- `NoneAlgorithm.get_signature` returns `b""` — disables signing entirely (`src/itsdangerous/signer.py:31-37`).

### `Serializer[_TSerialized]` (generic over str|bytes)
- Fields: `secret_keys`, `salt`, `serializer` (the data serializer, default `json`), `is_text_serializer: bool`, `signer: type[Signer]`, `signer_kwargs: dict`, `fallback_signers: list`, `serializer_kwargs: dict`
- Definition: `src/itsdangerous/serializer.py:40-234`
- `default_serializer = json` (`src/itsdangerous/serializer.py:95`).
- `default_signer = Signer` (`src/itsdangerous/serializer.py:99`).
- `default_fallback_signers = []` (the SHA-512 fallback from 1.x was removed in 2.0) (`src/itsdangerous/serializer.py:101-104`).
- `is_text_serializer` is computed once at construction by `is_text_serializer(serializer)` — calls `serializer.dumps({})` and checks `isinstance(..., str)` (`src/itsdangerous/serializer.py:33-37`, `src/itsdangerous/serializer.py:220`).

### `TimestampSigner` (subclass of `Signer`)
- Definition: `src/itsdangerous/timed.py:22-167`.
- `sign` embeds the current epoch timestamp (base64-encoded big-endian uint64 with leading zero bytes stripped) between the value and the signature, separated by `sep` (`src/itsdangerous/timed.py:45-51`, `src/itsdangerous/encoding.py:44-50`).
- `get_timestamp()` returns `int(time.time())` — second-resolution UTC epoch (`src/itsdangerous/timed.py:29-33`).

### `TimedSerializer` (subclass of `Serializer`)
- `default_signer = TimestampSigner` (`src/itsdangerous/timed.py:175`).

### `URLSafeSerializerMixin`
- Definition: `src/itsdangerous/url_safe.py:15-69`. `default_serializer = _CompactJSON` (`src/itsdangerous/url_safe.py:21`).
- Compression marker: a leading `b"."` byte in the payload indicates zlib compression was applied; otherwise the payload is plain base64-encoded JSON (`src/itsdangerous/url_safe.py:32-34`, `src/itsdangerous/url_safe.py:55-69`).

### `URLSafeSerializer` / `URLSafeTimedSerializer`
- `URLSafeSerializer(URLSafeSerializerMixin, Serializer[str])` (`src/itsdangerous/url_safe.py:72-76`).
- `URLSafeTimedSerializer(URLSafeSerializerMixin, TimedSerializer[str])` (`src/itsdangerous/url_safe.py:79-83`).
- MRO places the mixin first, so `dump_payload`/`load_payload` (with compression) run before `Serializer.dump_payload` is invoked via `super()`.

### `_CompactJSON` (internal)
- Wraps stdlib `json` with `ensure_ascii=False` and `separators=(",", ":")` to strip whitespace (`src/itsdangerous/_json.py:7-18`).

### Exception hierarchy (`src/itsdangerous/exc.py:1-106`)
```
BadData
├── BadSignature              (carries optional .payload)
│   ├── BadTimeSignature      (carries optional .date_signed)
│   │   └── SignatureExpired
│   └── BadHeader             (carries .header and .original_error)
└── BadPayload                (carries .original_error)
```
