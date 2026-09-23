# radlermass

<a href="https://pypi.org/project/radlermass/"><img src="https://img.shields.io/pypi/v/radlermass.svg" alt="Latest PyPI version" /></a>
<a href="https://pypi.org/project/radlermass/"><img src="https://img.shields.io/badge/python-3.14%2B-blue.svg" alt="Supported Python versions" /></a>
<a href="https://discord.gg/astral-sh"><img src="https://img.shields.io/badge/Discord-%235865F2.svg?logo=discord&logoColor=white" alt="Discord" /></a>

Go binaries in Python wheels.

Partially derived from Simon Willison's [go-to-wheel](https://github.com/simonw/go-to-wheel).

Requires Python 3.14+ and Go. Cgo is not supported.

## Usage

```console
$ uv tool install radlermass
$ radlermass ./mytool --version 1.2.3
```

This builds the root `main` package for Linux, macOS, and Windows on amd64 and
arm64. Wheels are written to `./dist`.

Use `--package-path cmd/mytool` to build a subdirectory. Run `radlermass --help`
for all options.

Wheels include `go.mod.json` by default. Use `--no-embed-gomod-json` to omit it.

## Python API

```python
from radlermass import build_wheels

wheels = build_wheels(
    "./mytool",
    package_path="cmd/mytool",
    version="1.2.3",
)
```

Set `embed_gomod_json=False` to omit `go.mod.json`.

## Contributing

See the [contributing guide](CONTRIBUTING.md) for development and release instructions.

## License

Original radlermass code and modifications are licensed under either of

- Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE) or
  <https://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or <https://opensource.org/licenses/MIT>)

at your option.

Code derived from go-to-wheel remains licensed under Apache-2.0. See
[NOTICE](NOTICE) for attribution and modification details.

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in
radlermass by you, as defined in the Apache-2.0 license, shall be dually licensed as above, without any
additional terms or conditions.

<div align="center">
  <a target="_blank" href="https://astral.sh" style="background:none">
    <img src="https://raw.githubusercontent.com/astral-sh/uv/main/assets/svg/Astral.svg" alt="Made by Astral">
  </a>
</div>
