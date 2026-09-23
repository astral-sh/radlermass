# radlermass

Go binaries in Python wheels.

Inspired by [go-to-wheel](https://github.com/simonw/go-to-wheel). The wheels
install native executables, with no Python wrapper.

Requires Python 3.14+ and Go. Cgo is not supported.

## Usage

From a checkout:

```console
$ uv run radlermass ./mytool --version 1.2.3
```

This builds the root `main` package for Linux, macOS, and Windows (amd64 and
arm64), writing wheels to `./dist`.

Use `--package-path cmd/mytool` for a subdirectory. See `uv run radlermass --help`
for names, target selection, metadata, and linker flags.

## Python API

```python
from radlermass import build_wheels

wheels = build_wheels(
    "./mytool",
    package_path="cmd/mytool",
    version="1.2.3",
    readme="# My tool\n\nA Go command.",
)
```

`build_wheels` returns a list of absolute wheel paths. `readme` accepts Markdown
as a `str` or a file as a `pathlib.Path`; relative paths resolve against the Go
module.

## Development

```console
$ uv sync --locked
$ uv run ruff check .
$ uv run ruff format --check .
$ uv run ty check
$ uv run pytest
$ uv build
```
