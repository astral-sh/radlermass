"""Supported Go targets and wheel platform tags."""

from collections.abc import Sequence
from dataclasses import dataclass

from packaging.tags import mac_platforms
from packaging.version import InvalidVersion, Version


@dataclass(frozen=True)
class Target:
    goos: str
    goarch: str
    tag: str


TARGETS = {
    "linux-amd64": Target("linux", "amd64", "manylinux_2_17_x86_64"),
    "linux-arm64": Target("linux", "arm64", "manylinux_2_17_aarch64"),
    "linux-amd64-musl": Target("linux", "amd64", "musllinux_1_2_x86_64"),
    "linux-arm64-musl": Target("linux", "arm64", "musllinux_1_2_aarch64"),
    "darwin-amd64": Target("darwin", "amd64", "x86_64"),
    "darwin-arm64": Target("darwin", "arm64", "arm64"),
    "windows-amd64": Target("windows", "amd64", "win_amd64"),
    "windows-arm64": Target("windows", "arm64", "win_arm64"),
}


def select_targets(platforms: Sequence[str] | None) -> list[Target]:
    """Select targets in request order, defaulting to all supported platforms."""
    selected = list(dict.fromkeys(TARGETS if platforms is None else platforms))
    if not selected:
        raise ValueError("Select at least one platform")

    unknown = [platform for platform in selected if platform not in TARGETS]
    if unknown:
        raise ValueError(f"Unknown platform(s): {', '.join(unknown)}")

    return [TARGETS[platform] for platform in selected]


# https://go.dev/wiki/MinimumRequirements and the Darwin release notes.
# Keep releases explicit: a new Go release may raise the macOS minimum.
MACOS_MINIMUMS = {
    (1, 16): (10, 12),
    (1, 17): (10, 13),
    (1, 18): (10, 13),
    (1, 19): (10, 13),
    (1, 20): (10, 13),
    (1, 21): (10, 15),
    (1, 22): (10, 15),
    (1, 23): (11, 0),
    (1, 24): (11, 0),
    (1, 25): (12, 0),
    (1, 26): (12, 0),
    (1, 27): (13, 0),
}


def macos_tag(go_version: str, arch: str) -> str:
    """Use the Go release's macOS minimum, with a floor of 11.0 on arm64."""
    try:
        version = Version(go_version.removeprefix("go").split("-", 1)[0])
        minimum = MACOS_MINIMUMS[version.major, version.minor]
    except InvalidVersion, KeyError:
        raise ValueError(
            f"Unknown macOS minimum for Go version {go_version!r}; "
            "update radler's Go version map"
        ) from None

    if arch == "arm64":
        minimum = max(minimum, (11, 0))

    return next(mac_platforms(version=minimum, arch=arch))
