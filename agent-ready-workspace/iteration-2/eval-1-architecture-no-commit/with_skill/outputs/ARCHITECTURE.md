# ARCHITECTURE.md

> ⚠ Mermaid CLI (`mmdc`) not installed — diagrams below were not validated.
> Install with `npm install -g @mermaid-js/mermaid-cli` and re-run `/agent-ready --skip-understand --architecture` to validate.

## 1. Summary

ItsDangerous is a small layered Python library: a public API barrel re-exports a serialization layer that wraps a signing layer. The signing layer composes a pluggable `SigningAlgorithm` (default HMAC-SHA1). Two orthogonal extensions sit on top — a time-aware variant (timestamp + `max_age`) and a URL-safe variant (base64 + optional zlib compression). The whole package depends only on the Python standard library. The dominant style is **layered with mixin composition**.

## 2. Component flowchart

```mermaid
flowchart TB
    init["__init__.py (public API)"]
    serializer["serializer.py — Serializer"]
    url_safe["url_safe.py — URLSafeSerializer or URLSafeTimedSerializer"]
    timed["timed.py — TimestampSigner or TimedSerializer"]
    signer["signer.py — Signer + HMACAlgorithm"]
    encoding["encoding.py — base64 helpers"]
    exc["exc.py — BadData hierarchy"]
    json_mod["_json.py — _CompactJSON"]

    init --> serializer
    init --> signer
    init --> timed
    init --> url_safe
    init --> exc
    init --> encoding

    serializer --> signer
    serializer --> encoding
    serializer --> exc

    timed --> serializer
    timed --> signer
    timed --> encoding
    timed --> exc

    url_safe --> serializer
    url_safe --> timed
    url_safe --> json_mod
    url_safe --> encoding
    url_safe --> exc

    signer --> encoding
    signer --> exc
```

## 3. Sequence diagrams

### 3.1 `URLSafeTimedSerializer.dumps`

```mermaid
sequenceDiagram
    participant user as Caller
    participant ser as URLSafeTimedSerializer
    participant mixin as URLSafeSerializerMixin
    participant signer as TimestampSigner
    participant alg as HMACAlgorithm

    user->>ser: dumps(obj, salt)
    ser->>mixin: dump_payload(obj) -> _CompactJSON.dumps then zlib then base64
    mixin-->>ser: payload bytes
    ser->>signer: make_signer(salt).sign(payload)
    signer->>signer: append base64 of uint64 now
    signer->>alg: get_signature(key, value)
    alg-->>signer: HMAC-SHA1 digest
    signer-->>ser: payload + sep + timestamp + sep + sig
    ser-->>user: token string
```

### 3.2 `URLSafeTimedSerializer.loads` (happy path)

```mermaid
sequenceDiagram
    participant user as Caller
    participant ser as URLSafeTimedSerializer
    participant signer as TimestampSigner
    participant mixin as URLSafeSerializerMixin

    user->>ser: loads(token, max_age)
    ser->>signer: iter_unsigners then signer.unsign(token, max_age, return_timestamp-true)
    signer->>signer: rsplit on sep then verify HMAC then check age
    alt age greater than max_age
        signer-->>ser: raise SignatureExpired
        ser-->>user: SignatureExpired
    else valid
        signer-->>ser: (payload_bytes, datetime)
        ser->>mixin: load_payload(payload_bytes) -> base64 decode then maybe zlib then JSON loads
        mixin-->>ser: object
        ser-->>user: object
    end
```

### 3.3 `Signer.unsign` with key rotation

```mermaid
sequenceDiagram
    participant user as Caller
    participant signer as Signer
    participant alg as HMACAlgorithm

    user->>signer: unsign(signed_value)
    signer->>signer: rsplit on sep -> (value, sig)
    loop reversed secret_keys newest first
        signer->>signer: derive_key(secret_key) using django-concat
        signer->>alg: verify_signature(key, value, sig) - constant time
        alt match
            alg-->>signer: True
            signer-->>user: value
        else no match
            alg-->>signer: False
        end
    end
    signer-->>user: raise BadSignature
```

## 4. Data model

