# Testing Strategy

- **Test runner:** pytest (`pyproject.toml:78-82`).
- **`testpaths = ["tests"]`**, `filterwarnings = ["error"]` (any unsilenced warning fails the test) (`pyproject.toml:80-82`).
- **Test layout:** module-per-source under `tests/test_itsdangerous/`: `test_signer.py`, `test_serializer.py`, `test_timed.py`, `test_url_safe.py`, `test_encoding.py`.
- **Type checking:** mypy + pyright in strict mode via tox `typing` env; also runs `pyright --verifytypes itsdangerous --ignoreexternal` to verify the public API is fully typed (`pyproject.toml:166-173`).
- **Lint:** ruff via pre-commit; tox `style` env runs all pre-commit hooks (`pyproject.toml:160-164`).
- **CI:** GitHub Actions workflows under `.github/workflows/` (tests, pre-commit, publish, lock).
- **Coverage:** branch coverage enabled; `source = ["jinja2", "tests"]` — this looks like a copy-paste error from another Pallets project (should likely be `itsdangerous`) (`pyproject.toml:84-86`).
- **Frozen-time tests:** `freezegun` is in the `tests` dependency group (`pyproject.toml:46-49`); used to test `TimestampSigner` time-based behaviour.
- **Tox matrix:** `py3.10`, `py3.11`, `py3.12`, `py3.13`, `pypy311`, plus `style`, `typing`, `docs` (`pyproject.toml:138-146`).

[NEEDS_CONTEXT]: `pyproject.toml:86` lists `source = ["jinja2", "tests"]` for coverage — is this an intentional cross-project alias or a copy-paste bug that should be `["itsdangerous", "tests"]`?
