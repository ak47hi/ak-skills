# Architecture: itsdangerous

Diagrams describing the structure and runtime behavior of itsdangerous. All diagrams are Mermaid and render in GitHub, VS Code, and most Markdown viewers.

---

## 1. Module dependency graph

How the package's modules depend on each other. Arrows point from importer to imported.

```mermaid
flowchart TD
    init["__init__.py<br/>(public API re-exports)"]
    encoding["encoding.py<br/>want_bytes, b64, int<->bytes"]
    exc["exc.py<br/>BadData hierarchy"]
    json_["_json.py<br/>_CompactJSON"]
    signer["signer.py<br/>Signer, HMACAlgorithm"]
    timed["timed.py<br/>TimestampSigner<br/>TimedSerializer"]
    serializer["serializer.py<br/>Serializer"]
    url_safe["url_safe.py<br/>URLSafe(Timed)Serializer"]

    init --> encoding
    init --> exc
    init --> signer
    init --> serializer
    init --> timed
    init --> url_safe

    signer --> encoding
    signer --> exc
    serializer --> encoding
    serializer --> exc
    serializer --> signer
    timed --> encoding
    timed --> exc
    timed --> serializer
    timed --> signer
    url_safe --> json_
    url_safe --> encoding
    url_safe --> exc
    url_safe --> serializer
    url_safe --> timed

    classDef leaf fill:#e8f4f8,stroke:#2a7a99
    classDef core fill:#fff4e0,stroke:#b8860b
    classDef facade fill:#e8f8e8,stroke:#2a9933
    class encoding,exc,json_ leaf
    class signer,serializer,timed core
    class url_safe,init facade
```

No cycles. `encoding`, `exc`, `_json` are leaves. `url_safe` is the deepest module.

---

## 2. Class hierarchy

Inheritance relationships across the public types.

```mermaid
classDiagram
    class SigningAlgorithm {
        +get_signature(key, value) bytes
        +verify_signature(key, value, sig) bool
    }
    class NoneAlgorithm {
        +get_signature() returns b""
    }
    class HMACAlgorithm {
        +digest_method
        +get_signature() HMAC
    }

    class Signer {
        +secret_keys: list[bytes]
        +salt: bytes
        +sep: bytes
        +key_derivation: str
        +algorithm: SigningAlgorithm
        +sign(value) bytes
        +unsign(signed) bytes
        +derive_key(secret) bytes
    }
    class TimestampSigner {
        +get_timestamp() int
        +sign(value) bytes  *embeds ts*
        +unsign(signed, max_age) bytes
    }

    class Serializer~T~ {
        +secret_keys, salt
        +serializer: _PDataSerializer
        +signer: type[Signer]
        +fallback_signers: list
        +dumps(obj, salt) T
        +loads(s, salt) Any
        +iter_unsigners() Iterator
    }
    class TimedSerializer~T~ {
        +default_signer = TimestampSigner
        +loads(s, max_age, return_timestamp)
    }
    class URLSafeSerializerMixin {
        +default_serializer = _CompactJSON
        +dump_payload() zlib+b64
        +load_payload() b64+unzlib
    }
    class URLSafeSerializer
    class URLSafeTimedSerializer

    SigningAlgorithm <|-- NoneAlgorithm
    SigningAlgorithm <|-- HMACAlgorithm
    Signer <|-- TimestampSigner
    Serializer <|-- TimedSerializer
    URLSafeSerializerMixin --|> Serializer
    URLSafeSerializer --|> URLSafeSerializerMixin
    URLSafeSerializer --|> Serializer
    URLSafeTimedSerializer --|> URLSafeSerializerMixin
    URLSafeTimedSerializer --|> TimedSerializer

    Signer "1" o-- "1" SigningAlgorithm : algorithm
    Serializer "1" ..> "1" Signer : constructs via make_signer()
```

---

## 3. Exception hierarchy

```mermaid
classDiagram
    class BadData {
        +message: str
    }
    class BadSignature {
        +payload: Any
    }
    class BadTimeSignature {
        +date_signed: datetime
    }
    class SignatureExpired
    class BadHeader {
        +header: Any
        +original_error: Exception
    }
    class BadPayload {
        +original_error: Exception
    }

    BadData <|-- BadSignature
    BadData <|-- BadPayload
    BadSignature <|-- BadTimeSignature
    BadSignature <|-- BadHeader
    BadTimeSignature <|-- SignatureExpired
```

Note that `BadPayload` is a sibling of `BadSignature`, not a child — `except BadSignature` will NOT catch `BadPayload`.

---

## 4. Sign flow (URLSafeTimedSerializer.dumps)

End-to-end sequence for the most heavily-stacked path: a URL-safe, timestamped, compressed-JSON signed token.

```mermaid
sequenceDiagram
    autonumber
    participant App as Caller
    participant USTS as URLSafeTimedSerializer
    participant Mix as URLSafeSerializerMixin
    participant CJSON as _CompactJSON
    participant TS as TimestampSigner
    participant HMAC as HMACAlgorithm

    App->>USTS: dumps({"id": 5}, salt="auth")
    USTS->>Mix: dump_payload({"id": 5})
    Mix->>CJSON: dumps({"id": 5})
    CJSON-->>Mix: '{"id":5}'
    Mix->>Mix: want_bytes -> zlib.compress
    Note right of Mix: keep compressed iff<br/>len(zlib) < len(raw)-1
    Mix->>Mix: base64_urlsafe (strip padding)
    Note right of Mix: prepend b"." if compressed
    Mix-->>USTS: payload bytes
    USTS->>TS: make_signer("auth").sign(payload)
    TS->>TS: ts = base64(int_to_bytes(time.time()))
    TS->>TS: value = payload + sep + ts
    TS->>HMAC: get_signature(derive_key(), value)
    HMAC-->>TS: digest
    TS->>TS: sig = base64(digest)
    TS-->>USTS: value + sep + sig
    USTS->>USTS: decode utf-8 (text serializer)
    USTS-->>App: "eyJpZCI6NX0.aBcD.xyz123"
```

