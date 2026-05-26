# Configuration & Tunables

These are **class-level attributes / constructor parameters**, not env vars or config files. There is no runtime configuration system.

| Name | Default | Where defined | Effect |
|---|---|---|---|
| `Signer.default_digest_method` | lazy SHA-1 | `src/itsdangerous/signer.py:120` | Hash used inside HMAC |
| `Signer.default_key_derivation` | `"django-concat"` | `src/itsdangerous/signer.py:127` | Key-derivation scheme |
| `Signer` `salt` ctor arg | `b"itsdangerous.Signer"` | `src/itsdangerous/signer.py:132` | Context-separator combined with secret |
| `Signer` `sep` ctor arg | `b"."` | `src/itsdangerous/signer.py:133` | Byte separating value from signature |
| `Serializer.default_serializer` | `json` | `src/itsdangerous/serializer.py:95` | Data serializer for `dumps`/`loads` |
| `Serializer.default_signer` | `Signer` | `src/itsdangerous/serializer.py:99` | Signer class used by `make_signer` |
| `Serializer.default_fallback_signers` | `[]` | `src/itsdangerous/serializer.py:104` | Extra signers tried when primary fails |
| `Serializer` `salt` ctor arg | `b"itsdangerous"` | `src/itsdangerous/serializer.py:193` | Salt passed to constructed signer |
| `TimedSerializer.default_signer` | `TimestampSigner` | `src/itsdangerous/timed.py:175` | Time-aware signer |
| `URLSafeSerializerMixin.default_serializer` | `_CompactJSON` | `src/itsdangerous/url_safe.py:21` | Whitespace-stripped JSON |
| `TimestampSigner.unsign` `max_age` | `None` | `src/itsdangerous/timed.py:75` | Reject signatures older than this many seconds |
| `HMACAlgorithm.default_digest_method` | lazy SHA-1 | `src/itsdangerous/signer.py:54` | Hash used by the HMAC algorithm itself (mirrors Signer default) |

Tooling configuration (build/test/lint) lives in `pyproject.toml`:
- pytest: `testpaths = ["tests"]`, warnings raise as errors (`pyproject.toml:78-82`).
- mypy: strict mode, `files = ["src"]` (`pyproject.toml:98-103`).
- pyright: `pythonVersion = "3.10"`, `typeCheckingMode = "standard"`, `include = ["src"]` (`pyproject.toml:105-108`).
- ruff: lints `B`, `E`, `F`, `I`, `UP`, `W`; ignores `UP038` (`pyproject.toml:117-127`).
- tox: matrix py3.10–py3.13, pypy311, style, typing, docs (`pyproject.toml:138-146`).
