# Business Logic Rules

1. **`sep` byte must not be in the base64 URL-safe alphabet** (`ascii_letters + digits + "-_="`); construction of `Signer` raises `ValueError` otherwise (`src/itsdangerous/signer.py:146-151`).
2. **Default key-derivation scheme is `django-concat`** = `digest(salt || b"signer" || secret_key)` (`src/itsdangerous/signer.py:127`, `src/itsdangerous/signer.py:202-205`).
3. **Default HMAC digest is SHA-1**, resolved lazily at runtime so FIPS builds without SHA-1 can override before first use (`src/itsdangerous/signer.py:40-45`, `src/itsdangerous/signer.py:54`).
4. **Default salt is `b"itsdangerous.Signer"`** for `Signer`, and `b"itsdangerous"` for `Serializer` (`src/itsdangerous/signer.py:132`, `src/itsdangerous/serializer.py:111`).
5. **Key rotation: signing uses the newest (last) key**; verification iterates `reversed(secret_keys)` so newer keys are tried first (`src/itsdangerous/signer.py:180`, `src/itsdangerous/signer.py:236-242`).
6. **Signature verification uses `hmac.compare_digest`** (constant-time) (`src/itsdangerous/signer.py:24-28`).
7. **Timestamped `unsign` rejects negative ages** (clock-skew protection): if `now - ts < 0`, raise `SignatureExpired` (`src/itsdangerous/timed.py:148-153`).
8. **Timestamped `unsign` raises `BadTimeSignature` if the inner separator is missing**, even when the signature is otherwise valid (`src/itsdangerous/timed.py:102-106`).
9. **URL-safe payload uses zlib compression only when it saves more than 1 byte net** (`len(compressed) < len(json) - 1`) — the leading `b"."` marker accounts for the 1 byte (`src/itsdangerous/url_safe.py:60-63`).
10. **`SignatureExpired` is NOT swallowed by `TimedSerializer.iter_unsigners` fallback loop** — once a signature unsigns successfully but is expired, no further signer is tried (`src/itsdangerous/timed.py:213-216`).
11. **The 1.x SHA-512 fallback signer was removed in 2.0** — `default_fallback_signers` is now an empty list; users who relied on it must opt back in explicitly (`src/itsdangerous/serializer.py:101-104`, `src/itsdangerous/serializer.py:79-81`).
12. **`loads_unsafe` returns `(signature_valid, payload)`** rather than raising — explicitly dangerous and documented as such; never use with a pickle serializer (`src/itsdangerous/serializer.py:349-365`).
13. **`Serializer.dumps` returns `str` when the underlying serializer is text** (UTF-8-decoded), bytes otherwise — determined by `is_text_serializer(serializer)` at construction (`src/itsdangerous/serializer.py:33-37`, `src/itsdangerous/serializer.py:309-320`).
14. **`Serializer.load_payload` decodes payload as UTF-8 before passing to a text serializer**; falls back to `BadPayload` (wrapping the original exception) on any deserialization error (`src/itsdangerous/serializer.py:243-269`).
15. **`timestamp_to_datetime` returns a timezone-aware UTC `datetime`** (changed from naive in 2.0) (`src/itsdangerous/timed.py:35-43`).
