# Business Logic Rules

1. Default key derivation is `"django-concat"`, computed as `digest_method(salt + b"signer" + secret_key)` (`src/itsdangerous/signer.py:127, 202-205`).
2. Default `digest_method` is SHA-1, but resolved lazily via `_lazy_sha1` so FIPS environments don't fail at import (`src/itsdangerous/signer.py:40-45, 54, 120`).
3. The separator `sep` must NOT belong to the urlsafe base64 alphabet (`A-Za-z0-9-_=`); supplying one raises `ValueError` at construction (`src/itsdangerous/signer.py:146-151`).
4. Default `sep` is the byte `.` (`src/itsdangerous/signer.py:133`); default `salt` is `b"itsdangerous.Signer"` for `Signer` (`:132, 156`) and `b"itsdangerous"` for `Serializer` (`src/itsdangerous/serializer.py:111`).
5. Signature verification is constant-time via `hmac.compare_digest` (`src/itsdangerous/signer.py:28`).
6. Secret-key rotation: `secret_key` may be a single value or an iterable; verification tries keys newest-first; new signatures always use the newest (last) key (`src/itsdangerous/signer.py:67-73, 175-180, 236-242`).
7. `TimestampSigner` timestamps are integer seconds since Unix epoch (`src/itsdangerous/timed.py:29-33`); `timestamp_to_datetime` returns timezone-aware UTC `datetime` (`:35-43`).
8. `TimestampSigner.unsign` rejects both `age > max_age` (expired) AND `age < 0` (timestamp in the future) with `SignatureExpired` (`src/itsdangerous/timed.py:141-153`).
9. `TimedSerializer.loads` re-raises `SignatureExpired` immediately and does NOT try fallback signers (`src/itsdangerous/timed.py:213-216`).
10. `URLSafeSerializerMixin` only uses zlib-compressed payload when it saves at least 2 bytes vs. raw (`src/itsdangerous/url_safe.py:60`); compressed payloads are marked with a leading `.` byte (`:66-67`).
11. URL-safe base64 strips padding `=` on encode and re-pads with `(-len % 4) * "="` on decode (`src/itsdangerous/encoding.py:25, 33`).
12. `base64_decode` re-raises any underlying `TypeError`/`ValueError` as `BadData("Invalid base64-encoded data")` (`src/itsdangerous/encoding.py:35-38`).
13. `Serializer.loads_unsafe` returns `(signature_valid, payload)` and never fails — it's explicitly flagged as "potentially very dangerous" and only safe with a non-exploitable serializer (i.e. NOT pickle) (`src/itsdangerous/serializer.py:349-365`).
14. `_CompactJSON` enforces `separators=(",",":")` and `ensure_ascii=False` defaults for compact, non-ASCII-preserving output (`src/itsdangerous/_json.py:14-18`).
15. `pytest` is configured with `filterwarnings = ["error"]` (`pyproject.toml:80-82`) — any warning during a test fails the build.
