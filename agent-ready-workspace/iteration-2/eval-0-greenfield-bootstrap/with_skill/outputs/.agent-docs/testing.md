# Testing Strategy

- **Runner**: `pytest` (`pyproject.toml:46-49`), configured at `pyproject.toml:78-82`. Warnings are treated as errors (`filterwarnings = ["error"]`).
- **Test layout**: `tests/test_itsdangerous/` mirrors `src/itsdangerous/` one-to-one:
  - `test_encoding.py` ↔ `encoding.py`
  - `test_signer.py` ↔ `signer.py`
  - `test_serializer.py` ↔ `serializer.py`
  - `test_timed.py` ↔ `timed.py` (uses `freezegun` for clock control — `pyproject.toml:47`)
  - `test_url_safe.py` ↔ `url_safe.py`
  - `conftest.py` — shared fixtures
- **Static checks**: `mypy` strict + `pyright` standard, both scoped to `src/` (`pyproject.toml:98-108`).
- **Lint**: ruff with B/E/F/I/UP/W enabled (`pyproject.toml:116-127`); enforced via pre-commit (`.pre-commit-config.yaml`).
- **CI** (`.github/workflows/tests.yaml`):
  - Matrix: CPython 3.10–3.13 on Ubuntu, plus 3.13 on Windows + macOS, plus PyPy 3.11 (`.github/workflows/tests.yaml:13-21`).
  - Runs `uv run --locked tox run -e ...` per matrix entry (`.github/workflows/tests.yaml:25`).
  - Separate `typing` job runs mypy + pyright (`.github/workflows/tests.yaml:26-...`).
- **Coverage**: configured to `branch = true`, source `["jinja2", "tests"]` (`pyproject.toml:84-89`) — note: `source = ["jinja2", ...]` looks copy-pasted from a sibling Pallets project; see Open Questions.
