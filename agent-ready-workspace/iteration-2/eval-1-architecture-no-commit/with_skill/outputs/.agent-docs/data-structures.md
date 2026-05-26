# Core Data Structures

### `Signer`
- Fields: `secret_keys: list[bytes]`, `sep: bytes`, `salt: bytes`, `key_derivation: str`, `digest_method`, `algorithm: SigningAlgorithm`
- Definition: `src/itsdangerous/signer.py:76-173`
- Invariants:
  - `sep` MUST NOT be a character in the base64 URL-safe alphabet (`ascii_letters + digits + "-_="`); construction raises `ValueError` otherwise (`src/itsdangerous/signer.py:146-151`).
  - `secret_keys` is always a list of `bytes` — `_make_keys_list` converts either a single str/bytes or an iterable (`src/itsdangerous/signer.py:67-73`).
  - The `secret_key` property always returns the **last** (newest) key in `secret_keys` for signing; verification iterates **reversed** so newest is tried first (`src/itsdangerous/signer.py:175-180`, `src/itsdangerous/signer.py:236-242`).

### `SigningAlgorithm` (abstract) + `HMACAlgorithm`, `NoneAlgorithm`
- Definition: `src/itsdangerous/signer.py:15-64`
- `HMACAlgorithm.default_digest_method` defaults to a lazy SHA-1 (resolved at runtime, not import — to support FIPS builds without SHA-1) (`src/itsdangerous/signer.py:40-45`, `src/itsdangerous/signer.py:48-54`).
- `verify_signature` uses `hmac.compare_digest` to avoid timing attacks (`src/itsdangerous/signer.py:24-28`).

### `Serializer[_TSerialized]` (generic over str|bytes)
- Fields: `secret_keys`, `salt`, `serializer` (the data serializer, default `json`), `is_text_serializer: bool`, `signer: type[Signer]`, `signer_kwargs: dict`, `fallback_signers: list`, `serializer_kwargs: dict`
- Definition: `src/itsdangerous/serializer.py:40-234`
- `default_serializer = json` (`src/itsdangerous/serializer.py:95`).
- `default_signer = Signer` (`src/itsdangerous/serializer.py:99`).
- `default_fallback_signers = []` (the SHA-512 fallback from 1.x was removed in 2.0) (`src/itsdangerous/serializer.py:101-104`).

### `TimestampSigner` (subclass of `Signer`)
- Definition: `src/itsdangerous/timed.py:22-167`.
- `sign` embeds the current epoch timestamp (base64-encoded big-endian uint64 with leading zero bytes stripped) between the value and the signature, separated by `sep` (`src/itsdangerous/timed.py:45-51`, `src/itsdangerous/encoding.py:44-50`).

### `TimedSerializer` (subclass of `Serializer`)
- `default_signer = TimestampSigner` (`src/itsdangerous/timed.py:175`).

### `URLSafeSerializerMixin`
- Definition: `src/itsdangerous/url_safe.py:15-69`. `default_serializer = _CompactJSON` (`src/itsdangerous/url_safe.py:21`).
- Compression marker: a leading `b"."` byte in the payload indicates zlib compression was applied; otherwise the payload is plain base64-encoded JSON (`src/itsdangerous/url_safe.py:32-34`, `src/itsdangerous/url_safe.py:55-69`).

### Exception hierarchy (`src/itsdangerous/exc.py:1-106`)
```
BadData
├── BadSignature              (carries optional .payload)
│   ├── BadTimeSignature      (carries optional .date_signed)
│   │   └── SignatureExpired
│   └── BadHeader             (carries .header and .original_error)
└── BadPayload                (carries .original_error)
```