---

## 5. Unsign flow with fallback signers and key rotation

The most complex runtime path — load a token while a key rotation and an algorithm migration are both in progress.

```mermaid
sequenceDiagram
    autonumber
    participant App as Caller
    participant Ser as Serializer
    participant Iter as iter_unsigners
    participant S1 as PrimarySigner<br/>(SHA-512)
    participant S2 as FallbackSigner<br/>(SHA-1)
    participant LP as load_payload

    App->>Ser: loads(token, salt="auth", max_age=86400)
    Ser->>Iter: yield signers
    Iter-->>Ser: S1 (primary)
    Ser->>S1: unsign(token)
    S1->>S1: try key_new -> mismatch
    S1->>S1: try key_old -> mismatch
    S1--xSer: BadSignature
    Iter-->>Ser: S2 (fallback, key_new)
    Ser->>S2: unsign(token)
    S2->>S2: try key_new -> match!
    S2-->>Ser: payload bytes
    alt Timed signer + expired
        S2--xSer: SignatureExpired
        Ser--xApp: SignatureExpired<br/>(no further fallbacks tried)
    else Fresh signature
        Ser->>LP: load_payload(bytes)
        LP-->>Ser: dict
        Ser-->>App: {"id": 5}
    end
```

Key invariants:
- Fallback iteration stops immediately on `SignatureExpired` — the signature was structurally valid, just stale.
- Within one signer, keys are tried newest-first (last in `secret_keys`).
- A primary failure walks to fallbacks; only the LAST `BadSignature` is re-raised.

---

## 6. Token wire format

The on-the-wire string layout for each serializer variant. `.` is the default `sep`.

```mermaid
flowchart LR
    subgraph SS["Signer.sign output"]
        a1[value bytes] --> a2[.] --> a3["base64(HMAC)"]
    end

    subgraph TS["TimestampSigner.sign output"]
        b1[value bytes] --> b2[.] --> b3["base64(ts)"] --> b4[.] --> b5["base64(HMAC over value.ts)"]
    end

    subgraph US["URLSafeSerializer.dumps output"]
        c0["optional '.' marker if compressed"] --> c1["base64(zlib(json) OR json)"] --> c2[.] --> c3["base64(HMAC)"]
    end

    subgraph UST["URLSafeTimedSerializer.dumps output"]
        d0["optional '.' marker"] --> d1["base64(zlib(json) OR json)"] --> d2[.] --> d3["base64(ts)"] --> d4[.] --> d5["base64(HMAC)"]
    end
```

The leading `.` on URLSafe payloads is a one-byte compression marker. Because `_base64_alphabet` includes `=` and `-_`, the separator must NOT be one of those (validated in `Signer.__init__`).

---

## 7. Build / test / release pipeline

How the project moves from a commit to a published package (from `.github/workflows/` and `pyproject.toml` tox envs).

```mermaid
flowchart TD
    dev[Developer commit] --> pc[pre-commit<br/>ruff lint/format]
    pc --> push[Push / PR]
    push --> ci_tests[GitHub Actions: tests.yaml<br/>pytest on py3.10/3.11/3.12/3.13 + pypy311]
    push --> ci_prec[pre-commit.yaml]
    push --> ci_typ["tox -e typing<br/>mypy + pyright + pyright --verifytypes"]
    push --> ci_docs["tox -e docs<br/>sphinx-build"]
    ci_tests --> merge[Merge to main]
    ci_prec --> merge
    ci_typ --> merge
    ci_docs --> merge
    merge --> tag[Tag release]
    tag --> publish[publish.yaml<br/>flit build + SLSA provenance<br/>+ PyPI trusted publisher]
    publish --> pypi[(PyPI)]
    pypi --> users[Downstream: Flask sessions,<br/>password reset tokens, signed URLs]
```

---

## 8. Component view (C4-ish)

Bird's-eye view of where itsdangerous sits in a typical web application.

```mermaid
flowchart LR
    subgraph App["Web Application (e.g. Flask)"]
        H[Request handler] --> ID
        ID[itsdangerous<br/>Serializer / TimestampSigner] --> H
        SK["Secret key(s)<br/>from env / vault"] -.-> ID
    end

    subgraph Client["Untrusted client"]
        Cookie[Signed cookie]
        URL[Signed URL token]
        Email["Email link<br/>password reset"]
    end

    H -->|set-cookie| Cookie
    H -->|render link| URL
    H -->|send| Email
    Cookie -->|return on next request| H
    URL -->|GET /confirm?token=...| H
    Email -->|click| H

    style ID fill:#fff4e0,stroke:#b8860b
    style SK fill:#ffe0e0,stroke:#cc0000
```

The library is a pure-Python building block — it has no network, disk, or process boundary of its own. All trust flows through the secret key.

---

## Validation

Diagrams in this file use only standard Mermaid syntax (flowchart, classDiagram, sequenceDiagram) that renders on GitHub. I did not run a headless mermaid CLI render, but I reviewed each block for syntax (matched subgraph/end, valid arrow types, no unbalanced brackets, no reserved-word participant names).
