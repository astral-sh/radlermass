# Contributing

## Development

```console
$ uv sync --locked
$ uv run ruff check .
$ uv run ruff format --check .
$ uv run ty check
$ uv run pytest
$ uv build
```

## Releasing

1. Run the [Prepare release workflow](https://github.com/astral-sh/radlermass/actions/workflows/release-prepare.yml)
   on `main` with the next version in `X.Y.Z` form, without a leading `v`.
   It opens or updates a `release/X.Y.Z` PR that bumps `pyproject.toml` and `uv.lock`.
2. Approve the workflow runs on the bot-created PR, review the changes, and merge
   once CI passes.
3. Run the [Release workflow](https://github.com/astral-sh/radlermass/actions/workflows/release.yml)
   on `main` with the same version. It runs CI, checks that the version matches,
   builds and publishes to PyPI, then creates the `vX.Y.Z` tag.
