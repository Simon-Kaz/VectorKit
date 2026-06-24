# Local development and validation

The goal: nothing broken reaches GitHub. The same checks run locally (as git
hooks) and in CI, so "passes locally" guarantees "passes CI".

## One-time setup

```bash
make setup    # create .venv, install dev deps + the package
make hooks    # install the git pre-commit and pre-push hooks
```

`make setup` requires Python 3.9+. `make hooks` fetches and caches the linters
the first time (needs network).

## What runs when

| Trigger | Checks | Speed |
|---|---|---|
| `git commit` (pre-commit hook) | ruff lint+format, trailing whitespace, EOF, YAML/TOML validity, merge-conflict markers, large files, shellcheck (build scripts), actionlint (CI pipelines) | <1s |
| `git push` (pre-push hook) | everything above + `pytest` | ~seconds |
| CI (push/PR) | the exact same hooks, via `pre-commit run` | - |

post-commit hooks are intentionally not used: they run after the commit
already exists, so they cannot block anything.

## Day-to-day commands

```bash
make check    # run ALL hooks against ALL files (run before pushing)
make lint     # ruff lint only, no changes
make format   # auto-format + auto-fix lint issues
make test     # pytest
make ci       # exactly what CI validates
make help     # list all targets
```

## How the checks stay in sync with CI

Tool versions are pinned in two places that must agree:
- `.pre-commit-config.yaml` pins each hook repo by `rev`.
- `pyproject.toml` pins `ruff` in the `dev` extra.

CI installs `.[dev]` and then runs `pre-commit run --all-files`, so it executes
the identical hooks at the identical versions. Bump versions in both files
together.

## Adding new code

- Python: lives under `libs/` or `prototypes/`; ruff and pytest cover it
  automatically. Add tests next to the code (`tests/` dirs are collected).
- Shell scripts (`*.sh`): shellcheck runs automatically. Keep `set -euo
  pipefail`.
- GitHub Actions YAML: actionlint runs automatically.
- The vendored SDK (`libs/vendor/`) is excluded from all checks - it is
  third-party code we do not lint or test.

## Bypassing (rare)

`git commit --no-verify` skips hooks. Avoid it; if a hook is wrong, fix the
hook. CI does not honor `--no-verify`, so a bypass only defers the failure.
