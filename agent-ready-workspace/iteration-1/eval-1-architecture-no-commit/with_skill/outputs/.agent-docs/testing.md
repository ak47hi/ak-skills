# Testing Strategy

- **Test runner:** pytest (`pyproject.toml:78-82`).
- **`testpaths = ["tests"]`**, `filterwarnings = ["error"]` (any unsilenced warning fails the test) (`pyproject.toml:80-82`).
- **Test layout:** module-per-source under `tests/test_itsdangerous/`: `test_signer.py`, `test_serializer.py`, `test_timed.py`, `test_url_safe.py`, `test_encoding.py`.
- **Type checking:** mypy + pyright in strict mode via tox `typing` env (`pyproject.toml:166-173`).
- **Lint:** ruff via pre-commit; tox `style` env runs all pre-commit hooks (`pyproject.toml:160-164`).
- **CI:** GitHub Actions workflows under `.github/workflows/`.
- **Coverage:** branch coverage, source = `["jinja2", "tests"]` — note this looks like a copy-paste error from another Pallets project (should likely be `itsdangerous`) (`pyproject.toml:84-86`).
- **Frozen-time tests:** `freezegun` is in the `tests` dependency group (`pyproject.toml:46-49`); used to test `TimestampSigner` time-based behaviour.

[NEEDS_CONTEXT]: `pyproject.toml:86` lists `source = ["jinja2", "tests"]` for coverage — is this an intentional cross-project alias or a copy-paste bug that should be `["itsdangerous", "tests"]`?
