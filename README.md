# radler

Go binaries in Python wheels.

`radler` compiles Go commands for Linux, macOS, and Windows and packages them
in wheels that you can install with `pip` or `uv`. It is inspired by
[go-to-wheel](https://github.com/simonw/go-to-wheel).

Building requires Python 3.14+ and Go.

## Usage

From a checkout of this repository:

```console
$ uv run radler ./mytool
```

This builds the module's root `main` package for all supported platforms and
writes the wheels to `./dist`. The package name defaults to the directory name
(`mytool` here), and the version defaults to `0.1.0`.

If your command lives under `cmd/` (or another subdirectory), use
`--package-path`:

```console
$ uv run radler ./mytool --package-path cmd/mytool
```

You can choose the package name, version, and platforms independently:

```console
$ uv run radler ./mytool \
    --package-path cmd/mytool \
    --name mytool-bin \
    --entry-point mytool \
    --version 1.2.3 \
    --platforms linux-amd64,darwin-arm64
```

Here, `mytool-bin` is the Python package name and `mytool` is the installed
command. Without `--entry-point`, the command name is the package name.

Install the wheel for your platform:

```console
$ uv tool install ./dist/mytool_bin-1.2.3-py3-none-macosx_13_0_arm64.whl
$ mytool --help
```

The macOS version in the wheel tag comes from the selected Go toolchain; the
example above uses Go 1.27.

To embed the package version in a Go string variable:

```console
$ uv run radler ./mytool --version 1.2.3 --set-version-var main.version
```

This passes `-X main.version=1.2.3` to the Go linker. `--ldflags` accepts
additional linker flags, after the default `-s -w` and any version assignment.

`--readme` takes a Markdown file for the package description, relative to the
Go module. The other metadata options are `--description`, `--author`,
`--author-email`, `--license`, and `--url`. See `uv run radler --help` for all
options, including `--output-dir`, `--go-binary`, and `--build-timeout`.

## Python API

You can also call `build_wheels` directly:

```python
from radler import build_wheels

wheels = build_wheels(
    "./mytool",
    package_path="cmd/mytool",
    name="mytool",
    version="1.2.3",
    platforms=["linux-amd64"],
)
```

`build_wheels` returns a list of absolute `pathlib.Path` objects. It raises
`ValueError` for invalid inputs, `RuntimeError` for Go command failures (including
timeouts), and `OSError` for I/O or process errors.

`description` defaults to `None`, which omits the package summary. `readme`
accepts raw Markdown as a `str` or a `pathlib.Path` to a UTF-8 file. Relative
README paths resolve against the Go module.

## How it works

`radler` cross-compiles the selected `main` package with `CGO_ENABLED=0` and
builds a wheel for each requested platform. Commands that require cgo aren't
supported.

Each wheel contains the binary under `{name}-{version}.data/scripts/`, using
the same layout as [maturin's `bin` bindings](https://www.maturin.rs/bindings.html#bin):

```text
mytool_bin-1.2.3.data/scripts/mytool
mytool_bin-1.2.3.dist-info/METADATA
mytool_bin-1.2.3.dist-info/WHEEL
mytool_bin-1.2.3.dist-info/RECORD
```

Installers copy the binary into the environment's `bin/` directory (`Scripts/`
on Windows), where it runs directly. No Python entry point is needed, so the
wheels omit `Requires-Python` and use `py3-none-<platform>` tags.

## Supported platforms

| Target | Wheel platform tag |
| --- | --- |
| `linux-amd64` | `manylinux_2_17_x86_64` |
| `linux-arm64` | `manylinux_2_17_aarch64` |
| `linux-amd64-musl` | `musllinux_1_2_x86_64` |
| `linux-arm64-musl` | `musllinux_1_2_aarch64` |
| `darwin-amd64` | `macosx_<version>_x86_64` |
| `darwin-arm64` | `macosx_<version>_arm64` |
| `windows-amd64` | `win_amd64` |
| `windows-arm64` | `win_arm64` |

For macOS, `radler` runs `go env GOVERSION` in the module directory and maps the
selected toolchain to its [minimum macOS version](https://go.dev/wiki/MinimumRequirements).
Go 1.25–1.26 use `12_0`; Go 1.27 uses `13_0`. The map covers Go 1.16–1.27, with
a minimum of `11_0` on arm64. Unknown Go releases raise `ValueError` until the map
is updated. `MACOSX_DEPLOYMENT_TARGET` does not affect the wheel tag.

Linux wheels contain statically linked binaries, with the same binary used for
manylinux and musllinux on each architecture. Builds use `GOAMD64=v1` and
`GOARM64=v8.0` to target baseline CPUs.

OS and kernel requirements also depend on the Go toolchain and the application;
`radler` doesn't run compatibility tests on the target systems.

## Development

```console
$ uv sync --locked
$ uv run ruff check .
$ uv run ruff format --check .
$ uv run ty check
$ uv run pytest
$ uv build
```

The tests compile a local Go module for every target and install and run the
host wheel with both `pip` and `uv`. They also check the wheel contents and
`RECORD` hashes. Go tests are skipped if Go isn't installed; they don't download
external Go modules.
