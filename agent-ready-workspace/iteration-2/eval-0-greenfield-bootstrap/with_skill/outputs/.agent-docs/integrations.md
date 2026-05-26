# External Dependencies

Runtime: **none beyond the Python stdlib.** The library is pure-Python, zero install dependencies (`pyproject.toml:1-24` shows no `dependencies` key).

Optional / dev-only groups:

| Group | Purpose | Where declared |
|---|---|---|
| `dev` | ruff, tox, tox-uv | `pyproject.toml:26-30` |
| `docs` | sphinx, pallets-sphinx-themes, sphinxcontrib-log-cabinet | `pyproject.toml:31-35` |
| `docs-auto` | sphinx-autobuild | `pyproject.toml:36-38` |
| `gha-update` | gha-update (CI pin updater) | `pyproject.toml:39-41` |
| `pre-commit` | pre-commit, pre-commit-uv | `pyproject.toml:42-45` |
| `tests` | freezegun, pytest | `pyproject.toml:46-49` |
| `typing` | mypy, pyright, pytest | `pyproject.toml:50-54` |

Build backend: `flit_core<4` (`pyproject.toml:56-58`). Lockfile pinning via `uv` (`uv.lock`, `pyproject.toml:75-76`).