```mermaid
classDiagram
    class SigningAlgorithm {
        +get_signature(key, value) bytes
        +verify_signature(key, value, sig) bool
    }
    class HMACAlgorithm {
        +digest_method
        +get_signature(key, value) bytes
    }
    class NoneAlgorithm
    class Signer {
        +secret_keys list bytes
        +salt bytes
        +sep bytes
        +key_derivation str
        +algorithm SigningAlgorithm
        +sign(value) bytes
        +unsign(signed_value) bytes
        +derive_key(secret_key) bytes
        +verify_signature(value, sig) bool
        +validate(signed_value) bool
    }
    class TimestampSigner {
        +sign(value) bytes
        +unsign(signed_value, max_age, return_timestamp)
        +get_timestamp() int
        +timestamp_to_datetime(ts) datetime
    }
    class Serializer {
        +secret_keys list bytes
        +salt bytes
        +serializer
        +signer type Signer
        +fallback_signers list
        +dumps(obj, salt)
        +loads(s, salt)
        +loads_unsafe(s, salt)
        +make_signer(salt) Signer
        +iter_unsigners(salt)
    }
    class TimedSerializer {
        +default_signer-TimestampSigner
        +loads(s, max_age, return_timestamp, salt)
    }
    class URLSafeSerializerMixin {
        +default_serializer-_CompactJSON
        +dump_payload(obj) bytes
        +load_payload(payload) any
    }
    class URLSafeSerializer
    class URLSafeTimedSerializer

    SigningAlgorithm <|-- HMACAlgorithm
    SigningAlgorithm <|-- NoneAlgorithm
    Signer <|-- TimestampSigner
    Serializer <|-- TimedSerializer
    Serializer <|-- URLSafeSerializerMixin
    URLSafeSerializerMixin <|-- URLSafeSerializer
    URLSafeSerializerMixin <|-- URLSafeTimedSerializer
    TimedSerializer <|-- URLSafeTimedSerializer
    Signer o-- SigningAlgorithm
    Serializer ..> Signer
```

## 5. Dependency graph

```mermaid
flowchart LR
    proj["itsdangerous"]
    proj --> hmac_lib["stdlib hmac"]
    proj --> hashlib_lib["stdlib hashlib"]
    proj --> base64_lib["stdlib base64"]
    proj --> json_lib["stdlib json"]
    proj --> zlib_lib["stdlib zlib"]
    proj --> struct_lib["stdlib struct"]
    proj --> time_lib["stdlib time"]
    proj --> datetime_lib["stdlib datetime"]
```

## 6. Config table

These are class attributes and constructor parameters; there are no environment variables or runtime config files.

| Name | Default | Where defined | Effect |
|---|---|---|---|
| `Signer.default_digest_method` | lazy SHA-1 | `src/itsdangerous/signer.py:120` | Hash used inside HMAC |
| `Signer.default_key_derivation` | `"django-concat"` | `src/itsdangerous/signer.py:127` | Key-derivation scheme |
| `Signer` `salt` ctor arg | `b"itsdangerous.Signer"` | `src/itsdangerous/signer.py:132` | Context-separator combined with secret |
| `Signer` `sep` ctor arg | `b"."` | `src/itsdangerous/signer.py:133` | Byte separating value from signature |
| `Serializer.default_serializer` | `json` | `src/itsdangerous/serializer.py:95` | Data serializer for `dumps`/`loads` |
| `Serializer.default_signer` | `Signer` | `src/itsdangerous/serializer.py:99` | Signer class used by `make_signer` |
| `Serializer.default_fallback_signers` | `[]` | `src/itsdangerous/serializer.py:104` | Extra signers tried when primary fails |
| `Serializer` `salt` ctor arg | `b"itsdangerous"` | `src/itsdangerous/serializer.py:111` | Salt passed to constructed signer |
| `TimedSerializer.default_signer` | `TimestampSigner` | `src/itsdangerous/timed.py:175` | Time-aware signer |
| `URLSafeSerializerMixin.default_serializer` | `_CompactJSON` | `src/itsdangerous/url_safe.py:21` | Whitespace-stripped JSON |
| `TimestampSigner.unsign` `max_age` | `None` | `src/itsdangerous/timed.py:75` | Reject signatures older than this many seconds |

## 7. Open Questions

1. [NEEDS_CONTEXT]: `pyproject.toml:86` lists `source = ["jinja2", "tests"]` for coverage — is this an intentional cross-project alias or a copy-paste bug that should be `["itsdangerous", "tests"]`?
