import pytest

from radler._platforms import macos_tag


@pytest.mark.parametrize(
    ("go_version", "amd64", "arm64"),
    [
        ("go1.20", "10_13", "11_0"),
        ("go1.26.2", "12_0", "12_0"),
        ("go1.27rc1", "13_0", "13_0"),
        ("go1.26.2-custom", "12_0", "12_0"),
    ],
)
def test_macos_tag(go_version, amd64, arm64):
    """Select the Go release's minimum and apply the arm64 floor.

    Patch versions, prereleases, and custom toolchain suffixes use the same map.
    """
    assert macos_tag(go_version, "x86_64") == f"macosx_{amd64}_x86_64"
    assert macos_tag(go_version, "arm64") == f"macosx_{arm64}_arm64"


def test_unknown_go_version():
    """Reject unknown Go releases instead of guessing a macOS minimum."""
    with pytest.raises(ValueError, match="Unknown macOS minimum"):
        macos_tag("go1.28.0", "arm64")
