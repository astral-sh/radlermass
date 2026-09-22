"""Compile a Go command and package it for each requested platform."""

import re
import tempfile
from collections.abc import Sequence
from pathlib import Path

from packaging.utils import canonicalize_name
from packaging.version import Version

from radler._go import Go
from radler._metadata import Metadata, validate_command
from radler._platforms import macos_tag, select_targets
from radler._wheel import wheel_timestamp, write_wheel


def _resolve_package(go_dir: str | Path, package_path: str) -> tuple[Path, str]:
    module = Path(go_dir).resolve()
    if not module.is_dir():
        raise ValueError(f"Go module directory not found: {go_dir}")
    if not (module / "go.mod").is_file():
        raise ValueError(f"Not a Go module (no go.mod): {module}")
    if not package_path or Path(package_path).is_absolute():
        raise ValueError("Package path must be a directory relative to the Go module")
    package_dir = (module / package_path).resolve()
    if not package_dir.is_relative_to(module):
        raise ValueError("Package path must stay inside the Go module")
    if not package_dir.is_dir():
        raise ValueError(f"Go package directory not found: {package_path}")
    return module, "./" + package_dir.relative_to(module).as_posix()


def _linker_flags(
    version: Version, ldflags: str | None, set_version_var: str | None
) -> str:
    flags = ["-s", "-w"]
    if set_version_var is not None:
        if not re.fullmatch(r"[^\s='\"\x00]+\.[A-Za-z_][A-Za-z0-9_]*", set_version_var):
            raise ValueError(f"Invalid Go version variable: {set_version_var!r}")
        flags.append(f"-X {set_version_var}={version}")
    if ldflags:
        flags.append(ldflags)
    result = " ".join(flags)
    if "\x00" in result:
        raise ValueError("Linker flags must not contain NUL characters")
    return result


def build_wheels(
    go_dir: str | Path,
    *,
    name: str | None = None,
    version: str = "0.1.0",
    output_dir: str | Path = "dist",
    entry_point: str | None = None,
    platforms: Sequence[str] | None = None,
    go_binary: str = "go",
    package_path: str = ".",
    description: str | None = None,
    author: str | None = None,
    author_email: str | None = None,
    license_: str | None = None,
    url: str | None = None,
    readme: str | Path | None = None,
    ldflags: str | None = None,
    set_version_var: str | None = None,
    build_timeout: float = 300,
) -> list[Path]:
    """Build wheels from ``go_dir`` and return their absolute paths.

    ``package_path`` selects the main package, defaulting to the module root.
    ``readme`` is Markdown text or a Path to a UTF-8 file. Relative README paths
    use ``go_dir``; relative ``output_dir`` paths use the working directory.
    ``description=None`` omits the package summary.

    Raises ValueError for invalid inputs, RuntimeError for Go failures or
    timeouts, and OSError for I/O or process errors.

    Existing wheels are replaced only after all builds succeed. Each replacement
    is atomic.
    """
    module, package = _resolve_package(go_dir, package_path)
    if name is None:
        name = module.name
    canonicalize_name(name, validate=True)
    command = name if entry_point is None else entry_point
    validate_command(command)
    targets = select_targets(platforms)

    if isinstance(readme, Path):
        readme = (module / readme).read_text(encoding="utf-8")
    metadata = Metadata(
        name=name,
        version=Version(version),
        description=description,
        author=author,
        author_email=author_email,
        license=license_,
        url=url,
        readme=readme,
    )
    metadata.render()  # Validate headers before invoking Go.
    flags = _linker_flags(metadata.version, ldflags, set_version_var)
    timestamp = wheel_timestamp()

    go = Go(module, executable=go_binary, timeout=build_timeout)
    wheel_tags = {}
    for target in targets:
        tag = target.tag
        if target.goos == "darwin":
            tag = macos_tag(go.version, tag)
        wheel_tags[target] = tag

    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Keep staged wheels on the output filesystem so each rename is atomic.
    with tempfile.TemporaryDirectory(prefix=".radler-", dir=output) as temporary:
        staging = Path(temporary)
        binaries = go.build(package, targets, staging, flags)
        wheels = []
        for target, tag in wheel_tags.items():
            wheel = write_wheel(
                binary=binaries[target.goos, target.goarch],
                output_dir=staging,
                metadata=metadata,
                command=command,
                tag=tag,
                timestamp=timestamp,
            )
            wheels.append(wheel)
        return [wheel.replace(output / wheel.name) for wheel in wheels]
