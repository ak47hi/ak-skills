# External Dependencies

| Dependency | Purpose | Where used |
|---|---|---|
| Python standard library `hmac` | HMAC computation + constant-time compare | `src/itsdangerous/signer.py:5`, `src/itsdangerous/signer.py:28`, `src/itsdangerous/signer.py:62-64`, `src/itsdangerous/signer.py:206-209` |
| Python standard library `hashlib` | Hash functions (default SHA-1, lazy) | `src/itsdangerous/signer.py:4`, `src/itsdangerous/signer.py:40-45` |
| Python standard library `base64` | URL-safe base64 encode/decode | `src/itsdangerous/encoding.py:3`, `src/itsdangerous/encoding.py:25`, `src/itsdangerous/encoding.py:36` |
| Python standard library `json` | Default data serializer | `src/itsdangerous/serializer.py:4`, `src/itsdangerous/serializer.py:95`; compact wrapper at `src/itsdangerous/_json.py:1-19` |
| Python standard library `zlib` | Payload compression for URL-safe variant | `src/itsdangerous/url_safe.py:4`, `src/itsdangerous/url_safe.py:46`, `src/itsdangerous/url_safe.py:58` |
| Python standard library `struct` | Big-endian uint64 packing for timestamps | `src/itsdangerous/encoding.py:5`, `src/itsdangerous/encoding.py:44-46` |
| Python standard library `time`, `datetime` | Timestamp generation + tz-aware conversion | `src/itsdangerous/timed.py:4`, `src/itsdangerous/timed.py:6-7`, `src/itsdangerous/timed.py:29-43` |
| Python standard library `string` | Source of the base64 URL-safe alphabet constant | `src/itsdangerous/encoding.py:4`, `src/itsdangerous/encoding.py:42` |

**No third-party runtime dependencies** — `pyproject.toml:1-16` declares no runtime requirements; all `[dependency-groups]` are dev/test/docs only (`pyproject.toml:25-54`).
