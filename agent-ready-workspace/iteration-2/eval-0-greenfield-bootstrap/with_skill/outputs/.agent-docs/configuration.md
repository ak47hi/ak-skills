# Configuration & Tunables

| Name | Default | Where read | Effect |
|---|---|---|---|
| `Signer(salt=)` | `b"itsdangerous.Signer"` | `src/itsdangerous/signer.py:132` | Salt mixed into key derivation |
| `Signer(sep=)` | `b"."` | `src/itsdangerous/signer.py:133` | Separator between value and signature (must not be in urlsafe-base64 alphabet) |
| `Signer(key_derivation=)` | `"django-concat"` | `src/itsdangerous/signer.py:127, 161` | One of `concat`, `django-concat`, `hmac`, `none` |
| `Signer(digest_method=)` | `_lazy_sha1` | `src/itsdangerous/signer.py:120, 166-168` | Hash function for HMAC (any `hashlib`-compatible) |
| `Signer(algorithm=)` | `HMACAlgorithm(digest_method)` | `src/itsdangerous/signer.py:170-173` | Pluggable signing algorithm |
| `Serializer(salt=)` | `b"itsdangerous"` | `src/itsdangerous/serializer.py:111, 178` | Salt passed through to inner Signer |
| `Serializer(serializer=)` | `json` (stdlib) | `src/itsdangerous/serializer.py:95, 217` | Payload encoder/decoder; must provide `dumps`/`loads` |
| `Serializer(signer=)` | `Signer` | `src/itsdangerous/serializer.py:99, 223` | Signer class to instantiate |
| `Serializer(fallback_signers=)` | `[]` | `src/itsdangerous/serializer.py:102-104, 228-229` | Alternate signer specs tried during `loads` |
| `TimestampSigner` salt | inherits `Signer` default | `src/itsdangerous/timed.py:22-27` | (same as Signer) |
| `TimedSerializer.loads(max_age=)` | `None` (no expiry) | `src/itsdangerous/timed.py:185-220` | Seconds; if set, signatures older than this raise `SignatureExpired` |
| `URLSafeSerializerMixin.default_serializer` | `_CompactJSON` | `src/itsdangerous/url_safe.py:21` | Class attribute; compact JSON output |

Lint/type/test config lives in `pyproject.toml`:
- ruff lint rules: `B, E, F, I, UP, W`, ignoring `UP038` (`pyproject.toml:117-127`)
- mypy: `strict = true`, `python_version = "3.10"`, scoped to `src` (`pyproject.toml:98-103`)
- pyright: `standard` mode, scoped to `src` (`pyproject.toml:105-108`)
- pytest: `testpaths = ["tests"]`, `filterwarnings = ["error"]` (`pyproject.toml:78-82`)
